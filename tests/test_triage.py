import json

from triagebot import reports
from triagebot.classify import by_rules
from triagebot.reports import TestResult
from triagebot.triage import labels_by_test, triage

from helpers import HISTORY, LABELS, RERUN, RUN


def test_sample_run_matches_every_expected_label():
    groups = triage(reports.load([RUN]), reports.load([RERUN]), reports.load_history(HISTORY))
    assert labels_by_test(groups) == json.loads(LABELS.read_text())


def test_one_product_bug_hit_by_two_tests_is_one_group():
    groups = triage(reports.load([RUN]), reports.load([RERUN]), reports.load_history(HISTORY))
    tax = [g for g in groups if "CheckoutTests.totalIncludesTax" in " ".join(g.tests)]
    assert len(tax) == 1 and len(tax[0].tests) == 2 and tax[0].label == "product"


def test_history_alone_marks_a_flaky_test():
    groups = triage(reports.load([RUN]), None, reports.load_history(HISTORY))
    labels = labels_by_test(groups)
    assert labels["com.shop.tests.SessionTests.tokenRefresh"] == "flaky"          # failed in 2 of 5 past builds
    # Without a rerun, a UI wait timeout is ambiguous: it is left for a human or the LLM step.
    assert labels["com.shop.tests.SearchTests.searchReturnsResults"] == "unknown"


def test_without_rerun_or_history_only_the_ambiguous_timeout_is_unknown():
    labels = labels_by_test(triage(reports.load([RUN])))
    assert [t for t, label in labels.items() if label == "unknown"] == ["com.shop.tests.SearchTests.searchReturnsResults"]
    assert labels["com.shop.tests.SessionTests.tokenRefresh"] == "product"  # looks like a real bug until history says otherwise


def test_rules():
    def label(error_type, message, trace=""):
        return by_rules(TestResult("t", "failed", error_type, message, trace)).label
    assert label("java.net.UnknownHostException", "payments.internal") == "environment"
    assert label("AssertionError", "Expected status code <200> but was <503 Service Unavailable>") == "environment"
    assert label("StaleElementReferenceException", "stale element reference") == "test"
    assert label("AssertionError", "Expected status code <200> but was <500>.") == "product"
    assert label("SomethingOdd", "weird") == "unknown"
