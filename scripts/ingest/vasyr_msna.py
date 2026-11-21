"""Ingest: vasyr_msna (idempotent). Logic lives in src/beqaa/ingest/vasyr_msna.py. Run: python scripts/ingest/vasyr_msna.py  (or: python -m beqaa.ingest vasyr_msna)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import vasyr_msna  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(vasyr_msna.run(), indent=2, default=str))
