"""Published damage figures (data/raw/damage/published_figures_transcribed.csv, 41 rows from the new data pack) -> data/processed/damage_published.csv.
The rows were read through AUTOMATED text extraction: every row is status `to_verify_pdf` until checked against the source PDF (docs/DATA_REQUESTS.md). They are governorate / district
totals and a few named cadasters, not a cadaster-level surface: they inform the 'Why Beqaa' panel and the evidence table, and are NOT used as a model input. No 2026 Bekaa
building-damage dataset was found (UNOSAT/HDX/UCDP downloads were blocked in the pack's environment)."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, RAW, provenance


def run() -> dict:
    d = pd.read_csv(RAW / "damage" / "published_figures_transcribed.csv").rename(columns={"source_id": "figure_source"})     # keep the per-row source id
    out = provenance(d, "Published damage figures (UN-Habitat BDDQA 2025, World Bank RDNA 2025, CNRS-L via Annahar, IMPACT HSM); automated extraction, verify against the PDFs",
                     "2026-11-21", "to_verify_pdf", "see source_url per row", "DMG")
    out.to_csv(PROCESSED / "damage_published.csv", index=False)
    return {"rows": len(out), "sources": sorted(out.figure_source.unique())}
