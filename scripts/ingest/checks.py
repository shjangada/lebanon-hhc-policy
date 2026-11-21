"""Ingest: checks (idempotent). Logic lives in src/beqaa/ingest/checks.py. Run: python scripts/ingest/checks.py  (or: python -m beqaa.ingest checks)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import checks  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(checks.run(), indent=2, default=str))
