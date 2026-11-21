"""Health riders: a small testing -> trigger -> screening/referral add-on attached to an already-funded project.

For each project located at cadaster or district precision (processed/projects.csv):
  * receiving centre: nearest MoPH-list PHC (network preferred) and hospital to the project's population centre, with travel time (straight line x 1.3 / 40 km/h; PHCC position = village centroid);
  * soil findings in the project's districts (rung a; sampled villages, parameters, tier);
  * need score of the project's cadasters (district mean) and how many are in the robust core set;
  * rider cost range from SOURCED unit prices (data/processed/cost_ranges.csv items 6a, 6b, 6c, 4a-4c, 2a) times PARAMETERS (sample counts, CHW months, screenings: assumptions
    shown as sliders, never facts);
  * rider cost as a % of the project budget when a USD budget is known (NaN otherwise, never imputed);
  * referral load: screenings per year vs the receiving centre's assumed weekly capacity.
Hook types: water_testing, testing_trigger, worker_protection, outreach_referral, water_hygiene (nitrate priced; microbial tests, household water-treatment guidance and hygiene supplies have NO
sourced price and are listed as `unpriced_items`). `direct_health` projects are health already and get no rider."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import m4_exposure
from .io import PROCESSED, load_dataset

PRICE_ITEMS = {"nitrate_water": "6a", "cr_water": "6b", "soil_total_cr": "6c", "chw_month": ("4b", "4a", "4c"), "phc_service": "2a"}
# Sample counts and screening numbers are PARAMETERS (assumptions), taken from the illustrative counts in the shortlist; the dashboard exposes them as sliders.
DEFAULTS = {"water_testing": dict(n_nitrate=40, n_cr_water=40, n_soil=0, chw_months=0, n_screenings=100, unpriced=""),
            "testing_trigger": dict(n_nitrate=30, n_cr_water=0, n_soil=30, chw_months=12, n_screenings=100, unpriced=""),
            "worker_protection": dict(n_nitrate=0, n_cr_water=0, n_soil=0, chw_months=6, n_screenings=100, unpriced="PPE (no sourced unit price)"),
            "outreach_referral": dict(n_nitrate=0, n_cr_water=0, n_soil=0, chw_months=6, n_screenings=100, unpriced=""),
            "water_hygiene": dict(n_nitrate=40, n_cr_water=0, n_soil=0, chw_months=0, n_screenings=100,
                                  unpriced="microbial water tests; household water-treatment guidance; menstrual and postpartum hygiene supplies (no sourced unit price)")}
CENTRE_CAPACITY_WEEKLY = 300        # assumed (facilities.csv): flat per centre
LOAD_FLAG = 0.10                    # flag a centre if the rider adds more than 10% of its yearly assumed capacity (assumption)


def unit_prices(costs: pd.DataFrame | None = None) -> pd.DataFrame:
    """Low / central / high USD per unit, each with its cost_ranges item id and status. A price comes only from a row that has a number."""
    c = costs if costs is not None else pd.read_csv(PROCESSED / "cost_ranges.csv")
    c = c.set_index("item_id")
    rows = []
    for name, item in PRICE_ITEMS.items():
        if isinstance(item, tuple):                   # CHW: 4b volunteer incentive (low), 4a NGO CHW pay (central), 4c outreach worker (high)
            lo, ce, hi = (float(c.loc[i, "usd_low"] if i == "4b" else c.loc[i, "usd_central"] if i == "4a" else c.loc[i, "usd_high"]) for i in item)
            ids, st = "/".join(item), "secondary"
        else:
            r = c.loc[item]
            lo, ce, hi = (float(r.usd_low) if pd.notna(r.usd_low) else float(r.usd_central), float(r.usd_central), float(r.usd_high) if pd.notna(r.usd_high) else float(r.usd_central))
            ids, st = item, str(r.status)
        rows.append({"unit": name, "usd_low": lo, "usd_central": ce, "usd_high": hi, "cost_item": ids, "status": st})
    return pd.DataFrame(rows)


def _hav(a, b, c, d):
    p = np.pi / 180
    x = np.sin((c - a) * p / 2) ** 2 + np.cos(a * p) * np.cos(c * p) * np.sin((d - b) * p / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(x))


def build(projects: pd.DataFrame | None = None, scored: pd.DataFrame | None = None, params: dict | None = None) -> pd.DataFrame:
    """One row per project with a rider. `params` overrides DEFAULTS per hook type (e.g. {"water_testing": {"n_nitrate": 80}})."""
    pr = projects if projects is not None else pd.read_csv(PROCESSED / "projects.csv", dtype={"cadaster_ids": str})
    pr = pr[pr.location_precision.isin(["cadaster", "district"]) & pr.hook_type.isin(DEFAULTS)].copy()
    prices = unit_prices().set_index("unit")
    cad = load_dataset("cadasters").df
    pop = load_dataset("population").df[["cadaster_id", "population_total"]]
    fac = load_dataset("facilities").df
    soil = m4_exposure.screen_sites()
    sc = scored if scored is not None else None
    cad = cad.merge(pop, on="cadaster_id")
    rows = []
    for r in pr.itertuples():
        d = {**DEFAULTS[r.hook_type], **((params or {}).get(r.hook_type, {}))}
        dists = [x for x in str(r.district_list).split(";") if x and x != "nan"]
        cids = [x for x in str(r.cadaster_ids).split(";") if x and x != "nan"]
        area = cad[cad.cadaster_id.isin(cids)] if cids else cad[cad.district.isin(dists)]
        w = area.population_total.clip(lower=1)
        lat, lon = float(np.average(area.lat, weights=w)), float(np.average(area.lon, weights=w))
        phc = fac[(fac.type == "PHC")].assign(km=lambda f: _hav(lat, lon, f.lat, f.lon))
        phc = phc.sort_values(["in_mophnetwork", "km"], ascending=[False, True]).iloc[0] if phc.in_mophnetwork.any() else phc.sort_values("km").iloc[0]
        hosp = fac[fac.type == "hospital_hub"].assign(km=lambda f: _hav(lat, lon, f.lat, f.lon)).sort_values("km").iloc[0]
        ss = soil[soil.cadaster_id.isin(cad[cad.district.isin(dists)].cadaster_id) | soil.cadaster_id.isin(cids)] if len(dists) or cids else soil.iloc[0:0]
        cost = {}
        for tag in ("low", "central", "high"):
            u = lambda k: float(prices.loc[k, f"usd_{tag}"])
            cost[tag] = (d["n_nitrate"] * u("nitrate_water") + d["n_cr_water"] * u("cr_water") + d["n_soil"] * u("soil_total_cr")
                         + d["chw_months"] * u("chw_month") + d["n_screenings"] * u("phc_service"))
        bud = r.budget_usd if pd.notna(r.budget_usd) else np.nan
        load = d["n_screenings"] / (CENTRE_CAPACITY_WEEKLY * 52)
        row = {"project_id": r.project_id, "name": r.name, "funder": r.funder, "implementers": r.implementers, "hook_type": r.hook_type, "location_precision": r.location_precision,
               "districts": ";".join(dists), "recency_ok": r.recency_ok, "attachability_score": r.attachability_score, "verified": r.verified,
               "nearest_phc": phc["name"], "phc_in_network": bool(phc.in_mophnetwork), "phc_minutes": round(float(phc.km) * 1.3 / 40 * 60, 1), "nearest_hospital": hosp["name"],
               "hospital_minutes": round(float(hosp.km) * 1.3 / 40 * 60, 1), "centre_position_precision": str(phc.get("coord_confidence", "village")),
               "soil_sites_in_area": int(ss.site_name.nunique()), "soil_findings": "; ".join(sorted({f"{x.parameter} tier {int(x.tier)} (rung {x.evidence_rung})" for x in ss.itertuples() if x.tier > 0})),
               "rider_cost_low_usd": round(cost["low"]), "rider_cost_central_usd": round(cost["central"]), "rider_cost_high_usd": round(cost["high"]),
               "project_budget_usd": bud, "rider_pct_of_budget_central": cost["central"] / bud if pd.notna(bud) and bud > 0 else np.nan,
               "referral_load_share_of_centre_year": load, "referral_load_flag": bool(load > LOAD_FLAG), "unpriced_items": d["unpriced"],
               "price_items": ";".join(f"{k}:{prices.loc[k, 'cost_item']}" for k in prices.index), "parameters": "; ".join(f"{k}={v}" for k, v in d.items() if k != "unpriced")}
        if sc is not None and len(area):
            row["need_score_mean"] = float(sc[sc.cadaster_id.isin(area.cadaster_id)].need_score.mean())
        rows.append(row)
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    out = build()
    out.to_csv(PROCESSED / "riders.csv", index=False)
    return out
