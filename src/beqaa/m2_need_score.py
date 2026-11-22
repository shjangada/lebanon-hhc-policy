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


def PROCESSED_WBD() -> set:
    """p-codes of Beqaa-valley cadasters in the WaSH 2024 water-borne-disease top-20 (matched by name in ingest/pilot_data.py)."""
    import pathlib
    f = pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "wbd_risk.csv"
    if not f.exists():
        return set()
    r = pd.read_csv(f, dtype={"cadaster_id": str})
    return set(r[(r.in_beqaa_valley == "yes") & r.cadaster_id.notna()].cadaster_id)


def _waterborne_rate() -> pd.Series:
    import pathlib
    if not (pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "esu_by_district.csv").exists():
        return pd.Series(dtype=float)
    from . import start_site
    return start_site.disease_rate()


def raw_indicators(d0: float = 30, demand_col: str = "women_15_49", include_unregistered: bool = True,
                   cr6_for_tier: float | None = None) -> pd.DataFrame:
    """Raw indicator values per cadaster (before scaling), plus stress-layer columns."""
    cad, m0 = load_dataset("cadasters")
    pop, m1 = load_dataset("population")
    fac, _ = load_dataset("facilities")
    tt, _ = load_dataset("travel_time")
    vul, _ = load_dataset("vulnerability")
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
    op = m1_access.effective_facilities(fac)
    t = tt[tt.facility_id.isin(op.facility_id) & (tt.minutes <= 30)].merge(op[["facility_id", "type", "offers_anc"]], on="facility_id")
    phc = t[t.type == "PHC"].groupby("cadaster_id").size().rename("phc_30")
    anc = t.groupby("cadaster_id").offers_anc.mean().rename("anc_share_30min")
    df = df.merge(phc, on="cadaster_id", how="left").merge(anc, on="cadaster_id", how="left")
    df["phc_30"] = df.phc_30.fillna(0)
    df["anc_share_30min"] = df.anc_share_30min.fillna(0)
    df["phc_per_50k"] = df.phc_30 / df.population_total * 50_000
    # vulnerability (district value applied to cadaster in mock; real = finer)
    df = df.merge(vul.drop(columns=[c for c in ("level", "is_mock", "source", "source_date", "url", "status") if c in vul.columns]), on="cadaster_id", how="left")
    # security exposure: conflict incidents since Oct 2023 (real source: LRP 2026 package, admin 3)
    ce, _ = load_dataset("conflict_exposure")
    df = df.merge(ce[["cadaster_id", "conflict_incidents"]], on="cadaster_id", how="left")
    df["conflict_incidents"] = df.conflict_incidents.fillna(0)
    # environment: soil hotspot proximity (tier x distance decay) + nitrate
    # M4 -> M2 link: soil tiers (Cr tier depends on the assumed Cr(VI) share; default precautionary) decay with distance (15 km)
    sites = m4_exposure.screen_sites(cr6_for_tier=cr6_for_tier)
    prox, spec_unc, rung_b, hq_near, nearest = [], [], [], [], []
    for r in df.itertuples():
        v = u = b = h = 0.0
        dmin = np.inf
        for s in sites.itertuples():
            if np.isnan(s.lat):
                continue
            dist = _hav(r.lat, r.lon, s.lat, s.lon)
            dmin = min(dmin, dist)
            decay = max(0.0, 1 - dist / 15.0)
            v = max(v, s.tier * decay)
            u = max(u, float(s.speciation_decisive) * decay)          # nearby result whose tier hinges on Cr(VI) speciation
            b = max(b, float(s.evidence_rung == "b") * decay)         # plausible pathway, health effect not demonstrated
            if not np.isnan(s.hq_high):
                h = max(h, s.hq_high * decay)
        prox.append(v); spec_unc.append(u); rung_b.append(b); hq_near.append(h); nearest.append(dmin)
    df["nearest_soil_site_km"] = nearest
    df["soil_sampled_nearby"] = df.nearest_soil_site_km < 15.0         # a result within the 15 km decay radius exists
    df["soil_hotspot_proximity"] = prox
    df["speciation_uncertainty_nearby"] = spec_unc
    df["rung_b_exposure_nearby"] = rung_b
    df["soil_hq_high_nearby"] = hq_near
    # Water exposure is UNKNOWN for every cadaster: no public Beqaa well data exists, so nitrate is never scored (indicator skipped; every cadaster is a water evidence gap).
    df["nitrate_mg_l"] = np.nan
    df["nitrate_imputed"] = True
    # WaSH water-borne-disease risk map (2024): 1 for a matched top-20 cadaster, unknown (NaN) otherwise: absence from the list is not evidence of safety
    wbd = PROCESSED_WBD()
    df["wbd_risk_top20"] = df.cadaster_id.isin(wbd).astype(float).where(df.cadaster_id.isin(wbd))
    df["env_evidence"] = df.soil_sampled_nearby | df.wbd_risk_top20.notna()
    # reported hepatitis A + typhoid per 10,000 by district (MoPH ESU, 2023-2025 mean): clinical-demand context at district resolution
    df["waterborne_per_10k"] = df.district.map(_waterborne_rate())
    # NGO-dependency stress (not a Need Score domain; drives the escrow switch): 1 - share funds managed locally (latest actual year)
    g = gov[~gov.projected.astype(bool)]
    g = g[g.year == g.year.max()][["district", "share_funds_managed_locally", "admin_capacity_index"]]
    df = df.merge(g, on="district", how="left")
    df["ngo_dependency"] = 1 - df.share_funds_managed_locally
    df["is_mock"] = bool(m0 or m1)
    return df


