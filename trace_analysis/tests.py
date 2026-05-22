from django.test import TestCase

from members.models import ProjectMember
from model_evaluation.models import EvaluationRun
from projects.models import Project
from users.models import User

from .models import TraceRisk, TraceStep
from .services import TraceAttributionService, TraceRecorder


class TraceRecorderServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="trace@example.com",
            password="test-password",
            username="trace_user",
        )
        self.project = Project.objects.create(
            name="Trace Project",
            description="test",
            ai_model_name="target-trace-model",
            created_by=self.user,
        )
        ProjectMember.objects.create(project=self.project, user=self.user, role="owner")
        self.run = EvaluationRun.objects.create(
            project=self.project,
            name="Trace run",
            run_type="jailbreak",
            status="running",
            model_name="target-trace-model",
        )

    def test_trace_steps_risks_and_attribution(self):
        trace = TraceRecorder.create_trace(
            project=self.project,
            run=self.run,
            scenario_type="jailbreak",
            input_text="attack prompt",
            metadata={"source": "test"},
        )
        step = TraceRecorder.add_step(
            trace,
            "model_output",
            "Target response",
            output_payload={"response": "unsafe output"},
        )
        self.assertEqual(TraceStep.objects.filter(trace=trace).count(), 1)
        self.assertEqual(step.position, 1)

        low_risk = TraceRecorder.add_risk(
            trace=trace,
            step=step,
            risk_code="unsafe_model_output",
            risk_name="Unsafe output",
            risk_level="low",
            evidence=["unsafe output"],
            reason="low risk",
        )
        self.assertEqual(low_risk.risk_level, "low")
        trace.refresh_from_db()
        self.assertEqual(trace.risk_level, "low")

        none_result = TraceAttributionService.from_judge_score(
            trace,
            {"score": 0, "risk_level": "none", "reason": "safe", "evidence": []},
            step=step,
        )
        self.assertIsNone(none_result)

        high_risk = TraceAttributionService.from_judge_score(
            trace,
            {
                "score": 8.0,
                "risk_level": "high",
                "reason": "judge found jailbreak",
                "evidence": ["jailbreak evidence"],
                "confidence": 0.8,
            },
            step=step,
            risk_code="jailbreak_success",
        )
        self.assertIsNotNone(high_risk)
        self.assertEqual(TraceRisk.objects.filter(trace=trace).count(), 2)
        trace.refresh_from_db()
        self.assertEqual(trace.risk_level, "high")

        TraceRecorder.finish_trace(trace, final_output="final", metadata={"finished": True})
        trace.refresh_from_db()
        self.assertEqual(trace.final_output, "final")
        self.assertTrue(trace.metadata["finished"])
        self.assertEqual(trace.metadata["source"], "test")

