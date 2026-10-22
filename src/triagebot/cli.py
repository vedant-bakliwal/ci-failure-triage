"""Command line.

    triagebot analyze --reports "samples/run/*.xml" --rerun "samples/rerun/*.xml" --history "samples/history/*/*.xml"
    triagebot evaluate --labels samples/labels.json [same report options]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from . import reports, summary
from .triage import labels_by_test, triage


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="triagebot", description="Triage CI test failures from JUnit XML reports.")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("analyze", "evaluate"):
        s = sub.add_parser(name)
        s.add_argument("--reports", nargs="+", required=True, help="glob(s) for this run's JUnit XML reports")
        s.add_argument("--rerun", nargs="*", help="glob(s) for reports of a rerun of the failed tests")
        s.add_argument("--history", help="glob for reports of earlier builds, one folder per build")
        s.add_argument("--llm", choices=["none", "bedrock"], default="none")
        if name == "analyze":
            s.add_argument("--out", default="out")
            s.add_argument("--github-summary", action="store_true", help="append the summary to $GITHUB_STEP_SUMMARY")
            s.add_argument("--pr-comment", metavar="PR_NUMBER", help="post the summary on a pull request with the gh CLI")
            s.add_argument("--fail-on", nargs="*", default=[], choices=["product", "test", "environment", "flaky", "unknown"],
                           help="exit 1 if any group has one of these labels")
        else:
            s.add_argument("--labels", required=True, help="JSON file mapping test id to the expected label")
    return p


def run_triage(args):
    current = reports.load(args.reports)
    groups = triage(current, reports.load(args.rerun) if args.rerun else None, reports.load_history(args.history))
    if args.llm == "bedrock":
        from .llm import BedrockAdvisor
        advisor = BedrockAdvisor()
        for g in groups:
            advisor.review(g)
    return current, groups


def analyze(args) -> int:
    current, groups = run_triage(args)
    text = summary.render(groups, len(current))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "triage.md").write_text(text)
    (out / "triage.json").write_text(json.dumps([asdict(g) for g in groups], indent=2))
    if args.github_summary and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text)
    if args.pr_comment:
        subprocess.run(["gh", "pr", "comment", args.pr_comment, "--body-file", str(out / "triage.md")], check=True)
    counts = {}
    for g in groups:
        counts[g.label] = counts.get(g.label, 0) + len(g.tests)
    print(f"{sum(counts.values())} failed tests in {len(groups)} groups: "
          + (", ".join(f"{k} {v}" for k, v in counts.items()) or "none") + f". Summary: {out / 'triage.md'}")
    return 1 if any(g.label in args.fail_on for g in groups) else 0


def evaluate(args) -> int:
    expected = json.loads(Path(args.labels).read_text())
    _, groups = run_triage(args)
    got = labels_by_test(groups)
    correct = sum(got.get(t) == label for t, label in expected.items())
    print(f"Label accuracy: {correct}/{len(expected)} ({correct / len(expected):.0%})")
    for t, label in expected.items():
        if got.get(t) != label:
            print(f"  {t}: expected {label}, got {got.get(t, 'not failing')}")
    return 0 if correct == len(expected) else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return analyze(args) if args.command == "analyze" else evaluate(args)


if __name__ == "__main__":
    sys.exit(main())
