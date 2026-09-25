from __future__ import annotations

from .models import ToolDecision, ToolRequest


class ToolPolicy:
    def __init__(
        self,
        allowed: frozenset[str] = frozenset({"search_knowledge"}),
        approval_required: frozenset[str] = frozenset({"send_email", "create_ticket"}),
        denied: frozenset[str] = frozenset({"delete_record", "run_shell"}),
    ) -> None:
        overlap = (allowed & approval_required) | (allowed & denied) | (approval_required & denied)
        if overlap:
            raise ValueError(f"Tools cannot belong to multiple policy groups: {sorted(overlap)}")
        self._allowed = allowed
        self._approval_required = approval_required
        self._denied = denied

    def decide(self, request: ToolRequest) -> ToolDecision:
        if request.name in self._denied:
            return ToolDecision("deny", "Tool is explicitly denied by policy")
        if request.name in self._approval_required:
            return ToolDecision("approval_required", "Tool can cause an external side effect")
        if request.name in self._allowed:
            return ToolDecision("allow", "Tool is allowlisted; normal authorization still applies")
        return ToolDecision("deny", "Unknown tools are denied by default")
