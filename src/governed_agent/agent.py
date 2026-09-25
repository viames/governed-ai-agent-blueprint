from __future__ import annotations

from typing import Protocol

from .audit import AuditSink
from .authorization import AccessContext, MetadataAuthorizer, RecordAuthorizer
from .models import Answer, KnowledgeRecord, ModelOutput, ToolDecision, ToolRequest
from .policy import ToolPolicy
from .retrieval import Retriever


class LanguageModel(Protocol):
    def complete(self, question: str, context: tuple[KnowledgeRecord, ...]) -> ModelOutput: ...


class GovernedAgent:
    def __init__(
        self,
        model: LanguageModel,
        retriever: Retriever,
        audit: AuditSink,
        policy: ToolPolicy | None = None,
        authorizer: RecordAuthorizer | None = None,
    ) -> None:
        self._model = model
        self._retriever = retriever
        self._audit = audit
        self._policy = policy or ToolPolicy()
        self._authorizer = authorizer or MetadataAuthorizer()

    def answer(
        self,
        question: str,
        actor_id: str = "anonymous",
        access: AccessContext | None = None,
    ) -> Answer:
        access = access or AccessContext(actor_id)
        actor_id = access.actor_id
        retrieved_records = self._retriever.search(question)
        records = self._authorizer.filter(retrieved_records, access)
        self._audit.emit(
            "retrieval.completed",
            actor_id,
            retrieved_count=len(retrieved_records),
            result_count=len(records),
            record_ids=tuple(record.record_id for record in records),
        )
        if not records:
            reason = "no_relevant_evidence"
            if retrieved_records:
                reason = "no_authorized_evidence"
            self._audit.emit("answer.refused", actor_id, reason=reason)
            return Answer(
                "I cannot answer from the available knowledge base.",
                (),
                False,
            )

        output = self._model.complete(question, records)
        available_citations = {record.record_id for record in records}
        citations = tuple(dict.fromkeys(output.citations))
        if not output.text.strip() or not citations or not set(citations) <= available_citations:
            self._audit.emit("answer.refused", actor_id, reason="invalid_model_citations")
            return Answer(
                "I cannot provide a grounded answer from the available evidence.",
                (),
                False,
            )

        self._audit.emit("answer.completed", actor_id, citations=citations)
        return Answer(output.text.strip(), citations, True)

    def decide_tool(self, request: ToolRequest, actor_id: str = "anonymous") -> ToolDecision:
        decision = self._policy.decide(request)
        self._audit.emit(
            "tool.decided",
            actor_id,
            tool=request.name,
            outcome=decision.outcome,
        )
        return decision
