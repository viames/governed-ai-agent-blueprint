import sys
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


class EvaluationModel:
    def complete(self, question, context):
        return ModelOutput(context[0].text, (context[0].record_id,))


agent = GovernedAgent(
    EvaluationModel(),
    KeywordRetriever((KnowledgeRecord("continuity-1", "Backups are verified every day."),)),
    InMemoryAuditSink(),
)

cases = (
    ("grounded_answer", agent.answer("When are backups verified?").grounded, True),
    ("unsupported_refusal", agent.answer("Who approved the budget?").grounded, False),
    (
        "mutating_tool_gate",
        agent.decide_tool(ToolRequest("create_ticket", {}, "Escalate incident")).outcome,
        "approval_required",
    ),
)

failures = [name for name, actual, expected in cases if actual != expected]
for name, actual, expected in cases:
    print(f"{'PASS' if actual == expected else 'FAIL'} {name}: {actual!r}")

raise SystemExit(1 if failures else 0)
