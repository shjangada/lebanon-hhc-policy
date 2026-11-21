"""WorldPop 2025 age/sex 1 km rasters (constrained, modelled) summed by cadaster and district -> data/processed/agesex_by_district.csv (district, sex, age_band, population).
Bands are WorldPop's own (0, 1-4, 5-9, ... 90+). Modelled, not counted: a population pyramid for the five districts and the Beqaa total, plus the demand shares the
dashboard quotes (women 15-49, children under 5, aged 60+). WorldPop is NOT scaled to the LRP 2026 totals here (it predates the 2026 displacement)."""
from __future__ import annotations

import re
import zipfile

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from .cadasters_population import UPSAMPLE, _admin3
from .common import PROCESSED, RAW, provenance

ZIP = RAW / "population" / "worldpop" / "lbn_agesex_structures_2025_CN_1km_R2025A_UA_v1.zip"


def run() -> dict:
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})
    feats = [f for f in _admin3() if f["properties"]["adm3_pcode"] in set(cad.cadaster_id)]
    names = sorted(n for n in zipfile.ZipFile(ZIP).namelist() if n.endswith(".tif") and re.search(r"_(f|m)_\d\d_", n))
    with rasterio.open(f"/vsizip/{ZIP}/{names[0]}") as src:
        tr, shp = src.transform, src.shape
    big_tr = tr * tr.scale(1 / UPSAMPLE, 1 / UPSAMPLE)
    ids = rasterize([(f["geometry"], i) for i, f in enumerate(feats)], out_shape=(shp[0] * UPSAMPLE, shp[1] * UPSAMPLE), transform=big_tr, fill=-1, dtype="int32")
    m = ids >= 0
    pc = [f["properties"]["adm3_pcode"] for f in feats]
    rows = []
    for n in names:
        sex, age = re.search(r"_(f|m)_(\d\d)_", n).groups()
        with rasterio.open(f"/vsizip/{ZIP}/{n}") as src:
            a = src.read(1).astype("float64")
        a[(a < 0) | ~np.isfinite(a)] = 0
        up = np.kron(a, np.ones((UPSAMPLE, UPSAMPLE))) / UPSAMPLE ** 2
        z = np.bincount(ids[m], weights=up[m], minlength=len(feats))
        rows += [{"cadaster_id": c, "sex": "female" if sex == "f" else "male", "age_band": int(age), "population": float(v)} for c, v in zip(pc, z)]
    t = pd.DataFrame(rows).merge(cad[["cadaster_id", "district"]], on="cadaster_id")
    d = t.groupby(["district", "sex", "age_band"], as_index=False).population.sum()
    out = provenance(d, "WorldPop 2025 age/sex 1 km (constrained, modelled), summed by district; not scaled to LRP 2026 totals", "2025-08-17", "partial",
                     "https://hub.worldpop.org/geodata/summary?id=77090", "WP")
    out.to_csv(PROCESSED / "agesex_by_district.csv", index=False)
    return {"rows": len(out), "total_population": round(float(d.population.sum())), "districts": sorted(d.district.unique())}
