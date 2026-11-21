"""Assumptions log: every parameter with value, range, source, status (page 9 / tab_assumptions.csv)."""
from __future__ import annotations

import pandas as pd

from . import allocation, escrow, m1_access, m2_need_score, m4_exposure, m5_options, research_gaps, state_capacity
from .io import ROOT
import yaml


def build() -> pd.DataFrame:
    rows = []

    def add(module, name, value, rng="", source="", status="assumption"):
        rows.append({"module": module, "parameter": name, "value": str(value), "range": rng, "source": source, "status": status})

    spec = m2_need_score.load_spec()
    for d, w in spec["domain_weights"].items():
        add("M2", f"weight[{d}]", w, "Dirichlet(1,…,1) draws", "team assumption; paper gives no weights")
    add("M2", "default aggregation / normalisation", "weighted arithmetic mean of domain means; safe/crisis goalposts", "geometric, max, percentile tested", "docs/METHODS_DECISIONS.md D2-D3")
    add("M2", "tier thresholds (high/moderate)", f"{spec['tiers']['high']}/{spec['tiers']['moderate']}", "sliders", "CLAUDE.md brief")
    add("M2", "top_k for p_top_tier", spec["top_k"], "", "team assumption")
    for d, inds in spec["domains"].items():
        for i in inds:
            add("M2", f"{d}.{i['name']}", f"safe={i['safe']}, crisis={i['crisis']}", f"level: {i['level']}; anchor: {i.get('anchor', 'assumption')}", i["source"], i["status"])
    ex = m4_exposure.load_params()
    for k, v in ex.items():
        if isinstance(v, dict) and "value" in v:
            add("M4", k, v["value"], "", v.get("source", "EPA IRIS (confirm)"), v.get("status", "verify"))
        elif isinstance(v, dict) and "status" in v:
            add("M4", k, f"{v.get('low')}–{v.get('high')}", "key uncertainty", "assumption", v["status"])
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, dict):
                    add("M4", f"{k}.{kk}", vv.get("value"), "", "EPA IRIS (confirm)", vv.get("status", "verify"))
                else:
                    add("M4", f"{k}.{kk}", vv, "", "EPA defaults" if "food" not in k else "assumption", "verify" if "food" not in k else "assumption")
    add("M4", "crop transfer factor", "max over crops for metal", "x0.25–x4 in tornado", "crop_transfer.csv (Abi Saab et al. 2022 when real)", "mock")
    add("M1", "decay function", "Gaussian within d0 (default)", "stepped zones alternative", "E2SFCA: Luo & Qi 2009 used stepped zones (S36); continuous Gaussian decay is a later refinement (to verify citation). D9")
    add("M1", "d0 catchment (min)", 30, "15 / 30 / 60", "team assumption")
    add("M1", "women share applied to every group in a cadaster", "cadaster-level share", "", "assumption: age/sex by displacement status not published")
    for g, w in m1_access.DEFAULT_DEMAND_WEIGHTS.items():
        add("M1", f"demand weight[{g}]", w, "0.5–3 in app", "assumption (displaced / unregistered women may carry more unmet need)")
    add("M5", "cascade independence", "product of conditional step probabilities", "", "assumption")
    add("M5", "intervention lifts / costs / reach", "interventions.csv ranges", "uniform within range", "MOCK until UNFPA/WHO/K2P quotes", "mock")
    for g, w in m5_options.DEFAULT_REACH_W.items():
        add("M5", f"reach weight[{g}]", w, "0.2–1.0", "assumption: unregistered workers harder to reach")
    for k, v in allocation.DEFAULTS.items():
        add("allocation", k, v, "local_fit 1.0–1.3" if k == "local_fit_multiplier" else "",
            "Mansuri & Rao 2013, Localizing Development: Does Participation Work? (World Bank; sources.csv S35); 3ie WP30 2018 (S26): mixed evidence" if k == "local_fit_multiplier" else "assumption")
    add("allocation", "community priority weights", "Dirichlet(0.7) per cadaster", "", "MOCK (stand-in for survey / participatory budgeting)", "mock")
    for k, v in escrow.DEFAULT_RULES.items():
        add("escrow", k, v, "editable", "national anchor SC01 (WGI GE 2025 = 29.9/100)" if k == "admin_capacity_min" else "assumption")
    for k, v in escrow.NEED_GATE.items():
        add("escrow", f"need_gate.{k}", v, "editable in app",
            "M2 Moderate tier threshold" if k == "need_score_min" else
            ("blend of M4 environmental exposure into priority (M2 already has a 0.15 environment domain)" if k == "env_priority_weight" else "assumption"))
    add("escrow", "pool expected realisation", escrow.POOL["expected_realisation"], "", "LRP 2026: 39% funded (docs/FEASIBILITY.md §1)", "verified")
    for r in escrow.LADDER.itertuples():
        add("escrow", f"ladder band[{r.level}]", r.min_capacity, "", "SC01 notes: WGI GE 2023 low 28.0 / 2000 high 51.4" if r.level in ("National NGO", "MoPH")
            else "assumption", "assumption")
    nb = state_capacity.national_baseline()
    add("state capacity", "national admin-capacity anchor (WGI GE / 100)", nb["admin_anchor"], f"year {nb['admin_anchor_year']}", "state_capacity_sources.csv SC01", nb["admin_anchor_status"])
    add("state capacity", "government share of health spending", nb["fiscal_anchor"], f"year {nb['fiscal_anchor_year']}", "state_capacity_sources.csv SC02", nb["fiscal_anchor_status"])
    add("state capacity", "district admin_capacity_index", "mock relative spread x national anchor", "replace with SC07 UN-Habitat 2026", "mock", "mock")
    add("state capacity", "default projected capacity gain per year", escrow.DEFAULT_YOY_GAIN, f"0 to {escrow.MAX_YOY_CAPACITY_GAIN}", "assumption (cap from docs/FEASIBILITY.md §5)")
    for k, v in research_gaps.GAP_WEIGHTS.items():
        add("research gaps", f"gap weight[{k}]", v, "", "assumption")
    add("research gaps", "candidate threshold (evidence_gap_score)", research_gaps.GAP_MIN, "", "assumption")
    add("M4", "Cr(VI) share used for tiering", "1.0 (precautionary) unless set in app", "0-1", "assumption: until speciation results exist")
    add("escrow", "max administrator level", escrow.DEFAULT_MAX_LEVEL, "MoPH only as co-governor", "docs/FEASIBILITY.md (MoPH cannot be assumed to administer by 2030)")
    add("escrow", "max year-on-year capacity gain (projections)", escrow.MAX_YOY_CAPACITY_GAIN, "", "docs/FEASIBILITY.md")
    add("escrow", "local-control weights", escrow.LEVEL_LOCAL_WEIGHT, "", "assumption")
    return pd.DataFrame(rows)
