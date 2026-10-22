"""Read JUnit-format XML reports (JUnit, TestNG, pytest, Playwright and most CI tools emit it)."""
from __future__ import annotations

import glob
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestResult:
    id: str            # "<classname>.<name>"
    status: str        # passed | failed | error | skipped
    error_type: str = ""
    message: str = ""
    trace: str = ""
    duration: float = 0.0

    @property
    def failed(self) -> bool:
        return self.status in ("failed", "error")


def parse_file(path: Path) -> list[TestResult]:
    root = ET.parse(path).getroot()
    results = []
    for case in root.iter("testcase"):
        name = case.get("name", "")
        classname = case.get("classname", "")
        test_id = f"{classname}.{name}" if classname else name
        duration = float(case.get("time") or 0)
        status, node = "passed", None
        for tag, label in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            found = case.find(tag)
            if found is not None:
                status, node = label, found
                break
        if node is None or status == "skipped":
            results.append(TestResult(test_id, status, duration=duration))
        else:
            results.append(TestResult(test_id, status, node.get("type", ""), node.get("message", ""),
                                      (node.text or "").strip(), duration))
    return results


def load(patterns: list[str] | None) -> list[TestResult]:
    """Load every report matching the glob patterns. Later files win for the same test id."""
    by_id: dict[str, TestResult] = {}
    for pattern in patterns or []:
        files = sorted(glob.glob(pattern, recursive=True))
        if not files:
            raise FileNotFoundError(f"No report matches {pattern}")
        for f in files:
            for r in parse_file(Path(f)):
                by_id[r.id] = r
    return list(by_id.values())


def load_history(pattern: str | None) -> list[list[TestResult]]:
    """One list of results per past build. Builds are grouped by the folder each report sits in."""
    if not pattern:
        return []
    builds: dict[str, list[TestResult]] = {}
    for f in sorted(glob.glob(pattern, recursive=True)):
        builds.setdefault(str(Path(f).parent), []).extend(parse_file(Path(f)))
    return list(builds.values())
