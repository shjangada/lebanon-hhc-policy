"""Assumptions log: every parameter with value, range, source, status (page 9 / tab_assumptions.csv)."""
from __future__ import annotations

import pandas as pd

from . import allocation, escrow, m1_access, m2_need_score, m4_exposure, m5_options
from .io import ROOT
import yaml


def build() -> pd.DataFrame:
    rows = []

    def add(module, name, value, rng="", source="", status="assumption"):
        rows.append({"module": module, "parameter": name, "value": str(value), "range": rng, "source": source, "status": status})

    spec = m2_need_score.load_spec()
    for d, w in spec["domain_weights"].items():
        add("M2", f"weight[{d}]", w, "Dirichlet(1,…,1) draws", "team assumption; paper gives no weights")
    add("M2", "tier thresholds (high/moderate)", f"{spec['tiers']['high']}/{spec['tiers']['moderate']}", "sliders", "CLAUDE.md brief")
    add("M2", "top_k for p_top_tier", spec["top_k"], "", "team assumption")
    for d, inds in spec["domains"].items():
        for i in inds:
            add("M2", f"{d}.{i['name']}", f"safe={i['safe']}, crisis={i['crisis']}", f"level: {i['level']}", i["source"], i["status"])
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
    add("M1", "decay function", "Gaussian within d0", "stepped alternative", "Luo & Qi 2009 E2SFCA form")
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
            "Mansuri & Rao 2013 (CDD review; mixed evidence): citation from memory, verify" if k == "local_fit_multiplier" else "assumption")
    add("allocation", "community priority weights", "Dirichlet(0.7) per cadaster", "", "MOCK (stand-in for survey / participatory budgeting)", "mock")
    for k, v in escrow.DEFAULT_RULES.items():
        add("escrow", k, v, "editable", "assumption")
    add("escrow", "admin level bands (capacity index)", escrow.BANDS, "INGO / national NGO / Union of Municipalities / MoPH (default ceiling: Union of Municipalities)", "assumption")
    add("escrow", "max administrator level", escrow.DEFAULT_MAX_LEVEL, "MoPH only as co-governor", "docs/FEASIBILITY.md (MoPH cannot be assumed to administer by 2030)")
    add("escrow", "max year-on-year capacity gain (projections)", escrow.MAX_YOY_CAPACITY_GAIN, "", "docs/FEASIBILITY.md")
    add("escrow", "local-control weights", escrow.LEVEL_LOCAL_WEIGHT, "", "assumption")
    return pd.DataFrame(rows)
