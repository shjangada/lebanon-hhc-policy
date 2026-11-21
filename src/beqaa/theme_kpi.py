"""Theme KPI: share of Beqaa health money controlled by Lebanese actors.

Two series, deliberately NOT merged (different scope):
  observed   = Lebanon Humanitarian Fund: share of project budgets going to National NGOs, by year (CBPF project summary via HDX; real, nationwide, one pooled fund, 2026 partial year).
  projection = the proposed escrow window, 2026-2030, from the escrow model: LOCAL CONTROL = released money weighted by the rung that holds it (INGO 0, national NGO 1/3, union of
               municipalities 2/3, MoPH 1: escrow.LEVEL_LOCAL_WEIGHT, an assumption). Plain 'held by Lebanese organisations' (rung >= national NGO) is also returned: under the current
               capacity inputs national NGOs qualify from day one, so that share starts at 100% and only the weighted control moves. District capacity inputs are MOCK scenario inputs
               (no public series), so the projection is an ASSUMPTION-based path.
`local_control_share(year, scenario)` returns the value with its status (real / assumption / missing), scope, source and caveat. With no processed LHF file the observed value is
returned as status 'missing' (never an invented number). Scenarios: baseline, S1_escalation (from 2028), S2_funding_shock (pool x0.5), S5_capacity_stall (0 gain per year).
"""
from __future__ import annotations

import pandas as pd

from . import escrow, io, m2_need_score as m2
from .io import PROCESSED, ROOT

LHF_FILE = "lhf_national_ngo_share_by_year.csv"
SCENARIOS = {"baseline": {}, "S1_escalation": {"escalation_year": 2028}, "S2_funding_shock": {"pool_factor": 0.5}, "S5_capacity_stall": {"yoy_gain": 0.0}}
SCENARIO_LABELS = {"baseline": "Baseline", "S1_escalation": "S1 renewed escalation (2028)", "S2_funding_shock": "S2 funding -50%", "S5_capacity_stall": "S5 capacity stall"}
LHF_URL = "https://data.humdata.org/dataset/cbpf-allocations-and-contributions"


def observed_series(processed_dir=None) -> pd.DataFrame | None:
    """LHF national-NGO share by year from the processed file; None if the file is absent."""
    f = (processed_dir or PROCESSED) / LHF_FILE
    if not f.exists():
        return None
    d = pd.read_csv(f)
    return d[["year", "national_ngo_share", "total_usd"]]


def _escrow_path(scenario: str, scored: pd.DataFrame | None = None):
    if scored is None:
        scored = m2.compute(m2.raw_indicators())
    kw = dict(SCENARIOS[scenario])
    pf = kw.pop("pool_factor", 1.0)
    base_pool = float(escrow.run(scored)[0][["released_usd", "held_in_escrow_usd"]].sum().sum())
    sched, summ, warns = escrow.run(scored, pool=base_pool * pf, **kw)
    rows = []
    for y, g in sched.groupby("year"):
        amt = {lvl: float(g.loc[g.administered_by_floor == lvl, "need_floor_usd"].sum() + g.loc[g.administered_by_tranche == lvl, "tranche_released_usd"].sum()) for lvl in escrow.LEVELS}
        tot = sum(amt.values())
        rows.append({"year": int(y), **{f"usd_{lvl}": v for lvl, v in amt.items()}, "released_usd": tot, "held_usd": float(g.held_in_escrow_usd.sum()),
                     "share_weighted": sum(amt[l] * escrow.LEVEL_LOCAL_WEIGHT[l] for l in amt) / tot if tot > 0 else 0.0,
                     "share_lebanese_held": 1 - amt["INGO"] / tot if tot > 0 else 0.0})
    return pd.DataFrame(rows), sched


def local_control_share(year: int, scenario: str = "baseline", processed_dir=None, scored: pd.DataFrame | None = None) -> dict:
    obs = observed_series(processed_dir)
    last_obs = 2026
    if year <= last_obs:
        if obs is None or year not in set(obs.year):
            return {"year": year, "scenario": scenario, "value": None, "status": "missing", "kind": "observed", "source": "CBPF project summary (not processed)",
                    "scope": "Lebanon Humanitarian Fund, national", "caveat": "Run `make ingest`; no value is shown without data."}
        v = float(obs.loc[obs.year == year, "national_ngo_share"].iloc[0])
        return {"year": year, "scenario": scenario, "value": v, "status": "real", "kind": "observed", "source": LHF_URL,
                "scope": "Lebanon Humanitarian Fund project budgets to National NGOs (nationwide, one pooled fund; not all aid, not Beqaa-specific)",
                "caveat": "2026 is a partial year." if year == 2026 else ""}
    s, _ = _escrow_path(scenario, scored)
    r = s[s.year == year]
    if r.empty:
        return {"year": year, "scenario": scenario, "value": None, "status": "missing", "kind": "projection", "source": "escrow model", "scope": "escrow window", "caveat": "year outside the model horizon"}
    return {"year": year, "scenario": scenario, "value": float(r.share_weighted.iloc[0]), "lebanese_held_share": float(r.share_lebanese_held.iloc[0]), "status": "assumption",
            "kind": "projection", "source": "escrow model (src/beqaa/escrow.py)",
            "scope": "local control of the proposed escrow window: money weighted by the rung that holds it (INGO 0, national NGO 1/3, union of municipalities 2/3, MoPH 1)",
            "caveat": "district governance capacity is a mock scenario input (no public series); the path shows the mechanism, not a forecast"}


def kpi_table(years=range(2026, 2031), scenarios=None, scored: pd.DataFrame | None = None) -> pd.DataFrame:
    """year x scenario table of the projection plus who holds the money (USD per rung, held in escrow)."""
    scored = scored if scored is not None else m2.compute(m2.raw_indicators())
    rows = []
    for sc in scenarios or SCENARIOS:
        s, _ = _escrow_path(sc, scored)
        for _, r in s[s.year.isin(list(years))].iterrows():
            rows.append({"year": int(r["year"]), "scenario": sc, "local_control_share": float(r.share_weighted), "lebanese_held_share": float(r.share_lebanese_held),
                         "donor_held_usd": float(r["usd_INGO"]), "national_ngo_usd": float(r["usd_National NGO"]), "union_usd": float(r["usd_Union of Municipalities"]),
                         "moph_usd": float(r["usd_MoPH"]), "held_in_escrow_usd": float(r.held_usd), "status": "assumption", "source": "escrow model"})
    return pd.DataFrame(rows)
