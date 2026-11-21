"""Adaptive funding switch (escrow). Money follows measured need; administrative control shifts
INGO -> national NGO -> municipality -> MoPH as measured capacity improves.

Per town and year: need-floor release (guaranteed, by Need Score share) + capacity tranche (released only if the
threshold rules pass). Locked tranche is either HELD in escrow (restricted) or released through a more-foreign
intermediary one level down (unrestricted). All thresholds and level bands are ASSUMPTIONS, editable in the app.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .io import load_dataset

LEVELS = ["INGO", "National NGO", "Municipality", "MoPH"]
LEVEL_LOCAL_WEIGHT = {"INGO": 0.0, "National NGO": 0.33, "Municipality": 0.67, "MoPH": 1.0}   # state-capacity weight (assumption)
BANDS = [0.35, 0.50, 0.70]            # admin_capacity_index cut-points between levels (assumption)
DEFAULT_RULES = {"referral_min": 0.40, "posts_filled_min": 0.60, "transparent_required": True, "admin_capacity_min": 0.40}


def level_for(index: float) -> str:
    return LEVELS[int(np.searchsorted(BANDS, index, side="right"))]


def run(scored: pd.DataFrame, pool: float = 1_000_000, n_towns: int = 8, need_floor_pct: float = 0.5, start: int = 2026, end: int = 2030,
        rules: dict | None = None, unrestricted: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    r = {**DEFAULT_RULES, **(rules or {})}
    gov, mock = load_dataset("governance_capacity")
    stf, _ = load_dataset("staffing_referrals")
    towns = scored.sort_values("need_score", ascending=False).head(n_towns).copy()
    share = towns.need_score / towns.need_score.sum()
    years = list(range(start, end + 1))
    per_year = pool / len(years)
    rows = []
    for t, sh in zip(towns.itertuples(), share):
        gd = gov[gov.district == t.district].set_index("year")
        posts_filled = 1 - t.posts_unfilled_share
        ref = t.referral_completion
        for y in years:
            g = gd.loc[y]
            idx = float(g.admin_capacity_index)
            floor = per_year * need_floor_pct * sh
            tranche = per_year * (1 - need_floor_pct) * sh
            fails = []
            if ref < r["referral_min"]:
                fails.append("referral completion")
            if posts_filled < r["posts_filled_min"]:
                fails.append("posts filled")
            if r["transparent_required"] and not bool(g.transparent_reporting):
                fails.append("transparent reporting")
            if idx < r["admin_capacity_min"]:
                fails.append("admin capacity")
            passed = not fails
            level = level_for(idx)
            if passed:
                released_tranche, held, level_t = tranche, 0.0, level
            elif unrestricted:
                released_tranche, held = tranche, 0.0
                level_t = LEVELS[max(0, LEVELS.index(level) - 1)]          # routed via a more-foreign intermediary
            else:
                released_tranche, held, level_t = 0.0, tranche, None
            released = floor + released_tranche
            local = (floor * LEVEL_LOCAL_WEIGHT[level] + (released_tranche * LEVEL_LOCAL_WEIGHT[level_t] if level_t else 0)) / released if released else 0
            rows.append({"cadaster_id": t.cadaster_id, "cadaster_name": t.cadaster_name, "district": t.district, "year": y,
                         "projected_capacity": bool(g.projected), "admin_capacity_index": idx, "need_share": sh,
                         "need_floor_usd": floor, "tranche_due_usd": tranche, "tranche_released_usd": released_tranche,
                         "held_in_escrow_usd": held, "released_usd": released, "administered_by_floor": level,
                         "administered_by_tranche": level_t or "held", "thresholds_failed": "; ".join(fails),
                         "share_managed_locally": local, "is_mock": bool(mock)})
    d = pd.DataFrame(rows)
    # warnings
    w = []
    lock = d.groupby("cadaster_name").apply(lambda x: (x.held_in_escrow_usd > 0).sum(), include_groups=False)
    for name, yrs in lock[lock > 0].items():
        w.append(f"Lock-out: {name} (a top-{n_towns} need town) has its capacity tranche held in {yrs} of {len(years)} years. "
                 f"Only the need floor ({need_floor_pct:.0%}) reaches the worst-off: check the exclusion.")
    tot_held = d.held_in_escrow_usd.sum()
    if tot_held > 0.25 * pool * (1 - need_floor_pct):
        w.append(f"${tot_held:,.0f} ({tot_held / pool:.0%} of the pool) is held back by thresholds; consider a lower tranche share or unrestricted routing.")
    if need_floor_pct < 0.3:
        w.append("Need floor below 30%: the highest-need, lowest-capacity towns depend mainly on capacity tranches they may never unlock.")
    # gaming risk: self-reported indicators bunching just above thresholds
    near = towns[(towns.referral_completion - r["referral_min"]).between(0, 0.05)]
    for t in near.itertuples():
        w.append(f"Gaming risk: {t.cadaster_name} referral completion ({t.referral_completion:.0%}) sits within 5 points above the threshold. "
                 "Self-reported: verify independently (sampled audits).")
    w.append("Gaming risk (structural): referral completion, posts filled and transparent reporting are self-reported by the implementer. "
             "Posts can be 'filled' on paper. Use third-party spot checks before releasing a tranche.")
    if unrestricted:
        w.append("Unrestricted routing: money reaches high-need towns but via more-foreign intermediaries and with weaker earmarking: higher capture risk.")
    else:
        w.append("Restricted: money is held in escrow when thresholds fail, which protects against capture but delays care in the weakest towns.")
    summary = d.groupby("year").agg(released_usd=("released_usd", "sum"), held_usd=("held_in_escrow_usd", "sum")).reset_index()
    summary["share_managed_locally"] = d.groupby("year").apply(lambda x: np.average(x.share_managed_locally, weights=np.maximum(x.released_usd, 1e-9)),
                                                               include_groups=False).values
    return d, summary, w
