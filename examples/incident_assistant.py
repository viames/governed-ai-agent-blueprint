from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from governed_agent import (
    AccessContext,
    GovernedAgent,
    InMemoryAuditSink,
    KnowledgeRecord,
    ModelOutput,
    SQLiteApprovalWorkflow,
    ToolRequest,
)
from governed_agent.retrieval import KeywordRetriever


class RunbookModel:
    """Deterministic stand-in for a provider model in this local example."""

    def complete(self, question, context):
        return ModelOutput(
            "The runbook requires isolating the worker and opening a high-severity ticket.",
            (context[0].record_id,),
        )


records = (
    KnowledgeRecord(
        "runbook-payment-worker",
        "A failing payment worker must be isolated and escalated as a high-severity ticket.",
        {"tenant_id": "acme", "allowed_roles": "operator,incident_manager"},
    ),
)
audit = InMemoryAuditSink()
agent = GovernedAgent(RunbookModel(), KeywordRetriever(records), audit)
access = AccessContext("operator-17", "acme", frozenset({"operator"}))

answer = agent.answer("How should a failing payment worker be handled?", access=access)
print(f"answer={answer.text}")
print(f"citations={answer.citations}")

tool_request = ToolRequest(
    "create_ticket",
    {"queue": "operations", "severity": "high"},
    "Escalate the verified payment-worker incident",
)
decision = agent.decide_tool(tool_request, access.actor_id)
print(f"tool_decision={decision.outcome}")

with tempfile.TemporaryDirectory() as directory:
    approvals = SQLiteApprovalWorkflow(Path(directory) / "approvals.sqlite3")
    pending = approvals.request(tool_request, access.actor_id, "payment-incident-2026-09-25")
    approved = approvals.approve(pending.approval_id, "incident-manager-4")
    consumed = approvals.consume(approved.approval_id)
    print(f"approval_state={pending.status}->{approved.status}->{consumed.status}")

print(f"audit_events={[event.kind for event in audit.events]}")
