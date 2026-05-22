from django.test import TestCase

from members.models import ProjectMember
from mitigation.models import MitigationRecommendation, RegressionCase
from projects.models import Project
from protection_strategy.services import ProtectionPolicyGenerator
from trace_analysis.models import AppTrace, TraceRisk
from users.models import User

from .models import AgentTool, AgentToolCall
from .services import AgentSandbox, AgentToolRegistry, ToolPolicyEngine


class AgentSecuritySandboxTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="agent-security@example.com",
            password="test-password",
            username="agent_security_user",
        )
        self.project = Project.objects.create(
            name="Agent Security Project",
            description="test",
            ai_model_name="target-agent-model",
            created_by=self.user,
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="owner")

    def test_seed_policy_and_sandbox_trace_flow(self):
        stats = AgentToolRegistry.seed_defaults(self.project)
        self.assertEqual(stats["total"], 6)
        self.assertEqual(AgentTool.objects.filter(project=self.project).count(), 6)

        delete_tool = AgentTool.objects.get(project=self.project, name="delete_file_mock")
        decision = ToolPolicyEngine.evaluate(
            delete_tool,
            arguments={"path": "/app/settings.py"},
            user_role="member",
            confirmed=False,
        )
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["blocked_reason"], "role_not_allowed")

        sandbox = AgentSandbox(project=self.project, target_model_name="target-agent-model", created_by=self.user)
        run = sandbox.create_run()
        sandbox.run(run)
        run.refresh_from_db()

        self.assertEqual(run.status, "completed")
        self.assertEqual(AgentToolCall.objects.filter(run=run).count(), 4)
        self.assertGreaterEqual(AgentToolCall.objects.filter(run=run, decision__in=["blocked", "requires_confirmation"]).count(), 3)
        self.assertEqual(AppTrace.objects.filter(project=self.project, scenario_type="agent").count(), 4)
        self.assertGreaterEqual(TraceRisk.objects.filter(trace__project=self.project, risk_code="agent_tool_overreach").count(), 2)
        self.assertGreaterEqual(MitigationRecommendation.objects.filter(project=self.project, risk_code="agent_tool_overreach").count(), 1)
        self.assertGreaterEqual(RegressionCase.objects.filter(regression_set__project=self.project, risk_code="agent_tool_overreach").count(), 1)

        strategy, version = ProtectionPolicyGenerator.generate(
            project=self.project,
            target_model_name="target-agent-model",
            created_by=self.user,
            activate=True,
        )
        self.assertEqual(strategy.active_version_id, version.id)
        top_codes = {item["risk_code"] for item in version.risk_profile["top_risks"]}
        self.assertIn("agent_tool_overreach", top_codes)
        self.assertIn("Agent 工具防护", version.guard_prompt)
