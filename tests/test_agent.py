import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from governed_agent import (
    GovernedAgent,
    InMemoryAuditSink,
    KnowledgeRecord,
    ModelOutput,
    ToolRequest,
)
from governed_agent.retrieval import KeywordRetriever


class RecordingModel:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, question, context):
        self.calls += 1
        return ModelOutput(f"Grounded in {context[0].record_id}", (context[0].record_id,))


class GovernedAgentTests(unittest.TestCase):
    def setUp(self):
        self.model = RecordingModel()
        self.audit = InMemoryAuditSink()
        records = (
            KnowledgeRecord("runbook-7", "Recovery target for production is four hours."),
            KnowledgeRecord("policy-2", "Production deletion requires security approval."),
        )
        self.agent = GovernedAgent(self.model, KeywordRetriever(records), self.audit)

    def test_answer_is_grounded_and_cited(self):
        answer = self.agent.answer("What is the production recovery target?", "operator-1")

        self.assertTrue(answer.grounded)
        self.assertEqual(("runbook-7",), answer.citations)
        self.assertEqual(1, self.model.calls)
        self.assertEqual("answer.completed", self.audit.events[-1].kind)

    def test_missing_evidence_refuses_without_calling_model(self):
        answer = self.agent.answer("What is the office lunch menu?")

        self.assertFalse(answer.grounded)
        self.assertEqual(0, self.model.calls)
        self.assertEqual("answer.refused", self.audit.events[-1].kind)

    def test_side_effect_requires_approval(self):
        decision = self.agent.decide_tool(
            ToolRequest("send_email", {"to": "owner@example.test"}, "Notify owner")
        )

        self.assertEqual("approval_required", decision.outcome)
        self.assertFalse(decision.may_execute)

    def test_model_cannot_cite_a_record_outside_supplied_context(self):
        class FabricatingModel:
            def complete(self, question, context):
                return ModelOutput("Unsupported claim", ("secret-record",))

        agent = GovernedAgent(
            FabricatingModel(),
            KeywordRetriever((KnowledgeRecord("runbook-7", "Recovery target is four hours."),)),
            self.audit,
        )

        answer = agent.answer("What is the recovery target?")

        self.assertFalse(answer.grounded)
        self.assertEqual((), answer.citations)
        self.assertEqual("invalid_model_citations", self.audit.events[-1].attributes["reason"])

    def test_model_must_cite_at_least_one_supplied_record(self):
        class UncitedModel:
            def complete(self, question, context):
                return ModelOutput("Uncited claim", ())

        agent = GovernedAgent(
            UncitedModel(),
            KeywordRetriever((KnowledgeRecord("runbook-7", "Recovery target is four hours."),)),
            self.audit,
        )

        self.assertFalse(agent.answer("What is the recovery target?").grounded)

    def test_unknown_and_dangerous_tools_are_denied(self):
        unknown = self.agent.decide_tool(ToolRequest("new_tool", {}, "Unknown"))
        dangerous = self.agent.decide_tool(ToolRequest("run_shell", {}, "Dangerous"))

        self.assertEqual("deny", unknown.outcome)
        self.assertEqual("deny", dangerous.outcome)

    def test_audit_does_not_record_tool_arguments_or_purpose(self):
        self.agent.decide_tool(
            ToolRequest("send_email", {"secret": "do-not-log"}, "Sensitive purpose")
        )

        attributes = self.audit.events[-1].attributes
        self.assertNotIn("arguments", attributes)
        self.assertNotIn("purpose", attributes)
        self.assertNotIn("do-not-log", repr(attributes))


if __name__ == "__main__":
    unittest.main()
