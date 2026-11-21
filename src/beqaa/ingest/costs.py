"""Costs: data/raw/costs/cost_ranges.csv (48 sourced rows, new_data/costs) -> data/processed/cost_ranges.csv, and interventions.csv with cost ranges
DERIVED by transparent arithmetic from those rows wherever a unit price exists. Everything else stays an labelled assumption (mock): nothing is invented.

Derivations (cost per intervention unit; low / high, USD):
  chw_women_orgs (10 CHW-years)   10 x 12 x monthly pay: low = volunteer incentive 4b ($100), central = NGO CHW pay 4a ($300), high = outreach worker 4c upper ($450). Excludes supervision, training, transport.
  soil_water_screening (catchment) sample count is an ASSUMPTION (10 soil total-Cr + 10 water nitrate + 10 water Cr per catchment) x unit prices 6d/6c (soil), 6a (nitrate), 6b (Cr water).
  mobile_maternal_unit (unit-year) NO published MMU operating cost exists (item 1a not_found): PROXY = consultations/month x 12 x full provider cost per consultation 1d (IRC Jordan, non-Lebanon proxy), throughput 1,200-1,800 per month (1c).
Not derivable (kept mock, labelled): hub_spoke_ereferral, transport_vouchers, washing_water_truck, sunflower_biochar_plot, cr_speciation_tests (Cr(VI) speciation price not found).
Effect sizes (lift), people reached and the collateral-damage columns stay assumptions in all rows."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, RAW, ROOT, provenance

SRC = RAW / "costs" / "cost_ranges.csv"
URL = "https://github.com/shjangada/lebanon-hhc-policy (data/raw/costs/cost_ranges.csv: each row carries its own source url)"


def _v(c: pd.DataFrame, item: str, col: str) -> float:
    x = c.loc[c.item_id == item, col]
    if x.empty or pd.isna(x.iloc[0]):
        raise KeyError(f"cost item {item} has no {col}")
    return float(x.iloc[0])


def derive(c: pd.DataFrame) -> dict[str, dict]:
    chw = lambda m: 10 * 12 * m
    out = {"chw_women_orgs": dict(cost_low_usd=chw(_v(c, "4b", "usd_low")), cost_high_usd=chw(_v(c, "4c", "usd_high")),
                                  cost_basis="10 CHW x 12 months x monthly pay: $100 volunteer (4b) to $450 outreach worker (4c); NGO CHW $300 (4a) = central; excludes supervision/training",
                                  cost_items="4a;4b;4c"),
           "soil_water_screening": dict(cost_low_usd=10 * (_v(c, "6d", "usd_low") + _v(c, "6a", "usd_central") + _v(c, "6b", "usd_low")),
                                        cost_high_usd=10 * (_v(c, "6d", "usd_high") + _v(c, "6a", "usd_central") + _v(c, "6b", "usd_high")),
                                        cost_basis="ASSUMED 10 soil + 10 water-nitrate + 10 water-Cr samples per catchment x lab unit prices 6d/6a/6b (soil from $33 to $210; AUB 2025 water $25/$30)",
                                        cost_items="6a;6b;6c;6d")}
    thr_lo, thr_hi = 1200.0, 1800.0
    out["mobile_maternal_unit"] = dict(cost_low_usd=thr_lo * 12 * _v(c, "1d", "usd_low"), cost_high_usd=thr_hi * 12 * _v(c, "1d", "usd_high"),
                                       cost_basis="PROXY (no published MMU operating cost): 1,200-1,800 consultations/month x 12 x $23-56 full provider cost per consultation (1d, non-Lebanon proxy)",
                                       cost_items="1a;1c;1d")
    return out


def run() -> dict:
    c = pd.read_csv(SRC)
    c_out = provenance(c, "New data pack: Bekaa health cost ranges (48 rows, each with its own source)", "2026-11-21", "partial", URL, "COST")
    c_out.to_csv(PROCESSED / "cost_ranges.csv", index=False)
    mock = pd.read_csv(ROOT / "data" / "mock" / "interventions.csv")
    d = derive(c)
    rows = []
    for r in mock.to_dict("records"):
        r = dict(r)
        if r["intervention_id"] in d:
            r.update(d[r["intervention_id"]])
            r["cost_status"] = "derived from sourced unit prices" + (" (proxy)" if r["intervention_id"] == "mobile_maternal_unit" else "")
            r["is_mock"] = False
            r["status"] = "partial"
            r["note"] = "COST derived from data/raw/costs (see cost_basis); effect, reach and risk columns remain assumptions"
        else:
            r["cost_basis"], r["cost_items"] = "no published unit cost: mock range kept as a labelled assumption", ""
            r["cost_status"] = "assumption (mock)"
            r["is_mock"] = True
        rows.append(r)
    out = pd.DataFrame(rows)
    out["source_id"], out["source_date"], out["url"] = "COST", "2026-11-21", URL
    out["source"] = "cost_ranges.csv (derived) / mock for rows without a unit price"
    out.to_csv(PROCESSED / "interventions.csv", index=False)
    return {"cost_rows": len(c), "interventions_with_derived_cost": len(d), "interventions_mock_cost": int(out.is_mock.sum()),
            "derived": {k: (round(v["cost_low_usd"]), round(v["cost_high_usd"])) for k, v in d.items()}}
