"""P5 escrow pool flow (the adaptive funding switch).

  international funds -> ring-fenced pooled window (inside LHF/LFF, not a new vehicle)
    -> NEED GATE   : towns admitted by priority score (M2 need + M4 environmental exposure, weight editable) and need_score >= floor
    -> NEED FLOOR  : guaranteed share released on need alone
    -> CAPACITY TRANCHE: released only if process thresholds pass (referral completion, posts filled, transparent reporting,
                         district admin capacity >= national anchor)
    -> ADMINISTRATOR LADDER (who holds the money): INGO -> national NGO -> Union of Municipalities (-> MoPH only if allowed)
    -> COMMUNITY COMMITTEE decides USE at every rung -> district / town allocation

All thresholds, ladder bands and roles live in data/params/escrow_params.yaml (assumptions, editable in the app).
District admin capacity is MOCK, anchored to the national WGI Government Effectiveness value (SC01) and capped at
<=0.05/yr gains (state_capacity.py, docs/FEASIBILITY.md §5). MoPH co-governs; it is not assumed to administer by 2030.
Locked tranche is either HELD in escrow (restricted) or released through a more-foreign intermediary one level down (unrestricted).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import state_capacity
from .io import load_dataset

_P = state_capacity.load_params()
LADDER = pd.DataFrame(_P["ladder"])
LEVELS = list(LADDER.level)
LEVEL_LOCAL_WEIGHT = dict(zip(LADDER.level, LADDER.local_weight))     # state-capacity weight (assumption)
BANDS = list(LADDER.min_capacity[1:])                                  # admin_capacity_index cut-points between levels
MAX_YOY_CAPACITY_GAIN = _P["national_anchor"]["max_yoy_gain"]         # docs/FEASIBILITY.md: >0.05/yr is not credible
DEFAULT_YOY_GAIN = _P["national_anchor"]["default_yoy_gain"]
DEFAULT_MAX_LEVEL = _P["max_level"]                                    # default 2030 administrator ceiling; MoPH only as co-governor
DEFAULT_RULES = dict(_P["capacity_thresholds"])
NEED_GATE = dict(_P["need_gate"])
POOL = dict(_P["pool"])


def level_for(index: float, bands: list[float] | None = None) -> str:
    return LEVELS[int(np.searchsorted(bands or BANDS, index, side="right"))]


def priority_score(scored: pd.DataFrame, env_weight: float | None = None) -> pd.Series:
    """Allocation priority = (1 - w) * M2 need score + w * M4 environmental exposure (D_environment, 0-1).
    w = 0 -> need score only. M2 already contains an environment domain; w is an explicit, visible top-up."""
    w = NEED_GATE["env_priority_weight"] if env_weight is None else env_weight
    env = scored["D_environment"].fillna(0) if "D_environment" in scored else 0.0
    return (1 - w) * scored.need_score + w * env


def select_towns(scored: pd.DataFrame, n_towns: int, need_min: float, env_weight: float | None) -> tuple[pd.DataFrame, list[str]]:
    s = scored.assign(priority_score=priority_score(scored, env_weight))
    w = []
    gated = s[s.need_score >= need_min]
    if gated.empty:
        w.append(f"Need gate: no town reaches need score {need_min:.2f}; falling back to the top {n_towns} by priority (check the gate).")
        gated = s
    elif len(gated) < n_towns:
        w.append(f"Need gate: only {len(gated)} towns reach need score {need_min:.2f}, fewer than the {n_towns} slots; the pool is shared among them.")
    return gated.sort_values("priority_score", ascending=False).head(n_towns).copy(), w


SCEN_REFERRAL = 0.5     # SCENARIO value (not data): referral completion is not published; break-even in breakeven.py
SCEN_POSTS = 0.8        # SCENARIO value (not data): share of budgeted posts filled


def run(scored: pd.DataFrame, pool: float | None = None, n_towns: int | None = None, need_floor_pct: float | None = None,
        start: int | None = None, end: int | None = None, rules: dict | None = None, unrestricted: bool = False,
        max_level: str = DEFAULT_MAX_LEVEL, escalation_year: int | None = None, escalation_drop: float = 0.15,
        recovery_per_year: float = 0.03, env_weight: float | None = None, need_min: float | None = None,
        yoy_gain: float | None = None, bands: list[float] | None = None,
        referral_completion: float = SCEN_REFERRAL, posts_filled: float = SCEN_POSTS) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    pool = POOL["default_usd"] if pool is None else pool
    n_towns = NEED_GATE["n_towns"] if n_towns is None else n_towns
    need_floor_pct = NEED_GATE["need_floor_pct"] if need_floor_pct is None else need_floor_pct
    need_min = NEED_GATE["need_score_min"] if need_min is None else need_min
    start, end = start or POOL["years"][0], end or POOL["years"][1]
    bands = bands or BANDS
    r = {**DEFAULT_RULES, **(rules or {})}
    gov = state_capacity.anchored_governance(yoy_gain=yoy_gain)
    mock = bool(gov.is_mock.any())
    towns, w = select_towns(scored, n_towns, need_min, env_weight)
    share = towns.priority_score / towns.priority_score.sum()
    years = list(range(start, end + 1))
    per_year = pool / len(years)
    roles = LADDER.set_index("level")
    rows = []
    for t, sh in zip(towns.itertuples(), share):
        gd = gov[gov.district == t.district].set_index("year")
        ref = referral_completion          # SCENARIO parameters (no public facility-level data): the same for every town; see breakeven.py
        for y in years:
            g = gd.loc[y]
            idx = float(g.admin_capacity_index)
            escalated = escalation_year is not None and y >= escalation_year
            if escalated:                                                     # renewed escalation: capacity drops, then recovers slowly
                idx = max(0.0, idx - max(0.0, escalation_drop - recovery_per_year * (y - escalation_year)))
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
            level = LEVELS[min(LEVELS.index(level_for(idx, bands)), LEVELS.index(max_level))]
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
                         "need_score": t.need_score, "env_exposure": getattr(t, "D_environment", np.nan), "priority_score": t.priority_score,
                         "projected_capacity": bool(g.projected), "admin_capacity_index": idx, "capacity_status": g.capacity_status,
                         "need_share": sh, "need_floor_usd": floor, "tranche_due_usd": tranche, "tranche_released_usd": released_tranche,
                         "held_in_escrow_usd": held, "released_usd": released, "administered_by_floor": level,
                         "administered_by_tranche": level_t or "held", "thresholds_failed": "; ".join(fails),
                         "holds_money": roles.loc[level, "holds_money"], "decides_use": roles.loc[level, "decides_use"],
                         "share_managed_locally": local,
                         "lebanese_managed_usd": (floor if level != "INGO" else 0.0) + (released_tranche if level_t not in (None, "INGO") else 0.0),
                         "escalation_scenario": escalated, "is_mock": mock})
    d = pd.DataFrame(rows)
    # warnings
    lock = d.groupby("cadaster_name").apply(lambda x: (x.held_in_escrow_usd > 0).sum(), include_groups=False)
    for name, yrs in lock[lock > 0].items():
        w.append(f"Lock-out: {name} (a top-{n_towns} need town) has its capacity tranche held in {yrs} of {len(years)} years. "
                 f"Only the need floor ({need_floor_pct:.0%}) reaches the worst-off: check the exclusion.")
    tot_held = d.held_in_escrow_usd.sum()
    if tot_held > 0.25 * pool * (1 - need_floor_pct):
        w.append(f"${tot_held:,.0f} ({tot_held / pool:.0%} of the pool) is held back by thresholds; consider a lower tranche share or unrestricted routing.")
    if need_floor_pct < 0.3:
        w.append("Need floor below 30%: the highest-need, lowest-capacity towns depend mainly on capacity tranches they may never unlock.")
    if 0 <= referral_completion - r["referral_min"] <= 0.05:
        w.append(f"Gaming risk: the assumed referral completion ({referral_completion:.0%}) sits within 5 points above the threshold. Self-reported: verify independently (sampled audits).")
    w.append("Gaming risk (structural): referral completion, posts filled and transparent reporting are self-reported by the implementer. "
             "Posts can be 'filled' on paper. Use third-party spot checks before releasing a tranche.")
    w.append(f"Capacity anchor: district admin capacity is MOCK, rescaled to the national WGI Government Effectiveness value "
             f"({gov.national_anchor.iloc[0]:.3f}, SC01, status to_verify_primary; 2025 value, predates the 2026 war, so likely an upper bound).")
    if escalation_year is not None:
        w.append(f"Renewed-escalation scenario from {escalation_year}: capacity falls by {escalation_drop:.2f} and recovers {recovery_per_year:.2f}/yr; "
                 "fixed activities should pause while CHW and phone follow-up continue.")
    if unrestricted:
        w.append("Unrestricted routing: money reaches high-need towns but via more-foreign intermediaries and with weaker earmarking: higher capture risk.")
    else:
        w.append("Restricted: money is held in escrow when thresholds fail, which protects against capture but delays care in the weakest towns.")
    summary = d.groupby("year").agg(released_usd=("released_usd", "sum"), held_usd=("held_in_escrow_usd", "sum")).reset_index()
    summary["share_lebanese_managed"] = (d.groupby("year").lebanese_managed_usd.sum() / d.groupby("year").released_usd.sum().clip(lower=1e-9)).values
    summary["share_managed_locally"] = d.groupby("year").apply(lambda x: np.average(x.share_managed_locally, weights=np.maximum(x.released_usd, 1e-9)),
                                                               include_groups=False).values
    return d, summary, w


POOL_NODE = "Pooled escrow window (LHF/LFF)"
SOURCE_NODE = "International funds"


def flow_links(sched: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    """Sankey links (source, target, value_usd): funds -> pool -> need floor / tranche passed / tranche held -> administrator ->
    community committee -> district. `year=None` sums all years."""
    d = sched if year is None else sched[sched.year == year]
    links = [(SOURCE_NODE, POOL_NODE, d.need_floor_usd.sum() + d.tranche_due_usd.sum())]
    links += [(POOL_NODE, "Need floor (guaranteed)", d.need_floor_usd.sum()),
              (POOL_NODE, "Capacity tranche: thresholds passed", d.loc[d.thresholds_failed == "", "tranche_released_usd"].sum()),
              (POOL_NODE, "Capacity tranche: rerouted (unrestricted)", d.loc[d.thresholds_failed != "", "tranche_released_usd"].sum()),
              (POOL_NODE, "Capacity tranche: held in escrow", d.held_in_escrow_usd.sum())]
    for lvl in LEVELS:
        links.append(("Need floor (guaranteed)", f"Administrator: {lvl}", d.loc[d.administered_by_floor == lvl, "need_floor_usd"].sum()))
        m = d.administered_by_tranche == lvl
        links.append(("Capacity tranche: thresholds passed", f"Administrator: {lvl}", d.loc[m & (d.thresholds_failed == ""), "tranche_released_usd"].sum()))
        links.append(("Capacity tranche: rerouted (unrestricted)", f"Administrator: {lvl}", d.loc[m & (d.thresholds_failed != ""), "tranche_released_usd"].sum()))
        links.append((f"Administrator: {lvl}", "Community committee decides use",
                      d.loc[d.administered_by_floor == lvl, "need_floor_usd"].sum() + d.loc[m, "tranche_released_usd"].sum()))
    for dist, g in d.groupby("district"):
        links.append(("Community committee decides use", f"District: {dist}", g.released_usd.sum()))
    out = pd.DataFrame(links, columns=["source", "target", "value_usd"])
    return out[out.value_usd > 0.005].reset_index(drop=True)


def role_table(sched: pd.DataFrame | None = None, bands: list[float] | None = None) -> pd.DataFrame:
    """Who controls money at each capacity level (from escrow_params.yaml), plus how many town-years sit at each level."""
    t = LADDER.copy()
    b = [0.0] + list(bands or BANDS)
    t["capacity_band"] = [f">= {lo:.3f}" + (f" and < {hi:.3f}" if hi is not None else "") for lo, hi in zip(b, b[1:] + [None])]
    if sched is not None:
        t["town_years_at_level"] = t.level.map(sched.administered_by_floor.value_counts()).fillna(0).astype(int)
        t["usd_administered"] = t.level.map(sched.groupby("administered_by_floor").need_floor_usd.sum()
                                            .add(sched.groupby("administered_by_tranche").tranche_released_usd.sum(), fill_value=0)).fillna(0.0)
    t["allowed_by_default"] = [LEVELS.index(l) <= LEVELS.index(DEFAULT_MAX_LEVEL) for l in t.level]
    return t[[c for c in ["level", "capacity_band", "holds_money", "decides_use", "co_governs", "verifies", "allowed_by_default",
                          "town_years_at_level", "usd_administered", "local_weight"] if c in t]]


def by_district(sched: pd.DataFrame) -> pd.DataFrame:
    return sched.groupby("district").agg(towns=("cadaster_id", "nunique"), released_usd=("released_usd", "sum"),
                                         held_usd=("held_in_escrow_usd", "sum"), lebanese_managed_usd=("lebanese_managed_usd", "sum"),
                                         mean_priority=("priority_score", "mean"), mean_env_exposure=("env_exposure", "mean")).reset_index()
