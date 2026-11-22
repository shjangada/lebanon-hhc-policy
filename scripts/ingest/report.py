"""Ingest: report (docs/DATA_STATUS.md). Run: python scripts/ingest/report.py"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import report  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(report.run(), indent=2))
