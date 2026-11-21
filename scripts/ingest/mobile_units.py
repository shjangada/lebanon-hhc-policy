"""Ingest: mobile_units (idempotent). Logic lives in src/beqaa/ingest/mobile_units.py. Run: python scripts/ingest/mobile_units.py  (or: python -m beqaa.ingest mobile_units)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import mobile_units  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(mobile_units.run(), indent=2, default=str))
