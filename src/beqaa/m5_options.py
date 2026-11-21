"""M5: Options & cost. Answers Q3 and the required options comparison.

Cascade (by group): any ANC -> ANC4 -> facility delivery -> postnatal, plus referral closed.
Pathway completion = product of step probabilities. ASSUMPTION: p_anc4 is treated as conditional on any ANC (ratio),
the other steps as conditional on the previous one, steps independent given the previous. Interventions raise specific
steps by an absolute `lift` for the women they reach (mock ranges). Monte Carlo over cost, reach and lift.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import equity
from .io import load_dataset

STEPS = ["any_anc", "anc4", "facility_delivery", "postnatal", "referral_complete"]
# Reach weights: how readily each group is actually reached by a given programme (ASSUMPTION, adjustable in the app).
DEFAULT_REACH_W = {"host_lebanese": 1.0, "displaced_lebanese": 1.0, "registered_displaced_syrians": 0.8, "unregistered_workers_est": 0.5}
CASCADE_GROUPS = list(DEFAULT_REACH_W)
BUDGET_TIERS = {"$1,000 (starter pilot)": 1_000, "$100,000": 100_000, "$1,000,000": 1_000_000}


def feasibility_flags(r) -> list[str]:
    """Feasibility filter F1-F8 (docs/FEASIBILITY.md). Returns the tests an intervention fails (qualitative team judgments)."""
    fl = []
    if r["needs_new_public_money"]:
        fl.append("F1 needs new public money")
    if not r["pausable"]:
        fl.append("F2 not pausable under escalation")
    if r["grid_power_dependent"]:
        fl.append("F3 needs grid power")
    if r["needs_new_doctors"]:
        fl.append("F4 needs new doctors")
    if not str(r["existing_institution"]).strip() or str(r["existing_institution"]) == "nan":
        fl.append("F5 no existing institution")
    if r["requires_id"]:
        fl.append("F6 requires ID: needs an anonymous / community-ID workaround")
    if not str(r["funding_window"]).strip() or str(r["funding_window"]) == "nan":
        fl.append("F7 no named funding window")
    if not str(r["indicator_source"]).strip() or str(r["indicator_source"]) == "nan":
        fl.append("F8 no measurable indicator")
    return fl


def feasibility_table() -> pd.DataFrame:
    iv, mock = load_dataset("interventions")
    rows = []
    for _, r in iv.iterrows():
        fl = feasibility_flags(r)
        rows.append({"intervention_id": r.intervention_id, "label": r.label, "feasible": not fl, "n_flags": len(fl), "flags": "; ".join(fl),
                     "existing_institution": r.existing_institution, "funding_window": r.funding_window, "indicator_source": r.indicator_source,
                     "is_mock": bool(mock)})
    return pd.DataFrame(rows)


def step_probs(row) -> dict:
    return {"any_anc": row.p_any_anc, "anc4": min(1.0, row.p_anc4 / row.p_any_anc), "facility_delivery": row.p_facility_delivery,
            "postnatal": row.p_postnatal, "referral_complete": row.p_referral_complete}


def completion(steps: dict) -> float:
    return float(np.prod([steps[s] for s in STEPS]))


def baseline() -> pd.DataFrame:
    c, mock = load_dataset("cascade_baseline")
    rows = []
    for r in c.itertuples():
        st = step_probs(r)
        rows.append({"group": r.group, **{f"step_{k}": v for k, v in st.items()}, "completion": completion(st), "is_mock": bool(mock)})
    return pd.DataFrame(rows)


def unit_effects(rng: np.random.Generator | None = None, n: int = 2000, reach_w: dict | None = None) -> pd.DataFrame:
    """Per intervention x group: mean extra completed pathways per woman reached, and cost per unit (MC mean, 5-95%)."""
    rng = rng or np.random.default_rng(42)
    iv, _ = load_dataset("interventions")
    base = baseline().set_index("group")
    out = []
    for r in iv.itertuples():
        steps = [s for s in str(r.steps).split(";") if s and s != "nan"]
        lift = rng.uniform(r.lift_low, r.lift_high, n)
        for g in CASCADE_GROUPS:
            st = {s: base.loc[g, f"step_{s}"] for s in STEPS}
            b = completion(st)
            if steps:
                gains = []
                new = dict(st)
                # vectorised lift on listed steps
                prod = np.ones(n)
                for s in STEPS:
                    prod *= np.minimum(1.0, st[s] + lift) if s in steps else st[s]
                gains = prod - b
            else:
                gains = np.zeros(n)
            out.append({"intervention_id": r.intervention_id, "group": g, "gain_per_woman": float(gains.mean()),
                        "gain_p05": float(np.percentile(gains, 5)), "gain_p95": float(np.percentile(gains, 95))})
    return pd.DataFrame(out)


def fundable_table(budget: float, n: int = 4000, seed: int = 42) -> pd.DataFrame:
    """For one budget: which interventions can be funded alone, how many units, probability >= 1 unit."""
    rng = np.random.default_rng(seed)
    iv, mock = load_dataset("interventions")
    rows = []
    for r in iv.itertuples():
        cost = rng.uniform(r.cost_low_usd, r.cost_high_usd, n)
        units = budget / cost if r.divisible else np.floor(budget / cost)
        rows.append({"intervention_id": r.intervention_id, "label": r.label, "acts_on": r.acts_on,
                     "cost_per_unit_range": f"${r.cost_low_usd:,.0f}–${r.cost_high_usd:,.0f}",
                     "p_fundable": float((units >= (0.999 if not r.divisible else 0.01)).mean()),
                     "units_median": float(np.median(units)), "is_mock": bool(mock)})
    return pd.DataFrame(rows)


def evaluate(selected: list[str], budget: float, shares: dict | None = None, reach_w: dict | None = None,
             n: int = 3000, seed: int = 42, target_women: float | None = None) -> pd.DataFrame:
    """Monte Carlo per selected intervention: units, women reached, extra completed pathways, cost per pathway, equity gap change.

    Budget split equally unless `shares` given. Women reached are distributed over groups proportional to
    population-weighted reach weights (unregistered workers are harder to reach => lower weight)."""
    rng = np.random.default_rng(seed)
    reach_w = reach_w or DEFAULT_REACH_W
    iv, mock = load_dataset("interventions")
    iv = iv.set_index("intervention_id")
    base = baseline().set_index("group")
    pop, _ = load_dataset("population")
    gp = equity.group_pops(pop)[CASCADE_GROUPS].sum()
    wts = pd.Series({g: gp[g] * reach_w[g] for g in CASCADE_GROUPS})
    wts = wts / wts.sum()
    shares = shares or {s: 1 / len(selected) for s in selected}
    rows = []
    for s in selected:
        r = iv.loc[s]
        b = budget * shares[s]
        cost = rng.uniform(r.cost_low_usd, r.cost_high_usd, n)
        units = b / cost if r.divisible else np.floor(b / cost)
        people = units * rng.uniform(r.people_low, r.people_high, n)
        if target_women:
            people = np.minimum(people, target_women)
        steps = [x for x in str(r.steps).split(";") if x and x != "nan"]
        lift = rng.uniform(r.lift_low, r.lift_high, n)
        gain = np.zeros(n)
        after_g = {}
        for g in CASCADE_GROUPS:
            st = {k: base.loc[g, f"step_{k}"] for k in STEPS}
            prod = np.ones(n)
            for k in STEPS:
                prod *= np.minimum(1.0, st[k] + lift) if k in steps else st[k]
            gain += people * wts[g] * (prod - completion(st))
            # after-intervention completion (population-averaged over reach share of that group)
            reached_share = np.minimum(1.0, people * wts[g] / max(gp[g] * 0.04, 1))   # ~4% of group pregnant at a time (approx)
            after_g[g] = completion(st) + reached_share * (prod - completion(st))
        b0 = pd.Series({g: base.loc[g, "completion"] for g in CASCADE_GROUPS})
        after_med = pd.DataFrame(after_g).median()
        gap_before = b0.max() - b0.min()
        gap_after = after_med.max() - after_med.min()
        spent = np.where(units > 0, b, 0)
        row = {"intervention_id": s, "label": r.label, "acts_on": r.acts_on, "budget_usd": b,
               "units_median": float(np.median(units)), "p_fundable": float((units > 0.01).mean()),
               "women_reached_median": float(np.median(people)), "women_reached_p05": float(np.percentile(people, 5)),
               "women_reached_p95": float(np.percentile(people, 95)),
               "extra_pathways_median": float(np.median(gain)), "extra_pathways_p05": float(np.percentile(gain, 5)),
               "extra_pathways_p95": float(np.percentile(gain, 95)),
               "cost_per_pathway_median": float(np.median(np.where(gain > 0, spent / np.maximum(gain, 1e-9), np.nan)[gain > 0])) if (gain > 0).any() else np.nan,
               "equity_gap_before": float(gap_before), "equity_gap_after": float(gap_after),
               "equity_gap_change": float(gap_after - gap_before),
               "collateral_exclusion": r.risk_exclusion, "collateral_capture": r.risk_capture, "collateral_dependency": r.risk_dependency,
               "collateral_displacement": r.risk_displacement, "collateral_conflict": r.risk_conflict,
               "feasibility_flags": "; ".join(feasibility_flags(r)) or "passes F1-F8", "is_mock": bool(mock)}
        if not steps:
            row["note"] = "Environmental / protection measure: acts on exposure, not on the ANC cascade (no pathways counted)"
        rows.append(row)
    return pd.DataFrame(rows)


def where_it_goes(scored: pd.DataFrame, women: float, k: int | None = None) -> pd.DataFrame:
    """Allocate programme reach to the highest Need Score cadasters until their pregnant women are covered."""
    s = scored.sort_values("need_score", ascending=False)
    left, rows = float(women), []
    for r in s.itertuples():
        if left <= 0 or (k and len(rows) >= k):
            break
        take = min(left, r.pregnant_est * 12 / 12)          # pregnant_est treated as annual pregnancies (approximation)
        rows.append({"cadaster_id": r.cadaster_id, "cadaster_name": r.cadaster_name, "district": r.district,
                     "need_score": r.need_score, "women_allocated": take})
        left -= take
    return pd.DataFrame(rows)


def options_table(scored: pd.DataFrame, budgets: dict | None = None, seed: int = 42) -> pd.DataFrame:
    """Memo table: each reach/continuity intervention alone at each tier + the environmental starters."""
    budgets = budgets or BUDGET_TIERS
    iv, _ = load_dataset("interventions")
    rows = []
    for tier, b in budgets.items():
        ev = evaluate(list(iv.intervention_id), b, shares={i: 1 / len(iv) for i in iv.intervention_id}, seed=seed)
        # evaluate each alone with the FULL tier budget
        for i in iv.intervention_id:
            e = evaluate([i], b, seed=seed).iloc[0].to_dict()
            e["budget_tier"] = tier
            rows.append(e)
    return pd.DataFrame(rows)
