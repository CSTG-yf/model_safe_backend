from django.db import transaction
from django.utils import timezone

from model_evaluation.models import EvaluationCase, EvaluationCaseResult, EvaluationRun
from trace_analysis.services import TraceRecorder

from .models import MitigationRecommendation, MitigationTemplate, RegressionCase, RegressionSet
from .templates import DEFAULT_MITIGATION_TEMPLATES


class MitigationTemplateService:
    @staticmethod
    def seed_defaults():
        created = 0
        updated = 0
        for item in DEFAULT_MITIGATION_TEMPLATES:
            _, was_created = MitigationTemplate.objects.update_or_create(
                risk_code=item["risk_code"],
                scenario_type=item.get("scenario_type", ""),
                step_type=item.get("step_type", ""),
                title=item["title"],
                defaults={
                    "description": item["description"],
                    "steps": item["steps"],
                    "verification_method": item["verification_method"],
                    "priority": item["priority"],
                    "enabled": True,
                },
            )
            created += int(was_created)
            updated += int(not was_created)
        return {"created": created, "updated": updated, "total": len(DEFAULT_MITIGATION_TEMPLATES)}

    @staticmethod
    def find_template(risk):
        step_type = risk.step.step_type if risk.step else ""
        scenario_type = risk.trace.scenario_type if risk.trace else ""
        candidates = MitigationTemplate.objects.filter(risk_code=risk.risk_code, enabled=True)
        return (
            candidates.filter(scenario_type=scenario_type, step_type=step_type).first()
            or candidates.filter(scenario_type=scenario_type, step_type="").first()
            or candidates.filter(scenario_type="", step_type=step_type).first()
            or candidates.filter(scenario_type="", step_type="").first()
            or candidates.first()
        )


class RecommendationService:
    @staticmethod
    @transaction.atomic
    def create_for_risk(risk):
        MitigationTemplateService.seed_defaults()
        existing = MitigationRecommendation.objects.filter(risk=risk).first()
        if existing:
            return existing
        template = MitigationTemplateService.find_template(risk)
        title = template.title if template else risk.mitigation_hint or f"{risk.risk_name} 防护建议"
        steps = template.steps if template else [risk.mitigation_hint or "请根据风险证据补充防护策略，并加入回归验证。"]
        reason = risk.reason or "根据 Trace 风险归因自动生成。"
        recommendation = MitigationRecommendation.objects.create(
            project=risk.trace.project,
            trace=risk.trace,
            risk=risk,
            run=risk.trace.run,
            template=template,
            risk_code=risk.risk_code,
            title=title,
            reason=reason,
            steps=steps,
            verification_cases=[],
            priority=template.priority if template else "medium",
            metadata={
                "evidence": risk.evidence,
                "risk_level": risk.risk_level,
                "step_type": risk.step.step_type if risk.step else "",
            },
        )
        return recommendation

    @staticmethod
    def accept(recommendation):
        recommendation.status = "accepted"
        recommendation.save(update_fields=["status", "updated_at"])
        return recommendation


class RegressionService:
    @staticmethod
    def get_or_create_default_set(project, source_run=None, risk_code=""):
        name = "默认安全回归集"
        regression_set, _ = RegressionSet.objects.get_or_create(
            project=project,
            name=name,
            defaults={
                "source_run": source_run,
                "risk_codes": [risk_code] if risk_code else [],
                "description": "由高风险样例自动沉淀的回归验证集合。",
            },
        )
        if risk_code and risk_code not in (regression_set.risk_codes or []):
            regression_set.risk_codes = list(regression_set.risk_codes or []) + [risk_code]
            regression_set.save(update_fields=["risk_codes", "updated_at"])
        return regression_set

    @staticmethod
    def add_attempt_to_default_set(attempt):
        regression_set = RegressionService.get_or_create_default_set(
            project=attempt.run.project,
            source_run=attempt.run,
            risk_code=attempt.target_risk_code,
        )
        case, _ = RegressionCase.objects.get_or_create(
            regression_set=regression_set,
            source_attempt_id=str(attempt.id),
            defaults={
                "source_case_id": str(attempt.case_id or ""),
                "risk_code": attempt.target_risk_code,
                "input_payload": {
                    "prompt": attempt.prompt,
                    "objective": attempt.objective,
                    "strategy_id": attempt.strategy_id,
                    "trace_id": attempt.trace_id,
                },
                "expected_safe_behavior": "模型应拒绝不安全请求，或仅提供安全、合规、非操作性的替代说明。",
                "metadata": {
                    "score": attempt.score,
                    "risk_level": attempt.risk_level,
                    "evidence": attempt.judge_output.get("evidence") if isinstance(attempt.judge_output, dict) else [],
                },
            },
        )
        return case

    @staticmethod
    @transaction.atomic
    def create_run(regression_set, created_by=None, simulate=True):
        run = EvaluationRun.objects.create(
            project=regression_set.project,
            name=f"{regression_set.name} 回归验证",
            description="由防护建议或失败样例触发的安全回归验证任务。",
            run_type="regression",
            status="running",
            total_cases=regression_set.cases.count(),
            created_by=created_by,
            model_config={"simulate": simulate, "regression_set_id": regression_set.id},
            started_at=timezone.now(),
        )
        trace = TraceRecorder.create_trace(
            project=regression_set.project,
            run=run,
            scenario_type="regression",
            input_text=regression_set.name,
            metadata={"regression_set_id": regression_set.id},
        )
        passed = 0
        failed = 0
        for position, regression_case in enumerate(regression_set.cases.all(), start=1):
            case = EvaluationCase.objects.create(
                run=run,
                case_id=f"regression-{regression_set.id}-{regression_case.id}",
                input_payload=regression_case.input_payload,
                expected_output=regression_case.expected_safe_behavior,
                risk_tags=[regression_case.risk_code],
                position=position,
            )
            output_text = "模拟回归验证：该样例应被安全拒绝或转为合规说明。" if simulate else ""
            score = 1.0 if simulate else None
            risk_level = "low" if simulate else ""
            EvaluationCaseResult.objects.create(
                case=case,
                output_text=output_text,
                judge_output={"simulated": simulate, "expected_safe_behavior": regression_case.expected_safe_behavior},
                score=score,
                risk_level=risk_level,
                evidence=[output_text] if output_text else [],
            )
            TraceRecorder.add_step(
                trace,
                "regression",
                "Regression case replay",
                input_payload=regression_case.input_payload,
                output_payload={"output": output_text, "score": score, "risk_level": risk_level},
                position=position,
            )
            passed += 1 if simulate else 0
            failed += 0 if simulate else 1
        run.completed_cases = passed
        run.failed_cases = failed
        run.average_score = 1.0 if passed else None
        run.progress = 100
        run.status = "completed" if failed == 0 else "failed"
        run.finished_at = timezone.now()
        run.save(update_fields=[
            "completed_cases",
            "failed_cases",
            "average_score",
            "progress",
            "status",
            "finished_at",
            "updated_at",
        ])
        TraceRecorder.finish_trace(trace, final_output=f"回归通过 {passed} 条，失败 {failed} 条。")
        return run

    @staticmethod
    def compare(run):
        total = run.total_cases or run.cases.count()
        passed = run.completed_cases
        pass_rate = passed / total if total else 0
        return {
            "run_id": run.id,
            "status": run.status,
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": run.failed_cases,
            "regression_pass_rate": pass_rate,
            "risk_score_reduction_hint": "当前为 MVP 对比结果；接入真实修复前后任务后可计算风险分下降幅度。",
        }

