"""Ingest: cascade_baseline (idempotent). Logic lives in src/beqaa/ingest/cascade_baseline.py. Run: python scripts/ingest/cascade_baseline.py  (or: python -m beqaa.ingest cascade_baseline)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import cascade_baseline  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(cascade_baseline.run(), indent=2, default=str))