def apply_quantile_anchors(spec: dict, raw: pd.DataFrame, lo: float = 0.10, hi: float = 0.90) -> dict:
    """Decision D6: where no published threshold exists (anchor: quantile), set safe/crisis to the 10th/90th percentile of the real data
    (goalposts observed in the data, as the HDI does with min/max). Direction (higher/lower is worse) is kept."""
    import copy
    spec = copy.deepcopy(spec)
    for inds in spec["domains"].values():
        for ind in inds:
            if ind.get("anchor") == "quantile" and ind["name"] in raw.columns:
                a, b = float(raw[ind["name"]].quantile(lo)), float(raw[ind["name"]].quantile(hi))
                if b > a:
                    ind["safe"], ind["crisis"] = (a, b) if ind["crisis"] > ind["safe"] else (b, a)
                    ind["status"] = "assumption (data-derived anchors)"
    return spec


def domain_matrix(scored: pd.DataFrame, domains: list[str] | None = None) -> np.ndarray:
    """Cadaster x domain scores; the environment column is NaN where there is no environmental evidence (see compute(env_unknown=))."""
    doms = domains or DOMAINS
    return np.column_stack([scored["D_environment_known"].values if d == "environment" and "D_environment_known" in scored else scored[f"D_{d}"].values for d in doms])


def aggregate_scores(D: np.ndarray, w: np.ndarray, agg: str = "arithmetic") -> np.ndarray:
    """Need score from a (cadasters x domains) matrix with NaN = unknown: weights are re-normalised per cadaster over the domains that have evidence."""
    ok = ~np.isnan(D)
    W = np.where(ok, w, 0.0)
    W = W / W.sum(axis=1, keepdims=True)
    Dz = np.where(ok, D, 0.0)
    if agg == "geometric":
        return np.exp((np.where(ok, np.log(np.clip(Dz, 1e-3, 1)), 0.0) * W).sum(axis=1))
    if agg == "max":
        return np.where(ok, D, -np.inf).max(axis=1)
    return (Dz * W).sum(axis=1)


