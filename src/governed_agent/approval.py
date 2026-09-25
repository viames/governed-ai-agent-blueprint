from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

from .models import ToolRequest
from .policy import ToolPolicy


class ApprovalError(RuntimeError):
    pass


class IdempotencyConflict(ApprovalError):
    pass


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    idempotency_key: str
    actor_id: str
    tool_name: str
    arguments: Mapping[str, object]
    purpose: str
    status: str
    created_at: datetime
    expires_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None


class SQLiteApprovalWorkflow:
    """Persist approval state without executing the requested tool."""

    def __init__(
        self,
        database_path: str | Path,
        policy: ToolPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._database_path = str(database_path)
        self._policy = policy or ToolPolicy()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._initialize()

    def request(
        self,
        tool_request: ToolRequest,
        actor_id: str,
        idempotency_key: str,
        lifetime: timedelta = timedelta(minutes=30),
    ) -> ApprovalRecord:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        if lifetime <= timedelta(0):
            raise ValueError("lifetime must be positive")
        decision = self._policy.decide(tool_request)
        if decision.outcome != "approval_required":
            raise ApprovalError("Only approval-required tools enter this workflow")

        arguments_json = json.dumps(
            dict(tool_request.arguments),
            sort_keys=True,
            separators=(",", ":"),
        )
        now = self._as_utc(self._clock())
        approval_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._find_by_idempotency(connection, idempotency_key)
            if existing:
                expected = (actor_id, tool_request.name, arguments_json, tool_request.purpose)
                actual = (
                    existing.actor_id,
                    existing.tool_name,
                    json.dumps(existing.arguments, sort_keys=True, separators=(",", ":")),
                    existing.purpose,
                )
                if actual != expected:
                    raise IdempotencyConflict("Idempotency key was reused for a different request")
                return existing

            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id, idempotency_key, actor_id, tool_name,
                    arguments_json, purpose, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    approval_id,
                    idempotency_key,
                    actor_id,
                    tool_request.name,
                    arguments_json,
                    tool_request.purpose,
                    now.isoformat(),
                    (now + lifetime).isoformat(),
                ),
            )
            return self._find(connection, approval_id)

    def approve(self, approval_id: str, approver_id: str) -> ApprovalRecord:
        if not approver_id.strip():
            raise ValueError("approver_id must not be empty")
        now = self._as_utc(self._clock())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._find(connection, approval_id)
            if record.status == "approved" and record.decided_by == approver_id:
                return record
            if record.status != "pending":
                raise ApprovalError(f"Cannot approve a {record.status} request")
            if record.expires_at <= now:
                connection.execute(
                    "UPDATE approvals SET status = 'expired' WHERE approval_id = ?",
                    (approval_id,),
                )
                connection.commit()
                raise ApprovalError("Approval request has expired")
            if record.actor_id == approver_id:
                raise ApprovalError("Requester cannot approve their own tool request")

            connection.execute(
                """
                UPDATE approvals
                SET status = 'approved', decided_by = ?, decided_at = ?
                WHERE approval_id = ? AND status = 'pending'
                """,
                (approver_id, now.isoformat(), approval_id),
            )
            return self._find(connection, approval_id)

    def consume(self, approval_id: str) -> ApprovalRecord:
        now = self._as_utc(self._clock())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._find(connection, approval_id)
            if record.status == "consumed":
                return record
            if record.status != "approved":
                raise ApprovalError(f"Cannot consume a {record.status} request")
            if record.expires_at <= now:
                connection.execute(
                    "UPDATE approvals SET status = 'expired' WHERE approval_id = ?",
                    (approval_id,),
                )
                connection.commit()
                raise ApprovalError("Approved request has expired")
            connection.execute(
                "UPDATE approvals SET status = 'consumed' WHERE approval_id = ?",
                (approval_id,),
            )
            return self._find(connection, approval_id)

    def get(self, approval_id: str) -> ApprovalRecord:
        with self._connect() as connection:
            return self._find(connection, approval_id)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    actor_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('pending', 'approved', 'consumed', 'expired')
                    ),
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    decided_by TEXT,
                    decided_at TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def _find_by_idempotency(
        self,
        connection: sqlite3.Connection,
        idempotency_key: str,
    ) -> ApprovalRecord | None:
        row = connection.execute(
            "SELECT * FROM approvals WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return self._decode(row) if row else None

    def _find(self, connection: sqlite3.Connection, approval_id: str) -> ApprovalRecord:
        row = connection.execute(
            "SELECT * FROM approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        if not row:
            raise ApprovalError("Approval request was not found")
        return self._decode(row)

    @staticmethod
    def _decode(row: sqlite3.Row) -> ApprovalRecord:
        return ApprovalRecord(
            approval_id=row["approval_id"],
            idempotency_key=row["idempotency_key"],
            actor_id=row["actor_id"],
            tool_name=row["tool_name"],
            arguments=json.loads(row["arguments_json"]),
            purpose=row["purpose"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            decided_by=row["decided_by"],
            decided_at=datetime.fromisoformat(row["decided_at"]) if row["decided_at"] else None,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)
