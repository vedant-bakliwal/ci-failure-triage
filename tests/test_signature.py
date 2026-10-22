from triagebot.signature import fingerprint, normalize, similarity, top_frames


def test_numbers_ids_and_timestamps_are_normalized():
    assert normalize("expected [108.25] but found [100.0]") == "expected [<n>] but found [<n>]"
    assert "<uuid>" in normalize("order 3fa85f64-5717-4562-b3fc-2c963f66afa6 not found")
    assert "<time>" in normalize("at 2026-10-20T14:02:11Z")


def test_same_bug_with_different_values_has_one_fingerprint():
    a = fingerprint("java.lang.AssertionError", "expected [108.25] but found [100.0]")
    b = fingerprint("java.lang.AssertionError", "expected [216.5] but found [200.0]")
    assert a == b
    assert a != fingerprint("java.lang.AssertionError", "expected [true] but found [false]")


def test_top_frames_skip_frameworks():
    trace = ("java.lang.AssertionError\n\tat org.testng.Assert.fail(Assert.java:111)\n"
             "\tat com.shop.tests.CheckoutTests.total(CheckoutTests.java:42)")
    assert top_frames(trace) == ["com.shop.tests.CheckoutTests.total"]


def test_similarity():
    assert similarity("connection refused db-1", "connection refused db-2") == 1.0
    assert similarity("connection refused", "element not found") == 0.0
