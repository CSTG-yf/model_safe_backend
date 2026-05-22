from django.test import TestCase
from rest_framework.test import APIClient

from agent_security.models import AgentTool, AgentToolCall
from members.models import ProjectMember
from mitigation.models import MitigationRecommendation, RegressionCase, RegressionSet
from model_evaluation.metric_registry import MetricRegistry
from model_evaluation.models import EvaluationCase, EvaluationRun
from projects.models import Project
from protection_strategy.services import ProtectionPolicyGenerator
from rag_security.models import RagEvalCase, RagKnowledgeBase
from redteam_engine.models import AttackStrategy, RedTeamAttempt
from trace_analysis.services import TraceRecorder
from users.models import User


class CompetitionPackageAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="report-package@example.com",
            password="test-password",
            username="report_package_user",
        )
        self.project = Project.objects.create(
            name="Report Package Project",
            description="test",
            ai_model_name="target-report-model",
            created_by=self.user,
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="owner")

        self.run = EvaluationRun.objects.create(
            project=self.project,
            name="Competition red-team run",
            run_type="jailbreak",
            status="completed",
            model_name="target-report-model",
            total_cases=1,
            completed_cases=1,
            average_score=8.0,
            progress=100,
        )
        self.case = EvaluationCase.objects.create(
            run=self.run,
            case_id="report-case-1",
            input_payload={"prompt": "unsafe"},
            risk_tags=["jailbreak_success"],
            position=1,
        )
        self.trace = TraceRecorder.create_trace(
            project=self.project,
            run=self.run,
            scenario_type="jailbreak",
            input_text="unsafe",
        )
        self.step = TraceRecorder.add_step(
            self.trace,
            "target_response",
            "Target response",
            output_payload={"response": "unsafe"},
        )
        self.risk = TraceRecorder.add_risk(
            self.trace,
            step=self.step,
            risk_code="jailbreak_success",
            risk_name="Jailbreak success",
            risk_level="high",
            evidence=["unsafe"],
            reason="unsafe response",
            mitigation_hint="refuse",
        )
        MitigationRecommendation.objects.create(
            project=self.project,
            trace=self.trace,
            risk=self.risk,
            run=self.run,
            risk_code="jailbreak_success",
            title="Harden prompt",
            reason="risk found",
            steps=["add guard"],
            priority="high",
            status="accepted",
        )
        regression_set = RegressionSet.objects.create(
            project=self.project,
            source_run=self.run,
            name="Report regression",
            risk_codes=["jailbreak_success"],
        )
        RegressionCase.objects.create(
            regression_set=regression_set,
            source_case_id="report-case-1",
            input_payload={"prompt": "unsafe"},
            expected_safe_behavior="refuse safely",
            risk_code="jailbreak_success",
        )
        strategy = AttackStrategy.objects.create(
            code="report_strategy",
            name="Report strategy",
            category="demo",
            prompt_template="{objective} {seed_prompt} {risk_code}",
            applicable_risks=["jailbreak_success"],
        )
        RedTeamAttempt.objects.create(
            run=self.run,
            case=self.case,
            strategy=strategy,
            trace_id=self.trace.trace_id,
            target_risk_code="jailbreak_success",
            objective="test jailbreak",
            prompt="unsafe",
            response="unsafe response",
            score=8.0,
            risk_level="high",
            judge_output={"evidence": ["unsafe"]},
            success=True,
            selection_reason="history",
        )
        kb = RagKnowledgeBase.objects.create(project=self.project, name="Report KB")
        RagEvalCase.objects.create(
            run=self.run,
            knowledge_base=kb,
            question="RAG question",
            retrieved_docs=[],
            final_answer="unsafe",
            judge_output={"risk_level": "high", "evidence": ["pollution"]},
            pollution_hit=True,
            pollution_adopted=True,
            trace_id=self.trace.trace_id,
        )
        tool = AgentTool.objects.create(
            project=self.project,
            name="delete_file_mock",
            display_name="Delete file",
            tool_type="destructive",
            risk_level="high",
            allowed_roles=["admin"],
        )
        AgentToolCall.objects.create(
            project=self.project,
            run=self.run,
            tool=tool,
            trace_id=self.trace.trace_id,
            case_id="agent-case",
            prompt="delete file",
            planned_tool_name="delete_file_mock",
            arguments={"path": "/workspace/production.db"},
            user_role="guest",
            decision="blocked",
            blocked_reason="role_not_allowed",
            risk_code="agent_tool_overreach",
            risk_level="high",
            simulated_result={"executed": False},
        )
        MetricRegistry.seed_defaults()
        MetricRegistry.record(self.project, "trace_coverage_rate", 1.0, run=self.run, model_name="target-report-model")
        ProtectionPolicyGenerator.generate(
            project=self.project,
            target_model_name="target-report-model",
            created_by=self.user,
            activate=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_competition_package_endpoint_returns_report_ready_payload(self):
        response = self.client.get(
            "/api/report-generation/competition-package/",
            {"project_id": self.project.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.data["data"]
        self.assertEqual(payload["project"]["target_model_name"], "target-report-model")
        self.assertTrue(payload["protection_strategy"]["has_active_policy"])
        self.assertEqual(payload["executive_summary"]["high_risk_count"], 1)
        self.assertTrue(payload["attack_paths"])
        self.assertTrue(payload["rag_findings"])
        self.assertTrue(payload["agent_findings"])
        self.assertTrue(payload["metric_summary"]["latest"])
        self.assertIn("attack_dataset_dir", payload["demo_materials"])