def compute(raw: pd.DataFrame, weights: dict | None = None, spec: dict | None = None, geometric: bool = False,
            domains_on: list[str] | None = None, exclude_indicators: list[str] | None = None,
            aggregation: str | None = None, normalization: str = "goalpost", env_unknown: str = "unknown") -> pd.DataFrame:
    """aggregation: arithmetic (default) | geometric | max (JIAF-style 'worst domain'); normalization: goalpost (default, safe/crisis anchors)
    | percentile (SVI-style rank within the cadasters). See docs/METHODS_DECISIONS.md D2-D4.
    env_unknown: what an UNSAMPLED cadaster (no soil result within 15 km and no measured well) gets for the environment domain.
      unknown (default): D_environment_known = NaN and that cadaster's other domains are re-weighted (no evidence is not evidence of safety);
      zero: legacy behaviour (unsampled = no exposure); conflict_prior: use the conflict-incident score as a strike-damage proxy prior."""
    aggregation = aggregation or ("geometric" if geometric else "arithmetic")
    spec = spec or load_spec()
    w = dict(weights or spec["domain_weights"])
    on = [d for d in (domains_on or DOMAINS) if w.get(d, 0) > 0]
    tot = sum(w[d] for d in on)
    wn = {d: w[d] / tot for d in on}
    out = raw.copy()
    skipped = []
    for d in DOMAINS:
        cols = []
        for ind in spec["domains"][d]:
            if exclude_indicators and ind["name"] in exclude_indicators:
                continue
            if ind["name"] not in raw.columns or raw[ind["name"]].isna().all():     # missing (stale data, or a column still waiting for its source): skip visibly
                skipped.append(ind["name"])
                continue
            col = f"s_{ind['name']}"
            if normalization == "percentile":
                pr = raw[ind["name"]].rank(pct=True, method="average")
                out[col] = pr if ind["crisis"] > ind["safe"] else 1 - pr
            else:
                out[col] = score_indicator(raw[ind["name"]], ind["safe"], ind["crisis"])
            cols.append(col)
        out[f"D_{d}"] = out[cols].mean(axis=1, skipna=True) if cols else 0.0
    gap = ~out["env_evidence"].astype(bool) if "env_evidence" in out else pd.Series(False, index=out.index)
    out["env_evidence_gap"] = gap
    out["D_environment_known"] = out["D_environment"].where(~gap)
    if env_unknown == "zero":
        out.loc[gap, "D_environment"] = 0.0
        out["D_environment_known"] = out["D_environment"]
    elif env_unknown == "conflict_prior" and "s_conflict_incidents" in out:
        out.loc[gap, "D_environment"] = out.loc[gap, "s_conflict_incidents"]
        out["D_environment_known"] = out["D_environment"]
    else:                                                         # unknown: keep a plain 0 in D_environment for charts, but score without the domain
        out["D_environment_known"] = out["D_environment"].where(~gap)
        out.loc[gap, "D_environment"] = 0.0
    D = np.column_stack([out["D_environment_known"].values if d == "environment" else out[f"D_{d}"].values for d in on])
    wv = np.array([wn[d] for d in on])
    out["need_score"] = aggregate_scores(D, wv, aggregation)      # per-cadaster re-weighting over the domains that have evidence
    out["rank"] = out.need_score.rank(ascending=False, method="min").astype(int)
    t = spec["tiers"]
    out["tier"] = np.where(out.need_score >= t["high"], "High", np.where(out.need_score >= t["moderate"], "Moderate", "Low"))
    # stress layers (0-1) for the map selector (providership/referral/NGO-dependency layers removed: no public source)
    out["stress_need"] = out.need_score
    out["stress_environment"] = out["D_environment"]
    out.attrs["weights_used"] = wn
    out.attrs["skipped_indicators"] = skipped
    return out


