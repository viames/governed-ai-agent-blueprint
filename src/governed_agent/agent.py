from __future__ import annotations

from typing import Protocol

from .audit import AuditSink
from .models import Answer, KnowledgeRecord, ToolDecision, ToolRequest
from .policy import ToolPolicy
from .retrieval import Retriever


class LanguageModel(Protocol):
    def complete(self, question: str, context: tuple[KnowledgeRecord, ...]) -> str: ...


class GovernedAgent:
    def __init__(
        self,
        model: LanguageModel,
        retriever: Retriever,
        audit: AuditSink,
        policy: ToolPolicy | None = None,
    ) -> None:
        self._model = model
        self._retriever = retriever
        self._audit = audit
        self._policy = policy or ToolPolicy()

    def answer(self, question: str, actor_id: str = "anonymous") -> Answer:
        records = self._retriever.search(question)
        self._audit.emit(
            "retrieval.completed",
            actor_id,
            result_count=len(records),
            record_ids=tuple(record.record_id for record in records),
        )
        if not records:
            self._audit.emit("answer.refused", actor_id, reason="no_relevant_evidence")
            return Answer(
                "I cannot answer from the available knowledge base.",
                (),
                False,
            )

        text = self._model.complete(question, records).strip()
        citations = tuple(record.record_id for record in records)
        self._audit.emit("answer.completed", actor_id, citations=citations)
        return Answer(text, citations, True)

    def decide_tool(self, request: ToolRequest, actor_id: str = "anonymous") -> ToolDecision:
        decision = self._policy.decide(request)
        self._audit.emit(
            "tool.decided",
            actor_id,
            tool=request.name,
            outcome=decision.outcome,
            purpose=request.purpose,
        )
        return decision
