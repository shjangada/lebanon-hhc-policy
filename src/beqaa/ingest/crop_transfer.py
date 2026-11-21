"""3.x crop_transfer: Abi Saab et al. 2022 (Water 14(9):1437), Beqaa (Tal Amara) field trial: printed bioaccumulation factors (BAF = C_plant / C_soil) by CROP,
metal and season (Table 4). Values are the printed factor-level means (pooled over water sources and irrigation methods): we do not recompute them. Metals in the paper:
Cr, Ni, Zn, Cu, Cd (no Pb, no As): M4 therefore has no crop pathway for Pb (soil ingestion only)."""
from __future__ import annotations

import re

import pandas as pd

from .common import PROCESSED, ROOT, provenance

SRC = ROOT / "transcribed" / "abi_saab_tf.csv"


def build() -> pd.DataFrame:
    t = pd.read_csv(SRC)
    t = t[t.table_or_figure.astype(str).str.startswith("Table 4")]
    t = t[t.site_or_treatment.astype(str).str.startswith("Crop:")].copy()
    t["season"] = t.site_or_treatment.str.extract(r"season (\d{4})")[0]
    val = t.transfer_factor if t.transfer_factor.notna().any() else t.crop_concentration_mg_kg
    out = pd.DataFrame({"metal": t.metal, "crop": t.crop.str.lower(), "transfer_factor": val, "season": t.season, "tf_definition": "BAF = C_plant / C_soil (as printed)",
                        "source": "Abi Saab et al. 2022, Water 14(9):1437, Table 4 (pooled factor-level means)", "page": t.page, "transcription_checked": t.checked})
    return provenance(out.reset_index(drop=True), "Abi Saab et al. 2022, Water 14(9):1437 (hand-transcribed, two passes)", "2022-05-01", "verified",
                      "https://www.mdpi.com/2073-4441/14/9/1437", "S28")


def run() -> dict:
    df = build()
    df.to_csv(PROCESSED / "crop_transfer.csv", index=False)
    return {"rows": len(df), "metals": sorted(df.metal.unique().tolist()), "crops": sorted(df.crop.unique().tolist()), "empty_values": int(df.transfer_factor.isna().sum())}
