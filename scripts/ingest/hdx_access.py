"""Ingest: hdx_access (idempotent). Logic lives in src/beqaa/ingest/hdx_access.py. Run: python scripts/ingest/hdx_access.py  (or: python -m beqaa.ingest hdx_access)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import hdx_access  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(hdx_access.run(), indent=2, default=str))
