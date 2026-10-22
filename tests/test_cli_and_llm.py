import json
import tempfile
from pathlib import Path

from triagebot.cli import main
from triagebot.llm import BedrockAdvisor
from triagebot.triage import Group

from helpers import HISTORY, LABELS, RERUN, RUN


def test_analyze_writes_summary_and_json():
    out = Path(tempfile.mkdtemp())
    code = main(["analyze", "--reports", RUN, "--rerun", RERUN, "--history", HISTORY, "--out", str(out)])
    assert code == 0
    md = (out / "triage.md").read_text()
    assert "9 failed tests in 7 groups" in md and "### Product bugs" in md and "\n\n\n" not in md
    groups = json.loads((out / "triage.json").read_text())
    assert {g["label"] for g in groups} == {"product", "test", "environment", "flaky"}


def test_fail_on_product_bugs_sets_exit_code():
    out = tempfile.mkdtemp()
    assert main(["analyze", "--reports", RUN, "--rerun", RERUN, "--out", out, "--fail-on", "product"]) == 1
    assert main(["analyze", "--reports", RUN, "--rerun", RERUN, "--out", out, "--fail-on", "unknown"]) == 0


def test_evaluate_reports_full_accuracy_on_the_samples():
    assert main(["evaluate", "--labels", str(LABELS), "--reports", RUN, "--rerun", RERUN, "--history", HISTORY]) == 0


class FakeBedrock:
    def __init__(self, text):
        self.text, self.calls = text, []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": self.text}]}}}


def group(confidence):
    return Group("unknown", confidence, "no rule matched", "WeirdError", "boom", ["a.T.t"])


def test_llm_decides_only_low_confidence_groups():
    advisor = BedrockAdvisor(model_id="m", client=FakeBedrock('{"label": "environment", "summary": "DNS outage."}'))
    low, high = group(0.3), group(0.9)
    advisor.review(low)
    advisor.review(high)
    assert (low.label, low.source, low.summary) == ("environment", "llm", "DNS outage.")
    assert (high.label, high.summary) == ("unknown", "DNS outage.")


def test_llm_cannot_invent_labels_or_break_on_bad_json():
    g = group(0.3)
    BedrockAdvisor(model_id="m", client=FakeBedrock('{"label": "cosmic rays", "summary": "?"}')).review(g)
    assert g.label == "unknown"
    BedrockAdvisor(model_id="m", client=FakeBedrock("not json")).review(g)
    assert g.label == "unknown"
