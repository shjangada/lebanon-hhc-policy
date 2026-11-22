"""Pilot flow: a light version of M3. Referral funnel, outreach schedule, water-testing floor, capacity-aware routing, break-evens.

Everything with no Beqaa measurement is a SLIDER (assumption), not data: screened share, symptomatic/positive rate, CHW-handled share, referral completion, illness duration, visits a CHW can
make, spare share of a centre's capacity. The one sourced default is water positivity: 72% of tested samples in Baalbek-Hermel informal-settlement water were faecally contaminated (WaSH
Sector / UNICEF SitRep No. 5, Jul 2026; processed/wash.csv). Expected wait from symptom to contact = half the visit interval: a model approximation, labelled as such.
WHO GDWQ Table 4.4 floor: at least 12 samples a year for a supply serving fewer than 5,000 people (docs/water_sampling_guideline.md): a quarterly schedule fails it."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import riders
from .io import load_dataset

WATER_POSITIVITY = 0.72                    # sourced: settlement water samples faecally contaminated, Baalbek-Hermel, Jul 2026
GDWQ_MIN_SAMPLES_PER_YEAR = 12             # supplies serving < 5,000 people
LOAD_LIMIT = 0.10                          # a centre is flagged if the rider adds > 10% of its assumed yearly capacity (riders.LOAD_FLAG)
DEFAULTS = dict(coverage=0.5, screened_share=0.5, positive_rate=0.15, chw_share=0.8, completion=0.5, illness_weeks=2.0, visits_per_chw_week=10, spare_share=0.2,
                monthly_incidence=0.02)


def funnel(people_in_settlements: float, p: dict | None = None) -> pd.DataFrame:
    """People reached -> screened -> symptomatic or positive -> handled by CHWs -> red flags -> referral completed (annual, one site)."""
    q = {**DEFAULTS, **(p or {})}
    reached = people_in_settlements * q["coverage"]
    screened = reached * q["screened_share"]
    pos = screened * q["positive_rate"]
    chw = pos * q["chw_share"]
    red = pos - chw
    done = red * q["completion"]
    return pd.DataFrame({"stage": ["reached", "screened", "symptomatic / positive", "handled by CHWs", "red flags referred", "referral completed"], "people": [reached, screened, pos, chw, red, done]})


def schedule(people_in_settlements: float, n_sources: int, chw_interval_weeks: float, water_interval_months: float, p: dict | None = None) -> dict:
    """Cost and yield of one CHW-visit and water-test schedule for a site. Cost uses sourced unit prices (CHW month, nitrate and Cr water tests)."""
    q = {**DEFAULTS, **(p or {})}
    u = riders.unit_prices().set_index("unit")
    reached = people_in_settlements * q["coverage"]
    visits_month = (52 / chw_interval_weeks) / 12 * max(1, int(np.ceil(reached / 200)))                      # one visit round per settlement group of ~200 people (assumption)
    n_chw = max(1.0, visits_month * 12 / 12 / (q["visits_per_chw_week"] * 52 / 12))
    chw_cost = n_chw * float(u.loc["chw_month", "usd_central"])
    tests_year = n_sources * 12 / water_interval_months
    water_cost = tests_year / 12 * float(u.loc["nitrate_water", "usd_central"] + u.loc["cr_water", "usd_central"])
    cost_month = chw_cost + water_cost
    detect = min(1.0, q["illness_weeks"] / chw_interval_weeks)                                                # chance a case overlaps a visit
    red_found = reached * q["monthly_incidence"] * detect * (1 - q["chw_share"])
    return {"chw_interval_weeks": chw_interval_weeks, "water_interval_months": water_interval_months, "visits_per_month": visits_month, "chws_needed": n_chw, "cost_per_month_usd": cost_month,
            "red_flags_found_per_month": red_found, "cost_per_red_flag_usd": cost_month / red_found if red_found > 0 else np.nan, "expected_wait_days": chw_interval_weeks * 7 / 2,
            "water_samples_per_year": tests_year, "samples_per_source_per_year": 12 / water_interval_months, "meets_gdwq_floor": bool(12 / water_interval_months >= GDWQ_MIN_SAMPLES_PER_YEAR)}


def compare_schedules(people: float, n_sources: int = 5, p: dict | None = None) -> pd.DataFrame:
    rows = [schedule(people, n_sources, wk, mo, p) for wk in (1, 2) for mo in (1, 3)]
    d = pd.DataFrame(rows)
    d['gdwq_floor_ok'] = d.meets_gdwq_floor                      # per supply: at least 12 samples a year (monthly); quarterly water tests fall below the WHO floor
    return d


def route_red_flags(sites: pd.DataFrame, centres: pd.DataFrame, tt: pd.DataFrame, red_flags: dict, p: dict | None = None, max_minutes: float = 30.0) -> pd.DataFrame:
    """Assign each site's red flags to the reachable centre (<= max_minutes) with the most remaining spare capacity. Spare = spare_share x weekly capacity x 52 (spare_share is an
    assumption; no occupancy data exists). Returns site, centre, flags, load share and a flag if the added load exceeds LOAD_LIMIT of the centre's yearly capacity."""
    q = {**DEFAULTS, **(p or {})}
    cap = centres.set_index("facility_id").capacity_weekly.astype(float) * 52
    spare = cap * q["spare_share"]
    used = {k: 0.0 for k in cap.index}
    rows = []
    for s in sites.itertuples():
        t = tt[(tt.cadaster_id == s.cadaster_id) & tt.facility_id.isin(cap.index) & (tt.minutes <= max_minutes)]
        n = float(red_flags.get(s.cadaster_id, 0.0))
        if t.empty:
            rows.append({"cadaster_id": s.cadaster_id, "facility_id": None, "red_flags": n, "minutes": np.nan, "added_load_share": np.nan, "over_limit": False, "reachable": False})
            continue
        best = max(t.facility_id, key=lambda f: spare[f] - used[f])
        used[best] += n
        rows.append({"cadaster_id": s.cadaster_id, "facility_id": best, "red_flags": n, "minutes": float(t[t.facility_id == best].minutes.iloc[0]), "reachable": True})
    r = pd.DataFrame(rows)
    load = r.groupby("facility_id").red_flags.sum() / cap
    r["added_load_share"] = r.facility_id.map(load)
    r["over_limit"] = r.added_load_share > LOAD_LIMIT
    return r


def break_even_chw_share(sites: pd.DataFrame, centres: pd.DataFrame, tt: pd.DataFrame, people: dict, p: dict | None = None) -> float | None:
    """Smallest CHW-handled share that keeps every centre under LOAD_LIMIT (bisection). None if even 100% still breaches (cannot happen: no red flags) or none breaches at 0."""
    q = {**DEFAULTS, **(p or {})}

    def worst(share):
        rf = {cid: funnel(n, {**q, "chw_share": share}).set_index("stage").people["red flags referred"] for cid, n in people.items()}
        r = route_red_flags(sites, centres, tt, rf, q)
        return float(r.added_load_share.max()) if r.added_load_share.notna().any() else 0.0
    if worst(0.0) <= LOAD_LIMIT:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if worst(m) > LOAD_LIMIT else (lo, m)
    return hi


def inputs_for(ranked: pd.DataFrame, top_n: int = 8):
    """Convenience: top start sites, MoPH-list PHCs and travel times for routing."""
    sites = ranked.head(top_n)[["cadaster_id", "cadaster_name", "settlement_people_2016"]]
    fac = load_dataset("facilities").df
    tt = load_dataset("travel_time").df
    return sites, fac[fac.type == "PHC"], tt
