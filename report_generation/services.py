from collections import Counter

from agent_security.models import AgentToolCall
from mitigation.models import MitigationRecommendation, RegressionSet
from mitigation.services import RegressionService
from model_evaluation.models import EvaluationRun, MetricValue
from projects.models import Project
from protection_strategy.models import ModelProtectionStrategy
from protection_strategy.services import ProtectionPolicyCompiler
from rag_security.models import RagEvalCase
from redteam_engine.models import RedTeamAttempt
from trace_analysis.models import AppTrace, TraceRisk


class CompetitionPackageService:
    """Build data for competition reports, demos, and defense presentation pages."""

    @staticmethod
    def build(project_id, target_model_name=""):
        project = Project.objects.get(id=project_id)
        target_model_name = target_model_name or project.ai_model_name or ""
        runs = EvaluationRun.objects.filter(project=project).order_by("-created_at")
        traces = AppTrace.objects.filter(project=project).order_by("-created_at")
        risks = TraceRisk.objects.filter(trace__project=project).select_related("trace", "step").order_by("-created_at")
        recommendations = MitigationRecommendation.objects.filter(project=project).order_by("-created_at")
        regression_sets = RegressionSet.objects.filter(project=project).prefetch_related("cases").order_by("-created_at")

        active_version = CompetitionPackageService._active_policy(project, target_model_name)
        recent_regression_run = runs.filter(run_type="regression").first()

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "target_model_name": target_model_name,
            },
            "executive_summary": CompetitionPackageService._summary(
                runs=runs,
                traces=traces,
                risks=risks,
                recommendations=recommendations,
                regression_sets=regression_sets,
                active_version=active_version,
            ),
            "run_summary": CompetitionPackageService._run_summary(runs[:20]),
            "risk_summary": CompetitionPackageService._risk_summary(risks),
            "metric_summary": CompetitionPackageService._metric_summary(project, target_model_name),
            "attack_paths": CompetitionPackageService._attack_paths(project),
            "rag_findings": CompetitionPackageService._rag_findings(project),
            "agent_findings": CompetitionPackageService._agent_findings(project),
            "protection_strategy": CompetitionPackageService._policy_summary(active_version),
            "defense_comparison": (
                RegressionService.compare(recent_regression_run) if recent_regression_run else {}
            ),
            "recommendations": CompetitionPackageService._recommendations(recommendations[:20]),
            "regression_assets": CompetitionPackageService._regression_assets(regression_sets[:10]),
            "demo_materials": {
                "api_document": "project_goal_markdown/新增API接口文档.md",
                "attack_dataset_dir": "project_goal_markdown/attack_datasets",
                "redteam_dataset": "project_goal_markdown/attack_datasets/redteam_attack_cases.json",
                "rag_dataset": "project_goal_markdown/attack_datasets/rag_pollution_documents.json",
                "agent_dataset": "project_goal_markdown/attack_datasets/agent_tool_overreach_cases.json",
                "playbook": "project_goal_markdown/attack_datasets/demo_execution_playbook.md",
            },
        }

    @staticmethod
    def _summary(runs, traces, risks, recommendations, regression_sets, active_version):
        risk_counter = Counter(risk.risk_level or "low" for risk in risks)
        high_risk_count = sum(risk_counter[level] for level in ["high", "critical"])
        return {
            "run_count": runs.count(),
            "trace_count": traces.count(),
            "risk_count": risks.count(),
            "high_risk_count": high_risk_count,
            "recommendation_count": recommendations.count(),
            "accepted_recommendation_count": recommendations.filter(status__in=["accepted", "verified"]).count(),
            "regression_set_count": regression_sets.count(),
            "regression_case_count": sum(item.cases.count() for item in regression_sets[:20]),
            "has_active_policy": bool(active_version),
            "active_policy_version": active_version.version if active_version else None,
        }

    @staticmethod
    def _run_summary(runs):
        return [
            {
                "id": run.id,
                "name": run.name,
                "run_type": run.run_type,
                "status": run.status,
                "model_name": run.model_name,
                "total_cases": run.total_cases,
                "completed_cases": run.completed_cases,
                "failed_cases": run.failed_cases,
                "average_score": run.average_score,
                "progress": run.progress,
                "created_at": run.created_at,
            }
            for run in runs
        ]

    @staticmethod
    def _risk_summary(risks):
        level_counter = Counter()
        code_counter = Counter()
        scenario_counter = Counter()
        evidence = []
        for risk in risks:
            level_counter[risk.risk_level or "low"] += 1
            code_counter[risk.risk_code] += 1
            scenario = risk.trace.scenario_type if risk.trace else "unknown"
            scenario_counter[scenario] += 1
            if len(evidence) < 12:
                evidence.append({
                    "risk_id": risk.id,
                    "trace_id": risk.trace.trace_id if risk.trace else "",
                    "scenario_type": scenario,
                    "step_type": risk.step.step_type if risk.step else "",
                    "risk_code": risk.risk_code,
                    "risk_level": risk.risk_level,
                    "reason": risk.reason,
                    "evidence": risk.evidence[:3] if isinstance(risk.evidence, list) else risk.evidence,
                })
        return {
            "by_level": dict(level_counter),
            "by_code": [{"risk_code": code, "count": count} for code, count in code_counter.most_common(12)],
            "by_scenario": dict(scenario_counter),
            "evidence": evidence,
        }

    @staticmethod
    def _metric_summary(project, target_model_name):
        values = MetricValue.objects.filter(project=project).select_related("definition").order_by("-measured_at")
        latest = {}
        timeline = []
        for value in values[:200]:
            code = value.definition.code
            if target_model_name and value.model_name and value.model_name != target_model_name:
                continue
            if code not in latest:
                latest[code] = {
                    "code": code,
                    "name": value.definition.name,
                    "category": value.definition.category,
                    "value": value.value,
                    "unit": value.unit,
                    "direction": value.definition.direction,
                    "risk_code": value.risk_code,
                    "measured_at": value.measured_at,
                }
            if len(timeline) < 50:
                timeline.append({
                    "code": code,
                    "value": value.value,
                    "unit": value.unit,
                    "run_id": value.run_id,
                    "risk_code": value.risk_code,
                    "measured_at": value.measured_at,
                })
        return {"latest": list(latest.values()), "timeline": timeline}

    @staticmethod
    def _attack_paths(project):
        attempts = (
            RedTeamAttempt.objects.filter(run__project=project)
            .select_related("run", "strategy", "parent_attempt")
            .order_by("-created_at")[:30]
        )
        return [
            {
                "attempt_id": attempt.id,
                "run_id": attempt.run_id,
                "trace_id": attempt.trace_id,
                "objective": attempt.objective,
                "strategy_code": attempt.strategy.code if attempt.strategy else "",
                "parent_attempt_id": attempt.parent_attempt_id,
                "risk_code": attempt.target_risk_code,
                "risk_level": attempt.risk_level,
                "score": attempt.score,
                "success": attempt.success,
                "selection_reason": attempt.selection_reason,
                "evidence": attempt.judge_output.get("evidence", []) if isinstance(attempt.judge_output, dict) else [],
            }
            for attempt in attempts
        ]

    @staticmethod
    def _rag_findings(project):
        cases = RagEvalCase.objects.filter(run__project=project).select_related("run", "knowledge_base").order_by("-created_at")[:30]
        return [
            {
                "case_id": case.id,
                "run_id": case.run_id,
                "knowledge_base_id": case.knowledge_base_id,
                "question": case.question,
                "trace_id": case.trace_id,
                "pollution_hit": case.pollution_hit,
                "pollution_adopted": case.pollution_adopted,
                "sensitive_doc_hit": case.sensitive_doc_hit,
                "sensitive_leak": case.sensitive_leak,
                "risk_level": case.judge_output.get("risk_level", ""),
                "evidence": case.judge_output.get("evidence", []),
            }
            for case in cases
        ]

    @staticmethod
    def _agent_findings(project):
        calls = AgentToolCall.objects.filter(project=project).select_related("run", "tool").order_by("-created_at")[:30]
        return [
            {
                "call_id": call.id,
                "run_id": call.run_id,
                "trace_id": call.trace_id,
                "case_id": call.case_id,
                "planned_tool_name": call.planned_tool_name,
                "user_role": call.user_role,
                "decision": call.decision,
                "blocked_reason": call.blocked_reason,
                "risk_code": call.risk_code,
                "risk_level": call.risk_level,
                "simulated_result": call.simulated_result,
            }
            for call in calls
        ]

    @staticmethod
    def _active_policy(project, target_model_name):
        strategy = (
            ModelProtectionStrategy.objects.filter(
                project=project,
                target_model_name=target_model_name,
                status="active",
            )
            .select_related("active_version")
            .order_by("-updated_at")
            .first()
        )
        return strategy.active_version if strategy and strategy.active_version else None

    @staticmethod
    def _policy_summary(version):
        if not version:
            return {"has_active_policy": False}
        return {
            "has_active_policy": True,
            "strategy_id": version.strategy_id,
            "version_id": version.id,
            "version": version.version,
            "status": version.status,
            "target_model_name": version.strategy.target_model_name,
            "risk_profile_summary": version.risk_profile.get("summary", {}),
            "top_risks": version.risk_profile.get("top_risks", []),
            "guard_prompt_preview": version.guard_prompt[:1200],
            "guard_policy": version.guard_policy,
            "rag_guard_rules": version.rag_guard_rules,
            "agent_tool_policy": version.agent_tool_policy,
            "output_guard_rules": version.output_guard_rules,
            "regression_case_count": len(version.regression_cases or []),
            "export_markdown_preview": ProtectionPolicyCompiler.export_markdown(version)[:2000],
        }

    @staticmethod
    def _recommendations(recommendations):
        return [
            {
                "id": item.id,
                "risk_code": item.risk_code,
                "title": item.title,
                "priority": item.priority,
                "status": item.status,
                "trace_id": item.trace.trace_id if item.trace else "",
                "steps": item.steps,
            }
            for item in recommendations
        ]

    @staticmethod
    def _regression_assets(regression_sets):
        return [
            {
                "id": item.id,
                "name": item.name,
                "risk_codes": item.risk_codes,
                "case_count": item.cases.count(),
                "cases": [
                    {
                        "id": case.id,
                        "source_case_id": case.source_case_id,
                        "risk_code": case.risk_code,
                        "input_payload": case.input_payload,
                        "expected_safe_behavior": case.expected_safe_behavior,
                    }
                    for case in item.cases.all()[:10]
                ],
            }
            for item in regression_sets
        ]
