from django.test import TestCase

from members.models import ProjectMember
from model_evaluation.models import EvaluationRun
from projects.models import Project
from trace_analysis.services import TraceRecorder
from users.models import User

from .models import MitigationRecommendation, RegressionCase
from .services import RecommendationService, RegressionService


class MitigationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="mitigation@example.com",
            password="test-password",
            username="mitigation_user",
        )
        self.project = Project.objects.create(
            name="Mitigation Project",
            description="test",
            ai_model_name="target-mitigation-model",
            created_by=self.user,
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="owner")
        self.run = EvaluationRun.objects.create(
            project=self.project,
            name="Mitigation run",
            run_type="jailbreak",
            status="completed",
            model_name="target-mitigation-model",
        )
        self.trace = TraceRecorder.create_trace(
            project=self.project,
            run=self.run,
            scenario_type="jailbreak",
            input_text="unsafe request",
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
            mitigation_hint="Add refusal guard.",
        )

    def test_recommendation_is_idempotent_and_regression_run_compares(self):
        first = RecommendationService.create_for_risk(self.risk)
        second = RecommendationService.create_for_risk(self.risk)
        self.assertEqual(first.id, second.id)
        self.assertEqual(MitigationRecommendation.objects.filter(risk=self.risk).count(), 1)

        regression_set = RegressionService.get_or_create_default_set(
            self.project,
            source_run=self.run,
            risk_code="jailbreak_success",
        )
        RegressionCase.objects.create(
            regression_set=regression_set,
            source_case_id="manual-case",
            input_payload={"prompt": "unsafe request"},
            expected_safe_behavior="refuse safely",
            risk_code="jailbreak_success",
        )
        regression_run = RegressionService.create_run(regression_set, created_by=self.user, simulate=True)
        comparison = RegressionService.compare(regression_run)

        self.assertEqual(regression_run.status, "completed")
        self.assertEqual(comparison["regression_pass_rate"], 1)
        self.assertEqual(comparison["failed_cases"], 0)

