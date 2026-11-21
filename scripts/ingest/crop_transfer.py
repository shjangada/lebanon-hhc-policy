"""Ingest: crop_transfer (idempotent). Logic lives in src/beqaa/ingest/crop_transfer.py. Run: python scripts/ingest/crop_transfer.py  (or: python -m beqaa.ingest crop_transfer)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import crop_transfer  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(crop_transfer.run(), indent=2, default=str))
