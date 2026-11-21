"""Ingest: lhf_allocations (idempotent). Logic lives in src/beqaa/ingest/lhf_allocations.py. Run: python scripts/ingest/lhf_allocations.py  (or: python -m beqaa.ingest lhf_allocations)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import lhf_allocations  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(lhf_allocations.run(), indent=2, default=str))
