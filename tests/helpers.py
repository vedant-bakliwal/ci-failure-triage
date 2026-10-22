from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = str(ROOT / "samples" / "run" / "*.xml")
RERUN = str(ROOT / "samples" / "rerun" / "*.xml")
HISTORY = str(ROOT / "samples" / "history" / "*" / "*.xml")
LABELS = ROOT / "samples" / "labels.json"
