from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol


@dataclass(frozen=True)
class AuditEvent:
    occurred_at: datetime
    kind: str
    actor_id: str
    attributes: Mapping[str, object]


class AuditSink(Protocol):
    def emit(self, kind: str, actor_id: str, **attributes: object) -> None: ...

    def record(self, event: AuditEvent) -> None: ...


class InMemoryAuditSink:
    def __init__(
        self,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.events: list[AuditEvent] = []

    def emit(self, kind: str, actor_id: str, **attributes: object) -> None:
        self.record(AuditEvent(self._clock(), kind, actor_id, dict(attributes)))

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)
