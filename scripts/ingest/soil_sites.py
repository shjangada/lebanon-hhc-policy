"""Ingest: soil_sites (idempotent). Logic lives in src/beqaa/ingest/soil_sites.py. Run: python scripts/ingest/soil_sites.py  (or: python -m beqaa.ingest soil_sites)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import soil_sites  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(soil_sites.run(), indent=2, default=str))
