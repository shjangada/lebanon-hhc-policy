"""Ingest: conflict (idempotent). Logic lives in src/beqaa/ingest/conflict.py. Run: python scripts/ingest/conflict.py  (or: python -m beqaa.ingest conflict)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import conflict  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(conflict.run(), indent=2, default=str))
