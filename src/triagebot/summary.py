"""Markdown for a pull-request comment or a CI job summary."""
from __future__ import annotations

from .triage import Group

TITLES = {
    "product": ("Product bugs", "Likely a real defect in the application. Route to the owning team."),
    "test": ("Test bugs", "The test code or test data needs a fix; the product is probably fine."),
    "environment": ("Environment problems", "Infrastructure or a dependency was down. Fix or wait, then rerun."),
    "flaky": ("Flaky tests", "Pass and fail without a code change. Candidates for quarantine and a stability fix."),
    "unknown": ("Needs a human", "No rule matched. Look at these first if the build must go out."),
}


def render(groups: list[Group], total_tests: int) -> str:
    failures = sum(len(g.tests) for g in groups)
    if not groups:
        return f"## Test triage\n\nAll {total_tests} tests passed.\n"
    lines = [f"## Test triage: {failures} failed tests in {len(groups)} groups ({total_tests} tests run)", "",
             "| Category | Groups | Tests |", "|---|---|---|"]
    for label, (title, _) in TITLES.items():
        gs = [g for g in groups if g.label == label]
        if gs:
            lines.append(f"| {title} | {len(gs)} | {sum(len(g.tests) for g in gs)} |")
    for label, (title, advice) in TITLES.items():
        gs = [g for g in groups if g.label == label]
        if not gs:
            continue
        lines += ["", f"### {title}", "", advice, ""]
        for n, g in enumerate(gs, 1):
            short = g.message if len(g.message) <= 160 else g.message[:157] + "..."
            lines.append(f"**{n}. {g.error_type.split('.')[-1] or 'Failure'}** ({len(g.tests)} test{'s' * (len(g.tests) > 1)}, "
                         f"confidence {g.confidence:.0%}{', LLM-reviewed' if g.source == 'llm' else ''})")
            lines.append(f"- Why: {g.reason}")
            lines.append(f"- Error: `{short.replace('`', '')}`")
            if g.frames:
                lines.append(f"- Where: `{g.frames[0]}`")
            if g.summary:
                lines.append(f"- Root cause (LLM): {g.summary}")
            lines.append("- Tests: " + ", ".join(f"`{t.split('.')[-2]}.{t.split('.')[-1]}`" if t.count('.') else f"`{t}`" for t in g.tests))
            lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text
