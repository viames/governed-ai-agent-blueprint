from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from governed_agent import (
    AccessContext,
    GovernedAgent,
    InMemoryAuditSink,
    KnowledgeRecord,
    ModelOutput,
    ToolRequest,
)
from governed_agent.retrieval import KeywordRetriever


class EvaluationModel:
    def complete(self, question, context):
        return ModelOutput(context[0].text, (context[0].record_id,))


def evaluate(case):
    audit = InMemoryAuditSink()
    if case["kind"] == "answer":
        records = tuple(
            KnowledgeRecord(
                item["record_id"],
                item["text"],
                item.get("metadata", {}),
            )
            for item in case["records"]
        )
        agent = GovernedAgent(EvaluationModel(), KeywordRetriever(records), audit)
        access_data = case["access"]
        access = AccessContext(
            access_data["actor_id"],
            access_data.get("tenant_id"),
            frozenset(access_data.get("roles", [])),
        )
        answer = agent.answer(case["question"], access=access)
        actual = {
            "grounded": answer.grounded,
            "citations": list(answer.citations),
        }
        expected = {
            "grounded": case["expected_grounded"],
            "citations": case["expected_citations"],
        }
    else:
        agent = GovernedAgent(EvaluationModel(), KeywordRetriever(()), audit)
        decision = agent.decide_tool(
            ToolRequest(case["tool"], {}, "Evaluation case"),
            "evaluation-actor",
        )
        actual = {"outcome": decision.outcome}
        expected = {"outcome": case["expected_outcome"]}

    return {
        "name": case["name"],
        "kind": case["kind"],
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")
    arguments = parser.parse_args()

    configuration = json.loads((ROOT / "evals" / "cases.json").read_text())
    results = [evaluate(case) for case in configuration["cases"]]
    passed = sum(result["passed"] for result in results)
    total = len(results)
    pass_rate = passed / total if total else 0.0
    by_kind = Counter(result["kind"] for result in results if result["passed"])
    totals_by_kind = Counter(result["kind"] for result in results)
    report = {
        "passed": passed,
        "total": total,
        "pass_rate": pass_rate,
        "minimum_pass_rate": configuration["minimum_pass_rate"],
        "metrics": {
            kind: {"passed": by_kind[kind], "total": count}
            for kind, count in sorted(totals_by_kind.items())
        },
        "results": results,
    }

    if arguments.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for result in results:
            state = "PASS" if result["passed"] else "FAIL"
            print(f"{state} {result['name']}: {result['actual']!r}")
        print(f"pass_rate={pass_rate:.1%} threshold={configuration['minimum_pass_rate']:.1%}")

    raise SystemExit(0 if pass_rate >= configuration["minimum_pass_rate"] else 1)


if __name__ == "__main__":
    main()
