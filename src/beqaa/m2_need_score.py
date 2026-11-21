"""M2: Beqaa Need Score. Answers Q1, Q5.

s = clip((x - safe)/(crisis - safe), 0, 1); domain = mean of its indicators; NeedScore = sum_d w_d D_d
(weights renormalised over active domains; optional weighted geometric mean = non-compensatory).
The paper (Barake et al.) gives no formula/weights/thresholds: everything here is our operationalisation.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import yaml

from . import equity, m1_access, m4_exposure
from .io import ROOT, load_dataset

PATH = ROOT / "data" / "params" / "need_score_indicators.yaml"
DOMAINS = ["clinical_demand", "capacity_strain", "vulnerability", "environment"]


def load_spec(path=None) -> dict:
    return yaml.safe_load(open(path or PATH))


def _hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    x = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def score_indicator(x: pd.Series, safe: float, crisis: float) -> pd.Series:
    return ((x - safe) / (crisis - safe)).clip(0, 1)


def raw_indicators(d0: float = 30, demand_col: str = "women_15_49", include_unregistered: bool = True) -> pd.DataFrame:
    """Raw indicator values per cadaster (before scaling), plus stress-layer columns."""
    cad, m0 = load_dataset("cadasters")
    pop, m1 = load_dataset("population")
    fac, _ = load_dataset("facilities")
    tt, _ = load_dataset("travel_time")
    vul, _ = load_dataset("vulnerability")
    stf, _ = load_dataset("staffing_referrals")
    gov, _ = load_dataset("governance_capacity")
    acc = m1_access.access_by_cadaster(d0, demand_col)
    prov = ["is_mock", "source", "source_date", "url", "status"]
    df = cad[["cadaster_id", "cadaster_name", "district", "governorate", "lat", "lon"]].merge(
        pop.drop(columns=[c for c in prov if c in pop.columns]), on="cadaster_id")
    df["pregnant_per_1000"] = df.pregnant_est / df.population_total * 1000
    df["women_share"] = df.women_15_49 / df.population_total
    df["unregistered_workers_share"] = df.unregistered_workers_est / df.population_total if include_unregistered else 0.0
    # capacity: access deficit relative to pre-2026 median
    ref = acc.access_baseline.median()
    acc["access_deficit"] = 1 - (acc.access_current / ref).clip(0, 1)
    df = df.merge(acc[["cadaster_id", "access_baseline", "access_current", "access_lost", "access_deficit"]], on="cadaster_id")
    # open PHCs and ANC share within 30 min
    op = fac[(fac.status_2026 == "open")]
    t = tt[tt.facility_id.isin(op.facility_id) & (tt.minutes <= 30)].merge(op[["facility_id", "type", "offers_anc"]], on="facility_id")
    phc = t[t.type == "PHC"].groupby("cadaster_id").size().rename("phc_30")
    anc = t.groupby("cadaster_id").offers_anc.mean().rename("anc_share_30min")
    df = df.merge(phc, on="cadaster_id", how="left").merge(anc, on="cadaster_id", how="left")
    df["phc_30"] = df.phc_30.fillna(0)
    df["anc_share_30min"] = df.anc_share_30min.fillna(0)
    df["phc_per_50k"] = df.phc_30 / df.population_total * 50_000
    # facility-level stress mapped to cadaster via nearest open PHC (by travel time)
    stf = stf.assign(posts_unfilled_share=1 - stf.posts_filled / stf.posts_budgeted,
                     referral_completion=stf.referral_completed_month / stf.referral_sent_month)
    stf["referral_incompletion"] = 1 - stf.referral_completion
    phcs = fac[fac.type == "PHC"][["facility_id"]].merge(stf, on="facility_id")
    tn = tt[tt.facility_id.isin(phcs.facility_id)].sort_values("minutes").drop_duplicates("cadaster_id")
    tn = tn.merge(phcs[["facility_id", "posts_unfilled_share", "referral_incompletion", "referral_completion"]], on="facility_id")
    df = df.merge(tn[["cadaster_id", "posts_unfilled_share", "referral_incompletion", "referral_completion"]], on="cadaster_id", how="left")
    # vulnerability (district value applied to cadaster in mock; real = finer)
    df = df.merge(vul.drop(columns=[c for c in ("level", "is_mock", "source", "source_date", "url", "status") if c in vul.columns]), on="cadaster_id", how="left")
    # environment: soil hotspot proximity (tier x distance decay) + nitrate
    sites = m4_exposure.screen_sites()
    prox = []
    for r in df.itertuples():
        v = 0.0
        for s in sites.itertuples():
            if np.isnan(s.lat):
                continue
            v = max(v, s.tier * max(0.0, 1 - _hav(r.lat, r.lon, s.lat, s.lon) / 15.0))
        prox.append(v)
    df["soil_hotspot_proximity"] = prox
    nit = m4_exposure.nitrate_by_cadaster()
    df = df.merge(nit, on="cadaster_id", how="left")
    df["nitrate_imputed"] = df.nitrate_mg_l.isna()
    df["nitrate_mg_l"] = df.nitrate_mg_l.fillna(df.groupby("district").nitrate_mg_l.transform("median")).fillna(df.nitrate_mg_l.median())
    # NGO-dependency stress (not a Need Score domain; drives the escrow switch): 1 - share funds managed locally (latest actual year)
    g = gov[~gov.projected.astype(bool)]
    g = g[g.year == g.year.max()][["district", "share_funds_managed_locally", "admin_capacity_index"]]
    df = df.merge(g, on="district", how="left")
    df["ngo_dependency"] = 1 - df.share_funds_managed_locally
    df["is_mock"] = bool(m0 or m1)
    return df


def compute(raw: pd.DataFrame, weights: dict | None = None, spec: dict | None = None, geometric: bool = False,
            domains_on: list[str] | None = None, exclude_indicators: list[str] | None = None) -> pd.DataFrame:
    spec = spec or load_spec()
    w = dict(weights or spec["domain_weights"])
    on = [d for d in (domains_on or DOMAINS) if w.get(d, 0) > 0]
    tot = sum(w[d] for d in on)
    wn = {d: w[d] / tot for d in on}
    out = raw.copy()
    for d in DOMAINS:
        cols = []
        for ind in spec["domains"][d]:
            if exclude_indicators and ind["name"] in exclude_indicators:
                continue
            col = f"s_{ind['name']}"
            out[col] = score_indicator(raw[ind["name"]], ind["safe"], ind["crisis"])
            cols.append(col)
        out[f"D_{d}"] = out[cols].mean(axis=1, skipna=True) if cols else 0.0
    D = out[[f"D_{d}" for d in on]].values
    wv = np.array([wn[d] for d in on])
    if geometric:
        out["need_score"] = np.exp((np.log(np.clip(D, 1e-3, 1)) * wv).sum(axis=1))
    else:
        out["need_score"] = (D * wv).sum(axis=1)
    out["rank"] = out.need_score.rank(ascending=False, method="min").astype(int)
    t = spec["tiers"]
    out["tier"] = np.where(out.need_score >= t["high"], "High", np.where(out.need_score >= t["moderate"], "Moderate", "Low"))
    # stress layers (0-1) for the map selector
    out["stress_need"] = out.need_score
    out["stress_providership"] = score_indicator(out.posts_unfilled_share, 0.10, 0.60)
    out["stress_referral"] = score_indicator(out.referral_incompletion, 0.20, 0.80)
    out["stress_ngo_dependency"] = out.ngo_dependency.clip(0, 1)
    out["stress_environment"] = out["D_environment"]
    out.attrs["weights_used"] = wn
    return out


def robustness(raw: pd.DataFrame, n: int = 5000, seed: int = 42, top_k: int | None = None, spec: dict | None = None,
               geometric: bool = False, domains_on: list[str] | None = None) -> pd.DataFrame:
    """Dirichlet(1,..,1) draws over domain weights (uniform on the simplex): rank intervals + p_top_tier."""
    spec = spec or load_spec()
    k = top_k or spec["top_k"]
    base = compute(raw, spec=spec, geometric=geometric, domains_on=domains_on)
    on = [d for d in (domains_on or DOMAINS)]
    D = base[[f"D_{d}" for d in on]].values
    rng = np.random.default_rng(seed)
    W = rng.dirichlet(np.ones(len(on)), n)                       # n x d
    if geometric:
        S = np.exp(np.log(np.clip(D, 1e-3, 1)) @ W.T)
    else:
        S = D @ W.T                                               # cadaster x draws
    ranks = (-S).argsort(axis=0).argsort(axis=0) + 1
    out = base[["cadaster_id", "cadaster_name", "district", "need_score", "rank"]].copy()
    out["p_top_tier"] = (ranks <= k).mean(axis=1)
    out["rank_p05"] = np.percentile(ranks, 5, axis=1).astype(int)
    out["rank_p50"] = np.percentile(ranks, 50, axis=1).astype(int)
    out["rank_p95"] = np.percentile(ranks, 95, axis=1).astype(int)
    out["rank_stable"] = (out.rank_p95 - out.rank_p05) <= 10
    out["is_mock"] = base.is_mock
    return out


def compare_official(scored: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """District comparison against JIAF 2.0 / FSA severity + cadasters that official district maps would hide."""
    sev, mock = load_dataset("official_severity")
    d = scored.groupby("district").agg(mean_need=("need_score", "mean"), max_need=("need_score", "max"),
                                         min_need=("need_score", "min")).reset_index()
    d = d.merge(sev[["district", "jiaf_severity", "health_severity", "fsa_composite_severity"]], on="district")
    d["rank_ours"] = d.mean_need.rank(ascending=False, method="min").astype(int)
    d["rank_jiaf"] = d.jiaf_severity.rank(ascending=False, method="min").astype(int)
    d["rank_diff"] = d.rank_jiaf - d.rank_ours
    d["within_district_spread"] = d.max_need - d.min_need
    d["note"] = np.where(d.rank_diff.abs() >= 2, "Differs from official ranking: check environment / equity domains",
                         np.where(d.within_district_spread > 0.25, "District average hides large within-district spread", "Broadly consistent"))
    d["is_mock"] = bool(mock)
    # cadasters with high need in districts the official map rates lower than the median
    s = scored.merge(sev[["district", "jiaf_severity"]], on="district")
    hidden = s[(s["rank"] <= 10) & (s.jiaf_severity < sev.jiaf_severity.median())][["cadaster_id", "cadaster_name", "district", "need_score", "rank", "jiaf_severity"]]
    hidden["why"] = "Top-10 cadaster inside a district rated below median by JIAF: finer resolution reveals it"
    return d, hidden


def group_need(scored: pd.DataFrame) -> pd.DataFrame:
    pop, _ = load_dataset("population")
    g = equity.by_group(scored, pop, ["need_score", "access_current"]).pivot(index="group", columns="metric", values="value").reset_index()
    return g


def triggers() -> pd.DataFrame:
    return pd.DataFrame([
        ("High", "Priority package: mobile maternal unit / voucher + CHW outreach, hub-spoke referral tracking, escrow need-floor release",
         "Quarterly Need Score refresh"),
        ("Moderate", "Standard package: PHC capacity top-up, referral tracking, outreach via women's organisations",
         "Biannual review"),
        ("Low", "Monitor only; re-score on any closure / displacement shock", "Annual review"),
    ], columns=["tier", "response_package", "review"])
