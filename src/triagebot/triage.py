"""Group failures by root cause and label each group."""
from __future__ import annotations

from dataclasses import dataclass, field

from .classify import Verdict, by_rules, flakiness
from .reports import TestResult
from .signature import fingerprint, similarity, top_frames

MERGE_SIMILARITY = 0.8


@dataclass
class Group:
    label: str
    confidence: float
    reason: str
    error_type: str
    message: str
    tests: list[str] = field(default_factory=list)
    frames: list[str] = field(default_factory=list)
    summary: str = ""          # filled by the optional LLM advisor
    source: str = "rules"      # "rules" or "llm"


def triage(current: list[TestResult], rerun: list[TestResult] | None = None,
           history: list[list[TestResult]] | None = None) -> list[Group]:
    rerun_by_id = {r.id: r for r in rerun or []}
    history_by_id = [{r.id: r for r in build} for build in history or []]

    groups: dict[str, Group] = {}
    for result in (r for r in current if r.failed):
        flaky = flakiness(result.id, rerun_by_id, history_by_id)
        verdict = flaky or by_rules(result)
        if verdict.label != "flaky" and result.id in rerun_by_id and rerun_by_id[result.id].failed:
            verdict = Verdict(verdict.label, min(0.99, verdict.confidence + 0.05), verdict.reason + "; failed again on rerun")
        # Flaky tests are grouped per test; everything else per root-cause fingerprint.
        key = f"flaky:{result.id}" if verdict.label == "flaky" else f"{verdict.label}:{fingerprint(result.error_type, result.message)}"
        group = groups.get(key)
        if group is None:
            group = groups[key] = Group(verdict.label, verdict.confidence, verdict.reason, result.error_type,
                                        result.message, frames=top_frames(result.trace))
        group.tests.append(result.id)

    merged: list[Group] = []
    for g in groups.values():
        twin = next((m for m in merged if m.label == g.label != "flaky" and m.error_type == g.error_type
                     and similarity(m.message, g.message) >= MERGE_SIMILARITY), None)
        if twin:
            twin.tests.extend(g.tests)
        else:
            merged.append(g)

    order = {"product": 0, "test": 1, "environment": 2, "flaky": 3, "unknown": 4}
    merged.sort(key=lambda g: (order[g.label], -len(g.tests)))
    return merged


def labels_by_test(groups: list[Group]) -> dict[str, str]:
    return {t: g.label for g in groups for t in g.tests}
