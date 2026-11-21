"""Ingest: funding_requirements (FTS % funded). Run: python scripts/ingest/funding_requirements.py"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import funding_requirements  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(funding_requirements.run(), indent=2))
