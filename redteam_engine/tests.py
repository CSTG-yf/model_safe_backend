from django.test import TestCase

from members.models import ProjectMember
from mitigation.models import MitigationRecommendation, RegressionCase
from projects.models import Project
from trace_analysis.models import AppTrace, TraceRisk
from users.models import User

from .models import AttackStrategy, RedTeamAttempt, StrategyStat
from .services import RedTeamOrchestrator, StrategySeedService
from .strategy_selector import StrategySelector


class RedTeamEngineServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="redteam@example.com",
            password="test-password",
            username="redteam_user",
        )
        self.project = Project.objects.create(
            name="RedTeam Project",
            description="test",
            ai_model_name="target-redteam-model",
            created_by=self.user,
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="owner")

    def test_strategy_selector_prefers_successful_history(self):
        weak = AttackStrategy.objects.create(
            code="weak_strategy",
            name="Weak",
            category="demo",
            prompt_template="Weak {objective} {seed_prompt} {risk_code}",
            applicable_risks=["jailbreak_success"],
        )
        strong = AttackStrategy.objects.create(
            code="strong_strategy",
            name="Strong",
            category="demo",
            prompt_template="Strong {objective} {seed_prompt} {risk_code}",
            applicable_risks=["jailbreak_success"],
        )
        StrategyStat.objects.create(
            strategy=weak,
            risk_code="jailbreak_success",
            attempts=5,
            successes=0,
            average_score=2,
            novelty_score=0.5,
        )
        StrategyStat.objects.create(
            strategy=strong,
            risk_code="jailbreak_success",
            attempts=5,
            successes=4,
            average_score=8,
            novelty_score=0.5,
        )

        selected = StrategySelector().select("jailbreak_success")

        self.assertEqual(selected.strategy, strong)
        self.assertIn("历史成功率", selected.reason)

    def test_simulated_orchestrator_writes_attempt_trace_recommendation_and_regression(self):
        StrategySeedService.seed_defaults()
        orchestrator = RedTeamOrchestrator(
            project=self.project,
            target_model_name="target-redteam-model",
            max_rounds=2,
            simulate=True,
            created_by=self.user,
        )
        run = orchestrator.create_run(
            name="Simulated red-team",
            objectives=[{"objective": "test jailbreak", "risk_code": "jailbreak_success"}],
        )
        orchestrator.run(run, [{"objective": "test jailbreak", "risk_code": "jailbreak_success"}])
        run.refresh_from_db()

        self.assertEqual(run.status, "completed")
        self.assertEqual(RedTeamAttempt.objects.filter(run=run).count(), 1)
        self.assertEqual(AppTrace.objects.filter(project=self.project, scenario_type="jailbreak").count(), 1)
        self.assertEqual(TraceRisk.objects.filter(trace__project=self.project, risk_code="jailbreak_success").count(), 1)
        self.assertEqual(MitigationRecommendation.objects.filter(project=self.project, risk_code="jailbreak_success").count(), 1)
        self.assertEqual(RegressionCase.objects.filter(regression_set__project=self.project, risk_code="jailbreak_success").count(), 1)

