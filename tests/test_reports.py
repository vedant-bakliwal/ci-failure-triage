from triagebot import reports

from helpers import HISTORY, RUN


def test_reads_passes_failures_and_errors():
    results = reports.load([RUN])
    assert len(results) == 24
    by_id = {r.id: r for r in results}
    tax = by_id["com.shop.tests.CheckoutTests.totalIncludesTax"]
    assert tax.status == "failed" and tax.error_type == "java.lang.AssertionError"
    assert "CheckoutTests.java:42" in tax.trace
    assert by_id["com.shop.tests.InventoryTests.reserveStock"].status == "error"
    assert sum(r.failed for r in results) == 9


def test_history_is_grouped_one_list_per_build():
    builds = reports.load_history(HISTORY)
    assert len(builds) == 5
    assert all(len(b) == 24 for b in builds)


def test_missing_report_is_a_clear_error():
    try:
        reports.load(["no/such/*.xml"])
    except FileNotFoundError as e:
        assert "no/such" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")
