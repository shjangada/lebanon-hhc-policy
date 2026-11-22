"""Start-site scorer: where is the pilot cheapest to start and most useful?

Criteria (each scaled 0-1; weights are sliders, default equal; all from processed data):
  soil       a soil result within 15 km exists (no new baseline sampling needed)          M2 `soil_sampled_nearby`
  host       a funded host project in the district: page-verified 1.0, partly verified 0.5, unverified 0.25 (host projects are OPTIONAL: they only lower the cost)   riders.csv
  centre     a reachable MoPH-list centre with room: E2SFCA access, scaled 0-1              M1 (capacity is ASSUMED: centres 300/week; ranking stable at 200-400)
  settlements informal-settlement population in the cadaster (IAMP Dec 2016: OLD)           informal_settlements.csv
  outreach   a named outreach operator covers the district (frequency not published)        outreach.csv
  disease    reported hepatitis A + typhoid per 10,000, district, 2023-2025 mean (ESU)      esu_by_district.csv (notified cases, under-reported)
  need       M2 need score (district-reliable; cadaster = screening)                         m2_need_score
Startup cost = only the pieces still missing, from sourced unit prices (cost_ranges, prices_pack): a baseline soil sample set if no soil result is near; Cr(VI) speciation if a chromium
finding is near (the one test that decides the response); water tests for N wells (water exposure is unknown everywhere); filters or chlorine for households in settlements;
CHW months. Counts are parameters, not facts. `zero_data_cost` is the same package for a site with no soil result and no host project."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import m1_access, m2_need_score as m2, riders
from .io import PROCESSED, load_dataset

CRITERIA = ["soil", "host", "centre", "settlements", "outreach", "disease", "need"]
DEFAULT_PARAMS = dict(n_wells=20, n_soil=10, n_cr6=10, hh_size=4.6, chw_months=6, filter_share=1.0)
OUTREACH_DISTRICT_WORDS = {"Hermel": ["hermel"], "Baalbek": ["baalbek", "arsal", "yohmor"], "Zahle": ["zahle", "maalaqa", "bar elias"], "West Bekaa": ["west bekaa", "kamed el loz", "jeb jenine", "mashghara"],
                           "Rachaya": ["rachaya"]}


def _prices(prices: pd.DataFrame | None = None) -> dict:
    pk = prices if prices is not None else pd.read_csv(PROCESSED / "prices_pack.csv")
    u = riders.unit_prices().set_index("unit")
    filt = pk[pk["item"].str.startswith("Household ceramic water filter")].iloc[0]
    return {"nitrate": tuple(u.loc["nitrate_water", ["usd_low", "usd_central", "usd_high"]]), "cr_water": tuple(u.loc["cr_water", ["usd_low", "usd_central", "usd_high"]]),
            "soil": tuple(u.loc["soil_total_cr", ["usd_low", "usd_central", "usd_high"]]), "chw": tuple(u.loc["chw_month", ["usd_low", "usd_central", "usd_high"]]),
            "filter": (float(filt.low), float(filt.central), float(filt.high)),         # UNICEF catalogue per household filter (ex-works; excludes freight and distribution)
            "cr6": (40.0, 76.0, 80.25)}      # US prices only (no Lebanese price): $40 soil (2024 list), $74.90 water (Westchester Co. NY 2025), $77 soil (c. 2008), $80.25 solid (2025); central = their median


def disease_rate(esu: pd.DataFrame | None = None, pop: pd.DataFrame | None = None) -> pd.Series:
    """Reported hepatitis A + typhoid cases per 10,000 people, by district, mean of 2023-2025 (2026 is a partial year; late-2025 zeros are lag)."""
    d = esu if esu is not None else pd.read_csv(PROCESSED / "esu_by_district.csv")
    d = d[(d.mohafaza_file == "Bekaa") & (d.geo_level == "caza") & d.year.between(2023, 2025) & d.disease.str.contains("Hepatitis A|Typhoid", case=False, regex=True)]
    cases = d.groupby(["district_clean", "year"]).cases.sum().groupby("district_clean").mean()
    p = pop if pop is not None else load_dataset("population").df.merge(load_dataset("cadasters").df[["cadaster_id", "district"]], on="cadaster_id")
    return (cases / p.groupby("district").population_total.sum() * 1e4).dropna()


def outreach_districts(out: pd.DataFrame | None = None) -> set:
    o = out if out is not None else pd.read_csv(PROCESSED / "outreach.csv")
    o = o[o.units.fillna("").str.upper().str.contains("NOT FOUND") == False]                      # noqa: E712
    text = (o.district.fillna("") + " " + o.service.fillna("")).str.lower()
    named = o[~o.district.fillna("").str.lower().str.startswith("national")]
    t = (named.district.fillna("") + " " + named.service.fillna("")).str.lower()
    return {d for d, words in OUTREACH_DISTRICT_WORDS.items() if any(w in " ".join(t) for w in words)} if len(named) else set()


def criteria(scored: pd.DataFrame | None = None, rid: pd.DataFrame | None = None) -> pd.DataFrame:
    raw = m2.raw_indicators()
    sc = scored if scored is not None else m2.compute(raw, spec=m2.apply_quantile_anchors(m2.load_spec(), raw))
    cad = sc[["cadaster_id", "cadaster_name", "district", "lat", "lon", "need_score", "rank", "soil_sampled_nearby", "nearest_soil_site_km", "soil_hq_high_nearby", "population_total"]].copy()
    r = rid if rid is not None else pd.read_csv(PROCESSED / "riders.csv")
    yes, partly = r[r.verified == "yes"], r[r.verified == "partly"]
    cad["host_projects"] = cad.district.map(lambda d: int(r.districts.fillna("").str.contains(d).sum()))
    cad["host_verified"] = cad.district.map(lambda d: int(yes.districts.fillna("").str.contains(d).sum()))
    cad["host_partly"] = cad.district.map(lambda d: int(partly.districts.fillna("").str.contains(d).sum()))
    acc = m1_access.access_by_cadaster(30, "women_15_49")[["cadaster_id", "access_current"]]
    cad = cad.merge(acc, on="cadaster_id")
    s = pd.read_csv(PROCESSED / "informal_settlements.csv", dtype={"cadaster_id": str}).groupby("cadaster_id").individuals.sum().rename("settlement_people_2016")
    cad = cad.merge(s, on="cadaster_id", how="left")
    cad["settlement_people_2016"] = cad.settlement_people_2016.fillna(0)
    od = outreach_districts()
    cad["outreach_operator"] = cad.district.isin(od)
    dr = disease_rate()
    cad["waterborne_per_10k"] = cad.district.map(dr)
    rb = pd.read_csv(PROCESSED / "robust_rank_per_cadaster.csv", dtype={"cadaster_id": str}) if (PROCESSED / "robust_rank_per_cadaster.csv").exists() else None
    cad["robust_core"] = cad.cadaster_id.isin(rb[rb["core"]].cadaster_id) if rb is not None and "cadaster_id" in rb else False
    c = pd.DataFrame({"cadaster_id": cad.cadaster_id})
    c["soil"] = cad.soil_sampled_nearby.astype(float)
    c["host"] = np.where(cad.host_verified > 0, 1.0, np.where(cad.host_partly > 0, 0.5, np.where(cad.host_projects > 0, 0.25, 0.0)))   # page-verified host 1.0; partly verified 0.5; unverified 0.25; none 0
    c["centre"] = (cad.access_current.rank(pct=True)).astype(float)
    c["settlements"] = np.minimum(1.0, cad.settlement_people_2016 / max(cad.settlement_people_2016.quantile(0.9), 1))
    c["outreach"] = cad.outreach_operator.astype(float)
    c["disease"] = (cad.waterborne_per_10k.rank(pct=True)).fillna(0.0)
    c["need"] = cad.need_score.clip(0, 1)
    return cad.merge(c, on="cadaster_id")


def startup_cost(cad: pd.DataFrame, params: dict | None = None, prices: dict | None = None) -> pd.DataFrame:
    p = {**DEFAULT_PARAMS, **(params or {})}
    pr = prices or _prices()
    out = []
    for tag, i in (("low", 0), ("central", 1), ("high", 2)):
        wells = p["n_wells"] * (pr["nitrate"][i] + pr["cr_water"][i])
        soil = np.where(cad.soil_sampled_nearby, 0.0, p["n_soil"] * pr["soil"][i])
        cr6 = np.where((cad.soil_hq_high_nearby > 0), p["n_cr6"] * pr["cr6"][i], 0.0)
        hh = cad.settlement_people_2016 / p["hh_size"] * p["filter_share"]
        kits = hh * pr["filter"][i]
        chw = p["chw_months"] * pr["chw"][i]
        out.append(pd.Series(wells + soil + cr6 + kits + chw, name=f"startup_{tag}_usd"))
    zero = {t: p["n_wells"] * (pr["nitrate"][i] + pr["cr_water"][i]) + p["n_soil"] * pr["soil"][i] + p["chw_months"] * pr["chw"][i] for t, i in (("low", 0), ("central", 1), ("high", 2))}
    r = pd.concat(out, axis=1).round(0)
    r["zero_data_site_central_usd"] = round(zero["central"])
    return r


def score(weights: dict | None = None, params: dict | None = None, scored: pd.DataFrame | None = None, rid: pd.DataFrame | None = None) -> pd.DataFrame:
    cad = criteria(scored, rid)
    w = {k: 1.0 for k in CRITERIA}
    w.update(weights or {})
    if sum(w.values()) <= 0:                                           # every weight set to zero: fall back to equal weights instead of dividing by zero
        w = {k: 1.0 for k in CRITERIA}
    tot = sum(w.values())
    cad["start_score"] = sum(cad[k] * w[k] for k in CRITERIA) / tot
    cad = pd.concat([cad, startup_cost(cad, params)], axis=1)
    cad["start_rank"] = cad.start_score.rank(ascending=False, method="min").astype(int)
    return cad.sort_values("start_rank")


def clusters(ranked: pd.DataFrame, radius_km: float = 8.0, top: int = 40) -> pd.DataFrame:
    """Group the top cadasters into clusters within `radius_km` of each other (the pilot runs one outreach circuit): greedy by score."""
    t = ranked.head(top).copy()
    left, out = list(t.index), []
    while left:
        i = left[0]
        near = [j for j in left if m2._hav(t.at[i, "lat"], t.at[i, "lon"], t.at[j, "lat"], t.at[j, "lon"]) <= radius_km]
        g = t.loc[near]
        out.append({"cluster_lead": t.at[i, "cadaster_name"], "district": t.at[i, "district"], "members": ", ".join(g.cadaster_name), "n": len(g), "mean_start_score": g.start_score.mean(),
                    "startup_central_usd": g.startup_central_usd.sum(), "settlement_people_2016": g.settlement_people_2016.sum()})
        left = [j for j in left if j not in near]
    return pd.DataFrame(out).sort_values("mean_start_score", ascending=False).reset_index(drop=True)


def rank_stability(cad: pd.DataFrame | None = None, n: int = 1000, seed: int = 42) -> dict:
    """How stable is the start-site ranking? Three perturbations of the criterion weights (equal weights are the centre):
      random: `n` Dirichlet(1,...,1) weight draws; perturb: each weight scaled by a random factor in [0.75, 1.25] (n draws); leave-one-out: drop each criterion in turn.
    Returns per-cadaster shares of draws in the top 1 / 3 / 10, mean rank, the baseline #1, and summary booleans. Scores are computed on the 0-1 criteria; no model is re-run."""
    c = cad if cad is not None else criteria()
    X = c[CRITERIA].values.astype(float)
    rng = np.random.default_rng(seed)
    base_w = np.ones(len(CRITERIA))
    draws = {"random": rng.dirichlet(np.ones(len(CRITERIA)), n), "perturb": base_w * rng.uniform(0.75, 1.25, (n, len(CRITERIA))),
             "leave_one_out": np.array([np.where(np.arange(len(CRITERIA)) == i, 0.0, 1.0) for i in range(len(CRITERIA))])}
    out, summary = c[["cadaster_id", "cadaster_name", "district"]].copy(), {}
    base_scores = X @ base_w
    base_first = int(np.argmax(base_scores))
    for name, W in draws.items():
        S = X @ W.T                                                  # cadasters x draws
        R = (-S).argsort(axis=0).argsort(axis=0) + 1
        out[f"top1_{name}"] = (R == 1).mean(axis=1)
        out[f"top3_{name}"] = (R <= 3).mean(axis=1)
        out[f"top10_{name}"] = (R <= 10).mean(axis=1)
        out[f"mean_rank_{name}"] = R.mean(axis=1)
        summary[name] = {"baseline_first_site": c.cadaster_name.iloc[base_first], "baseline_first_share_top1": float((R[base_first] == 1).mean()), "baseline_first_share_top3": float((R[base_first] <= 3).mean()),
                         "most_frequent_first": c.cadaster_name.iloc[int(np.argmax((R == 1).mean(axis=1)))], "n_draws": int(W.shape[0])}
    # district view: how often is the top site in each district
    tops = {}
    for name, W in draws.items():
        first = np.argmax(X @ W.T, axis=0)
        tops[name] = pd.Series(c.district.values[first]).value_counts(normalize=True).round(3).to_dict()
    summary["district_of_first_site"] = tops
    summary["first_site_stable"] = bool(summary["random"]["baseline_first_share_top3"] >= 0.5)
    return {"per_cadaster": out.sort_values("top3_random", ascending=False).reset_index(drop=True), "summary": summary}
