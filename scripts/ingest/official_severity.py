"""Ingest: official_severity (idempotent). Logic lives in src/beqaa/ingest/official_severity.py. Run: python scripts/ingest/official_severity.py  (or: python -m beqaa.ingest official_severity)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import official_severity  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(official_severity.run(), indent=2, default=str))