def robustness(raw: pd.DataFrame, n: int = 5000, seed: int = 42, top_k: int | None = None, spec: dict | None = None,
               geometric: bool = False, domains_on: list[str] | None = None) -> pd.DataFrame:
    """Dirichlet(1,..,1) draws over domain weights (uniform on the simplex): rank intervals + p_top_tier."""
    spec = spec or load_spec()
    k = top_k or spec["top_k"]
    base = compute(raw, spec=spec, geometric=geometric, domains_on=domains_on)
    on = [d for d in (domains_on or DOMAINS)]
    D = domain_matrix(base, on)
    rng = np.random.default_rng(seed)
    W = rng.dirichlet(np.ones(len(on)), n)                       # n x d
    S = np.column_stack([aggregate_scores(D, W[j], "geometric" if geometric else "arithmetic") for j in range(n)])   # cadaster x draws
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


def method_sensitivity(raw: pd.DataFrame, spec: dict | None = None, top_k: int | None = None) -> pd.DataFrame:
    """Does the ranking depend on our methodological choices? (JRC handbook: test alternative normalisation, aggregation, weights, exclusions.)
    Each variant is compared with the reference configuration (goalpost normalisation, arithmetic mean, spec weights)."""
    from scipy.stats import spearmanr
    spec = spec or load_spec()
    k = top_k or spec["top_k"]
    ref = compute(raw, spec=spec)
    ref_top = set(ref.nsmallest(k, "rank").cadaster_id)
    variants = {"reference": {}, "aggregation: geometric": {"aggregation": "geometric"}, "aggregation: max (worst domain, JIAF-style)": {"aggregation": "max"},
                "normalisation: percentile rank (SVI-style)": {"normalization": "percentile"},
                "weights: vulnerability-heavy (0.4)": {"weights": {"clinical_demand": 0.2, "capacity_strain": 0.2, "vulnerability": 0.4, "environment": 0.2}},
                "weights: access-heavy (0.4)": {"weights": {"clinical_demand": 0.2, "capacity_strain": 0.4, "vulnerability": 0.2, "environment": 0.2}},
                "weights: clinical-heavy (0.4)": {"weights": {"clinical_demand": 0.4, "capacity_strain": 0.2, "vulnerability": 0.2, "environment": 0.2}}}
    for d in DOMAINS:
        variants[f"drop domain: {d}"] = {"domains_on": [x for x in DOMAINS if x != d]}
    variants["drop indicator: unregistered_workers_share"] = {"exclude_indicators": ["unregistered_workers_share"]}
    rows = []
    for name, kw in variants.items():
        s = compute(raw, spec=spec, **kw)
        top = set(s.nsmallest(k, "rank").cadaster_id)
        rows.append({"variant": name, "spearman_vs_reference": float(spearmanr(ref.need_score, s.need_score)[0]),
                     "top_k_retained": len(top & ref_top), "top_k": k, "top_k_jaccard": len(top & ref_top) / len(top | ref_top),
                     "max_rank_shift": int((s["rank"] - ref["rank"]).abs().max()), "is_mock": bool(raw.is_mock.all())})
    return pd.DataFrame(rows)


def exposure_access_targets(scored: pd.DataFrame, env_min: float = 0.33, deficit_min: float = 0.5) -> pd.DataFrame:
    """P1c: cadasters with HIGH environmental exposure (M4 tier-based environment domain) and LOW access (access deficit vs the pre-2026 median).
    This set is the core target list for the memo. Both thresholds are assumptions (env 0.33 = 'Moderate' band; deficit 0.5 = half the pre-2026 access lost)."""
    t = scored[(scored["D_environment"] >= env_min) & (scored["access_deficit"] >= deficit_min)].copy()
    t["why"] = "environmental exposure tier >= moderate AND access deficit >= 50%: exposure findings are screening-level (rung a/b), access gap is modelled"
    return t.sort_values(["access_deficit", "D_environment"], ascending=False)[["cadaster_id", "cadaster_name", "district", "D_environment", "access_deficit", "need_score", "why"]]
