from __future__ import annotations

import re
from typing import Protocol

from .models import KnowledgeRecord


class Retriever(Protocol):
    def search(self, query: str, limit: int = 3) -> tuple[KnowledgeRecord, ...]: ...


class KeywordRetriever:
    def __init__(self, records: tuple[KnowledgeRecord, ...], minimum_score: int = 2) -> None:
        if minimum_score < 1:
            raise ValueError("minimum_score must be positive")
        self._records = records
        self._minimum_score = minimum_score

    def search(self, query: str, limit: int = 3) -> tuple[KnowledgeRecord, ...]:
        query_terms = self._terms(query)
        if not query_terms:
            return ()

        ranked: list[tuple[int, str, KnowledgeRecord]] = []
        for record in self._records:
            score = len(query_terms & self._terms(record.text))
            if score >= self._minimum_score:
                ranked.append((score, record.record_id, record))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in ranked[:limit])

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}
