"""Ingest: haus_2024 (appendix evidence from the UNHCR HAUS 2024 report). Run: python scripts/ingest/haus_2024.py"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from beqaa.ingest import haus_2024  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(haus_2024.run(), indent=2))
