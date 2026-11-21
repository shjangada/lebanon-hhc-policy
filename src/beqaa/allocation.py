"""Community / participatory allocation simulator (the team's theme).

Regimes over the top-k Need Score cadasters for a fixed budget:
 (1) top_down: budget share ~ Need Score; central planner buys the most cost-effective intervention everywhere.
 (2) per_capita: budget share ~ population; same central-planner intervention.
 (3) community: budget share ~ Need Score (same as top-down, to isolate local choice); each cadaster's community
     priority weights choose the intervention; effectiveness x `local_fit_multiplier`; funds lost to capture.
The effect of local decision-making is an ASSUMPTION with a literature range, NOT an estimate: community-driven
development reviews find mixed effects on service delivery and elite-capture risks (e.g. Mansuri & Rao 2013,
'Localizing Development', World Bank: citation from memory, status: verify). Community priority weights are MOCK.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import equity, m5_options
from .io import load_dataset

REGIMES = ["top_down", "per_capita", "community"]
DEFAULTS = {"local_fit_multiplier": 1.10,           # assumption; plausible range 1.0-1.3 (mixed evidence)
            "base_capture": 0.20,                   # share of funds lost to capture without safeguards (assumption)
            "women_seat_share": 0.30, "worker_seat_share": 0.10,       # decision seats
            "share_reaching_unregistered": 0.50}    # relative reach of unregistered workers vs their pop share


def mock_priorities(cadaster_ids, intervention_ids, seed: int = 7) -> pd.DataFrame:
    """MOCK community priority weights (rows sum to 1) standing in for survey / participatory-budgeting input."""
    rng = np.random.default_rng(seed)
    W = rng.dirichlet(np.ones(len(intervention_ids)) * 0.7, len(cadaster_ids))
    df = pd.DataFrame(W, columns=list(intervention_ids))
    df.insert(0, "cadaster_id", list(cadaster_ids))
    df["is_mock"] = True
    return df


def capture_rate(p: dict) -> float:
    safeguard = min(1.0, (p["women_seat_share"] + p["worker_seat_share"]) / 0.6)    # 60% combined seats = full safeguard (assumption)
    return p["base_capture"] * (1 - safeguard)


def simulate(scored: pd.DataFrame, budget: float, top_k: int = 8, params: dict | None = None, candidate: list[str] | None = None,
             seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (summary per regime, per-cadaster detail)."""
    p = {**DEFAULTS, **(params or {})}
    iv, mock = load_dataset("interventions")
    pop, _ = load_dataset("population")
    cands = candidate or [i for i in iv.intervention_id if iv.set_index("intervention_id").loc[i, "steps"] == iv.set_index("intervention_id").loc[i, "steps"]
                          and str(iv.set_index("intervention_id").loc[i, "steps"]) not in ("", "nan")]
    ivx = iv.set_index("intervention_id").loc[cands]
    ue = m5_options.unit_effects(np.random.default_rng(seed))
    ue = ue[ue.intervention_id.isin(cands)]
    cost_mid = ((ivx.cost_low_usd + ivx.cost_high_usd) / 2)
    ppl_mid = ((ivx.people_low + ivx.people_high) / 2)
    cost_per_woman = cost_mid / ppl_mid                              # $ per woman reached
    reach_w = {**m5_options.DEFAULT_REACH_W}
    reach_w["unregistered_workers_est"] = 0.5 * 2 * p["share_reaching_unregistered"]    # 0.5 default => 0.5
    gain_g = ue.pivot(index="intervention_id", columns="group", values="gain_per_woman").loc[cands]
    top = scored.sort_values("need_score", ascending=False).head(top_k).merge(
        pop[["cadaster_id", "population_total"]].rename(columns={"population_total": "pop_total"}), on="cadaster_id")
    gp = equity.group_pops(pop).set_index("cadaster_id")
    best = (gain_g.mean(axis=1) / cost_per_woman).idxmax()           # planner's most cost-effective intervention
    pri = mock_priorities(top.cadaster_id, cands, seed + 1).set_index("cadaster_id")
    cap = capture_rate(p)
    detail = []
    for regime in REGIMES:
        share = (top.need_score / top.need_score.sum()) if regime != "per_capita" else (top.pop_total / top.pop_total.sum())
        for r, sh in zip(top.itertuples(), share):
            b = budget * sh
            if regime == "community":
                mix = pri.loc[r.cadaster_id]
                eff_mult, leak = p["local_fit_multiplier"], cap
            else:
                mix = pd.Series({c: 1.0 if c == best else 0.0 for c in cands})
                eff_mult, leak = 1.0, 0.0
            women = {g: 0.0 for g in m5_options.CASCADE_GROUPS}
            pathways = 0.0
            for c in cands:
                spend = b * mix[c] * (1 - leak)
                reached = spend / cost_per_woman[c]
                wts = pd.Series({g: gp.loc[r.cadaster_id, g] * reach_w[g] for g in m5_options.CASCADE_GROUPS})
                wts = wts / wts.sum() if wts.sum() > 0 else wts
                for g in m5_options.CASCADE_GROUPS:
                    women[g] += reached * wts[g]
                    pathways += reached * wts[g] * gain_g.loc[c, g] * eff_mult
            reached_total = sum(women.values())
            detail.append({"regime": regime, "cadaster_id": r.cadaster_id, "cadaster_name": r.cadaster_name, "district": r.district,
                           "budget_usd": b, "women_reached": reached_total, "pregnant_est": r.pregnant_est,
                           "coverage": min(1.0, reached_total / max(r.pregnant_est, 1)), "extra_pathways": pathways,
                           "top_intervention": best if regime != "community" else mix.idxmax(),
                           **{f"reached_{g}": women[g] for g in women}})
    d = pd.DataFrame(detail)
    base = m5_options.baseline().set_index("group").completion
    rows = []
    for regime, g in d.groupby("regime"):
        tot_w = g.women_reached.sum()
        by_group = {x: g[f"reached_{x}"].sum() for x in m5_options.CASCADE_GROUPS}
        gpop = gp.loc[g.cadaster_id, m5_options.CASCADE_GROUPS].sum()
        group_cov = pd.Series({x: min(1.0, by_group[x] / max(gpop[x] * 0.04, 1)) for x in by_group})    # ~4% pregnant at a time
        after = pd.Series({x: base[x] + group_cov[x] * (g.extra_pathways.sum() / max(tot_w, 1e-9)) for x in by_group})
        rows.append({"regime": regime, "budget_usd": g.budget_usd.sum(), "women_reached": tot_w,
                     "mean_coverage": g.coverage.mean(), "min_cadaster_coverage": g.coverage.min(),
                     "extra_pathways": g.extra_pathways.sum(),
                     "cost_per_pathway": g.budget_usd.sum() / max(g.extra_pathways.sum(), 1e-9),
                     "unregistered_share_of_reach": by_group["unregistered_workers_est"] / max(tot_w, 1e-9),
                     "equity_gap_after": float(after.max() - after.min()),
                     "capture_loss_rate": cap if regime == "community" else 0.0, "is_mock": bool(mock)})
    return pd.DataFrame(rows), d


def what_local_choice_changes(summary: pd.DataFrame) -> pd.DataFrame:
    s = summary.set_index("regime")
    rows = []
    for m in ["women_reached", "extra_pathways", "cost_per_pathway", "unregistered_share_of_reach", "equity_gap_after"]:
        rows.append({"metric": m, "top_down": s.loc["top_down", m], "community": s.loc["community", m],
                     "community_minus_top_down": s.loc["community", m] - s.loc["top_down", m]})
    return pd.DataFrame(rows)
