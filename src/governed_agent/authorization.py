from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import KnowledgeRecord


@dataclass(frozen=True)
class AccessContext:
    actor_id: str
    tenant_id: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)


class RecordAuthorizer(Protocol):
    def filter(
        self,
        records: tuple[KnowledgeRecord, ...],
        context: AccessContext,
    ) -> tuple[KnowledgeRecord, ...]: ...


class MetadataAuthorizer:
    """Apply tenant and role restrictions encoded in record metadata."""

    def filter(
        self,
        records: tuple[KnowledgeRecord, ...],
        context: AccessContext,
    ) -> tuple[KnowledgeRecord, ...]:
        return tuple(record for record in records if self._can_read(record, context))

    @staticmethod
    def _can_read(record: KnowledgeRecord, context: AccessContext) -> bool:
        tenant_id = record.metadata.get("tenant_id")
        if tenant_id and tenant_id != context.tenant_id:
            return False

        allowed_roles = {
            role.strip()
            for role in record.metadata.get("allowed_roles", "").split(",")
            if role.strip()
        }
        return not allowed_roles or bool(allowed_roles & context.roles)
