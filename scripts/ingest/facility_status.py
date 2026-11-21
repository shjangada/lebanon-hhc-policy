"""Ingest: facility_status (idempotent). Logic lives in src/beqaa/ingest/facility_status.py. Run: python scripts/ingest/facility_status.py  (or: python -m beqaa.ingest facility_status)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import facility_status  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(facility_status.run(), indent=2, default=str))
