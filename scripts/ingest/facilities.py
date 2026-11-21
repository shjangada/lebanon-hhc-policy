"""Ingest: facilities (idempotent). Logic lives in src/beqaa/ingest/facilities.py. Run: python scripts/ingest/facilities.py  (or: python -m beqaa.ingest facilities)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import facilities  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(facilities.run(), indent=2, default=str))
