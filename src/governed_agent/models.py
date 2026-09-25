from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class KnowledgeRecord:
    record_id: str
    text: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[str, ...]
    grounded: bool


@dataclass(frozen=True)
class ToolRequest:
    name: str
    arguments: Mapping[str, object]
    purpose: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True)
class ToolDecision:
    outcome: str
    reason: str

    @property
    def may_execute(self) -> bool:
        return self.outcome == "allow"
