"""Costs: data/raw/costs/cost_ranges.csv (48 sourced rows, new_data/costs) -> data/processed/cost_ranges.csv, and interventions.csv with cost ranges
DERIVED by transparent arithmetic from those rows wherever a unit price exists. Everything else stays an labelled assumption (mock): nothing is invented.

Derivations (cost per intervention unit; low / high, USD):
  chw_women_orgs (10 CHW-years)   10 x 12 x monthly pay: low = volunteer incentive 4b ($100), central = NGO CHW pay 4a ($300), high = outreach worker 4c upper ($450). Excludes supervision, training, transport.
  soil_water_screening (catchment) sample count is an ASSUMPTION (10 soil total-Cr + 10 water nitrate + 10 water Cr per catchment) x unit prices 6d/6c (soil), 6a (nitrate), 6b (Cr water).
  mobile_maternal_unit (unit-year) NO published MMU operating cost exists (item 1a not_found): PROXY = consultations/month x 12 x full provider cost per consultation 1d (IRC Jordan, non-Lebanon proxy), throughput 1,200-1,800 per month (1c).
A software-only proxy for hub_spoke_ereferral (Sierra Leone eIDSR: $1,021 + $224 per facility, PMC8820104) is computed below but deliberately NOT used in the ranking: the option's effect size is still an unsourced placeholder, so a real cost with a placeholder effect would make it look dominant (it moved the community-vs-status-quo break-even from 5.6% to 63%). It is shown in unit_costs.csv for information.
Not derivable (kept as labelled placeholders): hub_spoke_ereferral, transport_vouchers, washing_water_truck, sunflower_biochar_plot, cr_speciation_tests (Cr(VI) speciation price not found).
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
    # hub_spoke_ereferral: PROXY from the Sierra Leone eIDSR (DHIS2) cost study (PMC8820104, 2017 USD): rollout USD 1,021 per facility and running cost USD 224 per facility per year.
    # First-year cost per district = (1,021 + 224) x number of MoPH-list PHCs in the district (4 to 24). Covers software and rollout only: it EXCLUDES coordination staff and the time to
    # track referrals (no sourced cost), and it is a surveillance system, not an e-referral tracker.
    fac = pd.read_csv(PROCESSED / "facilities.csv", dtype={"cadaster_id": str})
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})[["cadaster_id", "district"]]
    n_phc = fac[fac.type == "PHC"].merge(cad, on="cadaster_id").groupby("district").size()
    out_hub = dict(cost_low_usd=float(n_phc.min() * (1021 + 224)), cost_high_usd=float(n_phc.max() * (1021 + 224)),
                   cost_basis="PROXY: Sierra Leone eIDSR (DHIS2) rollout $1,021 + running $224 per facility (PMC8820104, 2017) x 4-24 PHCs per district; software and rollout only (no staff time)",
                   cost_items="eIDSR")
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
            r["cost_basis"], r["cost_items"] = "no published unit cost: range kept as a labelled ASSUMPTION (placeholder), not data", ""
            r["cost_status"] = "assumption (placeholder)"
            r["is_mock"] = True
        rows.append(r)
    out = pd.DataFrame(rows)
    # Effects: only where a published estimate was READ (not Lebanon; scenario ranges). CHW: any-ANC +0.0 (Tanzania cluster RCT, RR 0.97 on <4 visits: null) to +0.169
    # (Afghanistan DiD, +10.5 pp, 95% CI 4.2-16.9) and facility delivery +11.0 pp (4.0-18.0), Edmond 2018 BMC Medicine; Geldsetzer 2019 PLoS Med. Mobile unit: no effect size found,
    # lift 0 here and the break-even is the result. All effects are non-Lebanon proxies to be verified against the originals.
    chw = out.intervention_id == "chw_women_orgs"
    out.loc[chw, ["lift_low", "lift_high"]] = [0.0, 0.169]
    out.loc[chw, "steps"] = "any_anc;facility_delivery"
    out["effect_basis"] = ""
    out.loc[chw, "effect_basis"] = "literature proxy (non-Lebanon): Edmond 2018 BMC Medicine (Afghanistan, +10.5 pp ANC, CI 4.2-16.9; delivery +11.0 pp); Geldsetzer 2019 PLoS Med (Tanzania, null on ANC4): range 0 to 0.169; verify originals"
    out.loc[~chw, "effect_basis"] = "no published effect size found: lift range is an ASSUMPTION (placeholder); the break-even is the result"
    out.loc[out.intervention_id == "soil_water_screening", "effect_basis"] = "environmental measure: acts on exposure, not on the ANC cascade"
    out["source_id"], out["source_date"], out["url"] = "COST", "2026-11-21", URL
    out["source"] = "cost_ranges.csv (derived) / mock for rows without a unit price"
    out.to_csv(PROCESSED / "interventions.csv", index=False)
    return {"cost_rows": len(c), "interventions_with_derived_cost": len(d), "assumption_rows": int(out.is_mock.sum()),
            "derived": {k: (round(v["cost_low_usd"]), round(v["cost_high_usd"])) for k, v in d.items()}}
