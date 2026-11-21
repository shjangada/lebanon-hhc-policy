"""Ingest: governance (idempotent). Logic lives in src/beqaa/ingest/governance.py. Run: python scripts/ingest/governance.py  (or: python -m beqaa.ingest governance)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import governance  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(governance.run(), indent=2, default=str))
