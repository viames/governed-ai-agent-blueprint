import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from governed_agent import (
    ApprovalError,
    IdempotencyConflict,
    SQLiteApprovalWorkflow,
    ToolRequest,
)


class SQLiteApprovalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.now = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)
        self.workflow = SQLiteApprovalWorkflow(
            Path(self.temporary_directory.name) / "approvals.sqlite3",
            clock=lambda: self.now,
        )
        self.request = ToolRequest(
            "create_ticket",
            {"queue": "operations", "severity": "high"},
            "Escalate a verified production incident",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_approval_is_persistent_and_consumed_once(self):
        pending = self.workflow.request(self.request, "operator-1", "incident-42")
        reopened = SQLiteApprovalWorkflow(
            Path(self.temporary_directory.name) / "approvals.sqlite3",
            clock=lambda: self.now,
        )

        approved = reopened.approve(pending.approval_id, "manager-1")
        consumed = reopened.consume(pending.approval_id)

        self.assertEqual("approved", approved.status)
        self.assertEqual("manager-1", approved.decided_by)
        self.assertEqual("consumed", consumed.status)
        self.assertEqual("consumed", reopened.consume(pending.approval_id).status)

    def test_request_is_idempotent_but_key_reuse_is_not(self):
        first = self.workflow.request(self.request, "operator-1", "incident-42")
        repeated = self.workflow.request(self.request, "operator-1", "incident-42")

        self.assertEqual(first.approval_id, repeated.approval_id)
        with self.assertRaises(IdempotencyConflict):
            self.workflow.request(
                ToolRequest("create_ticket", {"severity": "low"}, "Different request"),
                "operator-1",
                "incident-42",
            )

    def test_requester_cannot_self_approve(self):
        pending = self.workflow.request(self.request, "operator-1", "incident-42")

        with self.assertRaises(ApprovalError):
            self.workflow.approve(pending.approval_id, "operator-1")

    def test_expired_request_cannot_be_approved(self):
        pending = self.workflow.request(
            self.request,
            "operator-1",
            "incident-42",
            lifetime=timedelta(minutes=5),
        )
        self.now += timedelta(minutes=6)

        with self.assertRaises(ApprovalError):
            self.workflow.approve(pending.approval_id, "manager-1")
        self.assertEqual("expired", self.workflow.get(pending.approval_id).status)

    def test_approved_request_expires_before_consumption(self):
        pending = self.workflow.request(
            self.request,
            "operator-1",
            "incident-42",
            lifetime=timedelta(minutes=5),
        )
        self.workflow.approve(pending.approval_id, "manager-1")
        self.now += timedelta(minutes=6)

        with self.assertRaises(ApprovalError):
            self.workflow.consume(pending.approval_id)
        self.assertEqual("expired", self.workflow.get(pending.approval_id).status)


if __name__ == "__main__":
    unittest.main()
