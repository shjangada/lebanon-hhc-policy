"""Ingest: cadasters_population (idempotent). Logic lives in src/beqaa/ingest/cadasters_population.py. Run: python scripts/ingest/cadasters_population.py  (or: python -m beqaa.ingest cadasters_population)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import cadasters_population  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(cadasters_population.run(), indent=2, default=str))
