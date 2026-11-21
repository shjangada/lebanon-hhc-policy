"""Ingest: funding_flows (idempotent). Logic lives in src/beqaa/ingest/funding_flows.py. Run: python scripts/ingest/funding_flows.py  (or: python -m beqaa.ingest funding_flows)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import funding_flows  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(funding_flows.run(), indent=2, default=str))
