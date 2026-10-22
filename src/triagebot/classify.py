"""Rule-based labels: product bug, test bug, environment problem, or flaky test.

Order matters. Rerun and history evidence come first (a test that passes on rerun is flaky
whatever its error says), then infrastructure signatures, then test-code signatures, then
assertion and server errors that point at the product.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .reports import TestResult
from .signature import top_frames

LABELS = ("product", "test", "environment", "flaky", "unknown")

ENVIRONMENT = re.compile(
    r"connection refused|connectexception|unknownhostexception|name or service not known|econnreset"
    r"|socket ?timeout|connect timed out|no space left on device|outofmemoryerror|too many open files"
    r"|503 service unavailable|502 bad gateway|session not created|chrome not reachable"
    r"|failed to launch|could not start a new session|rate limit", re.I)
TEST_CODE = re.compile(
    r"nosuchelementexception|staleelementreferenceexception|unable to locate element|invalidselector"
    r"|element click intercepted|locator|fixture|test data|testdatafactory", re.I)
SERVER_ERROR = re.compile(r"(status code|status) ?<?2\d\d>? but was <?5\d\d>?|\b5\d\d internal server error", re.I)
ASSERTION = re.compile(r"assertionerror|expected \[.*\] but found|expected:? ?<.*> but was|assert ", re.I)


@dataclass(frozen=True)
class Verdict:
    label: str
    confidence: float
    reason: str


def flakiness(test_id: str, rerun: dict[str, TestResult], history: list[dict[str, TestResult]]) -> Verdict | None:
    again = rerun.get(test_id)
    if again is not None and again.status == "passed":
        return Verdict("flaky", 0.95, "failed, then passed on rerun with no code change")
    past = [h[test_id].failed for h in history if test_id in h]
    if len(past) >= 3 and any(past) and not all(past):
        return Verdict("flaky", 0.7, f"failed in {sum(past)} of the last {len(past)} builds without a fix")
    return None


def by_rules(result: TestResult) -> Verdict:
    text = f"{result.error_type} {result.message} {result.trace}"
    if ENVIRONMENT.search(text):
        return Verdict("environment", 0.9, "infrastructure error (network, service, browser or resources)")
    if TEST_CODE.search(text):
        return Verdict("test", 0.85, "failure in test code: locator, fixture or test data")
    frames = top_frames(result.trace)
    if result.error_type.endswith(("NullPointerException", "IndexOutOfBoundsException", "ClassCastException")) \
            and frames and ".tests." in frames[0]:
        return Verdict("test", 0.75, f"exception thrown in test code at {frames[0]}")
    if SERVER_ERROR.search(text):
        return Verdict("product", 0.85, "the service returned a 5xx error")
    if ASSERTION.search(text):
        return Verdict("product", 0.7, "an assertion on product behaviour failed")
    return Verdict("unknown", 0.3, "no rule matched")
