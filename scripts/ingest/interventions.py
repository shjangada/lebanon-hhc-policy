"""Ingest: interventions (reference cost lines only; no unit costs exist in the source)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import interventions  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(interventions.run(), indent=2, default=str))
