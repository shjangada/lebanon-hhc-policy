"""M2 x evidence: where is the evidence weakest, and which registry rows could fund implementation research there?

Flags districts / cadasters (and interventions) where a decision hinges on evidence we do not have:
  * speciation    - a nearby Cr result whose screening tier flips between Cr(III) and Cr(VI) (M4 HQ range straddles 1)
  * rung_b        - exposure pathway plausible (rung b) but no health effect demonstrated (rung c never assigned)
  * nitrate       - well nitrate imputed from the district median (no measurement in the cadaster)
  * rank          - need-score rank is unstable across random domain weightings (M2 robustness)
Interventions: every cost and lift in interventions.csv is MOCK, so effect size and unit cost are research questions.
The gap weights below are ASSUMPTIONS. Registry links come only from funding_registry.csv (never invented);
'closed' rows are excluded, 'closed_recurring' rows are shown as 'expected next round'.
"""
from __future__ import annotations

import pandas as pd

from . import funding_finder as ff
from .io import load_dataset

GAP_WEIGHTS = {"speciation": 0.35, "rung_b": 0.25, "nitrate": 0.15, "rank": 0.25}     # assumption
GAP_MIN = 0.40                                                                    # candidate threshold (assumption)

QUESTIONS = {
    "speciation": ("Is the soil chromium near here hexavalent? The answer moves the site between tier 0-1 (advice, monitoring) and tier 2 (washing water, screening, referral).",
                   "Cr(VI) speciation on ~10 samples through a university lab (AUB; cost in interventions.csv is mock: get a quote)",
                   ["climate & natural resources", "health", "recovery", "cooperatives", "livelihoods"], "cr_speciation_tests"),
    "rung_b": ("Does the exposure pathway reach people (crop uptake, hand-to-mouth, washing water)? Health effect is not demonstrated (rung b, not c).",
               "Crop-uptake sampling + diet survey of farming households; targeted blood-lead screening where Pb is elevated",
               ["health", "climate & natural resources", "cooperatives", "livelihoods"], "soil_water_screening"),
    "nitrate": ("Well nitrate is imputed from the district median: is the 50 mg/L guideline exceeded here?",
                "Nitrate test-strip / lab survey of wells used for drinking and washing",
                ["water", "infrastructure", "community"], "soil_water_screening"),
    "rank": ("Is this town really top-tier? Its rank depends on how domains are weighted.",
             "Collect the cadaster-level indicators that drive the split (vulnerability is district-level today) and agree weights with the community committee",
             ["humanitarian", "health", "community development", "civil society"], None),
}


def _registry_links(keywords: list[str], max_rows: int = 4) -> tuple[str, str]:
    try:
        f = ff.annotate(ff.load_funding())
    except FileNotFoundError:
        return "", "funding_registry.csv missing"
    f = ff.filter_funding(f, active_only=False, show_next_round=True)          # drops 'closed' and 'active_closed_to_new'
    m = ff.match_sectors(f, keywords)
    if m.empty:
        return "", "No verified entry; add one to the registry."
    m = ff.rank(m, keywords).sort_values(["sector_match", "involvement_score", "score"], ascending=False)
    m = m.head(max_rows)
    return "; ".join(m.fund_id), "; ".join(f"{r.fund_id} ({r.availability})" for r in m.itertuples())


def cadaster_gaps(scored: pd.DataFrame, rob: pd.DataFrame | None = None, need_min: float = 0.33, gap_min: float = GAP_MIN) -> pd.DataFrame:
    """One row per cadaster: gap components (0-1), evidence_gap_score, research_priority = need_score x gap, candidate flag."""
    d = scored[["cadaster_id", "cadaster_name", "district", "need_score"]].copy()
    d["gap_speciation"] = scored.get("speciation_uncertainty_nearby", 0.0)
    d["gap_rung_b"] = scored.get("rung_b_exposure_nearby", 0.0)
    d["gap_nitrate"] = scored.get("nitrate_imputed", False).astype(float) if "nitrate_imputed" in scored else 0.0
    if rob is not None:
        n = len(rob)
        width = rob.set_index("cadaster_id").reindex(d.cadaster_id)
        d["gap_rank"] = ((width.rank_p95 - width.rank_p05) / max(n - 1, 1)).clip(0, 1).values
    else:
        d["gap_rank"] = 0.0
    d["evidence_gap_score"] = sum(GAP_WEIGHTS[k] * d[f"gap_{k}"] for k in GAP_WEIGHTS)
    d["research_priority"] = d.need_score * d.evidence_gap_score
    d["candidate"] = (d.need_score >= need_min) & (d.evidence_gap_score >= gap_min)
    d["main_gap"] = d[[f"gap_{k}" for k in GAP_WEIGHTS]].mul(pd.Series({f"gap_{k}": w for k, w in GAP_WEIGHTS.items()})).idxmax(axis=1).str[4:]
    d["is_mock"] = bool(scored.is_mock.any()) if "is_mock" in scored else True
    return d.sort_values("research_priority", ascending=False).reset_index(drop=True)


def research_candidates(gaps: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """Candidates for implementation-research funding, with the question, study and registry rows whose sectors fit."""
    c = gaps[gaps.candidate].head(top)
    rows = []
    for r in c.itertuples():
        q, study, kw, iv = QUESTIONS[r.main_gap]
        ids, labels = _registry_links(kw)
        rows.append({"cadaster_name": r.cadaster_name, "district": r.district, "need_score": r.need_score,
                     "evidence_gap_score": r.evidence_gap_score, "main_gap": r.main_gap, "research_question": q, "study": study,
                     "related_intervention": iv or "", "registry_fund_ids": ids, "registry_rows": labels, "is_mock": r.is_mock})
    return pd.DataFrame(rows)


def district_gaps(gaps: pd.DataFrame) -> pd.DataFrame:
    g = gaps.groupby("district").agg(cadasters=("cadaster_id", "nunique"), candidates=("candidate", "sum"),
                                     mean_need=("need_score", "mean"), mean_gap=("evidence_gap_score", "mean"),
                                     max_research_priority=("research_priority", "max")).reset_index()
    g["main_gap"] = gaps.groupby("district").apply(lambda x: x.main_gap.mode().iat[0], include_groups=False).values
    return g.sort_values("max_research_priority", ascending=False).reset_index(drop=True)


def intervention_gaps(tornado: pd.DataFrame | None = None) -> pd.DataFrame:
    """Interventions whose effect size / unit cost are unsourced (mock) or which act on exposure with only rung-b evidence."""
    iv, mock = load_dataset("interventions")
    rows = []
    for r in iv.itertuples():
        gaps = []
        if mock or str(getattr(r, "status", "")) == "mock":
            gaps.append("unit cost and effect size are mock: needs a sourced quote / implementation study")
        if str(r.acts_on) in ("exposure", "environment") or not str(r.steps) or str(r.steps) == "nan":
            gaps.append("acts on exposure: health benefit not demonstrated (rung b)")
        kw = (["health", "climate & natural resources", "cooperatives", "water"] if "exposure" in " ".join(gaps)
              else ["health", "maternal", "referrals", "GBV"])
        ids, labels = _registry_links(kw)
        rows.append({"intervention_id": r.intervention_id, "label": r.label, "evidence_gaps": "; ".join(gaps),
                     "registry_fund_ids": ids, "registry_rows": labels, "is_mock": bool(mock)})
    out = pd.DataFrame(rows)
    if tornado is not None and len(tornado):
        out.attrs["top_voi_driver"] = tornado.iloc[0].driver
        out.attrs["top_voi_evidence"] = tornado.iloc[0].evidence_that_would_change_response
    return out
