"""M1: Enhanced 2-step floating catchment area (E2SFCA) access. Answers Q1.

Step 1: R_j = cap_j / sum_k pop_k W(t_kj).  Step 2: A_i = sum_j R_j W(t_ij).
W = continuous Gaussian decay inside catchment d0, 0 outside (a later refinement of E2SFCA; Luo & Qi 2009 themselves used stepped
travel-time zones, available here as kind='stepped'). A_i is capacity per person. See docs/METHODS_DECISIONS.md D9.
Conservation: sum_i pop_i A_i = sum of capacity of facilities with non-zero demand in catchment.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import equity
from .io import load_dataset

DEMAND_COLS = ("population_total", "women_15_49", "pregnant_est", "weighted_women_15_49")
# Demand multipliers per group for `weighted_women_15_49` (ASSUMPTION: displaced / unregistered women carry more unmet ANC need).
DEFAULT_DEMAND_WEIGHTS = {"host_lebanese": 1.0, "displaced_lebanese": 1.0, "registered_displaced_syrians": 1.0, "unregistered_workers_est": 1.0}


def weighted_demand(pop: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Add `weighted_women_15_49`: women 15-49 in each group x group weight, summed.

    Women per group = group population x the cadaster's women 15-49 share (from WorldPop age/sex; the same share is
    applied to every group in a cadaster: ASSUMPTION, since age/sex by displacement status is not published)."""
    w = {**DEFAULT_DEMAND_WEIGHTS, **(weights or {})}
    gp = equity.group_pops(pop).set_index("cadaster_id")
    share = (pop.set_index("cadaster_id").women_15_49 / pop.set_index("cadaster_id").population_total)
    tot = gp[list(w)].sum(axis=1).replace(0, np.nan)
    scale = pop.set_index("cadaster_id").population_total / tot          # keep groups consistent with the cadaster total
    out = pop.copy()
    out["weighted_women_15_49"] = (sum(gp[g] * w[g] for g in w) * scale.fillna(1.0) * share).reindex(pop.cadaster_id).values
    return out


def decay(t: np.ndarray, d0: float, kind: str = "gaussian") -> np.ndarray:
    t = np.asarray(t, dtype=float)
    inside = t <= d0
    if kind == "stepped":
        w = np.where(t <= d0 / 3, 1.0, np.where(t <= 2 * d0 / 3, 0.68, np.where(inside, 0.22, 0.0)))
        return w
    g = (np.exp(-0.5 * (t / d0) ** 2) - math.exp(-0.5)) / (1 - math.exp(-0.5))
    return np.where(inside, g, 0.0)


def e2sfca(pop: pd.DataFrame, fac: pd.DataFrame, tt: pd.DataFrame, d0: float = 30, demand_col: str = "women_15_49",
           facilities: str = "all", scenario: str = "current_2026", kind: str = "gaussian", exclude: set | None = None) -> pd.DataFrame:
    """Return per-cadaster access A_i (capacity per person) for one scenario."""
    f = fac.copy()
    if scenario == "current_2026":
        f = f[f.status_2026 == "open"]
    elif scenario != "baseline_pre2026":
        raise ValueError(scenario)
    if exclude:
        f = f[~f.facility_id.isin(exclude)]
    if facilities == "offers_anc":
        f = f[f.offers_anc.astype(bool)]
    cad_ids = list(pop.cadaster_id)
    T = (tt[tt.facility_id.isin(f.facility_id)].pivot(index="cadaster_id", columns="facility_id", values="minutes")
         .reindex(index=cad_ids, columns=list(f.facility_id)))
    W = decay(T.values, d0, kind)
    demand = pop.set_index("cadaster_id").loc[cad_ids, demand_col].values.astype(float)
    cap = f.set_index("facility_id").loc[T.columns, "capacity_weekly"].values.astype(float)
    denom = (demand[:, None] * W).sum(axis=0)
    R = np.divide(cap, denom, out=np.zeros_like(cap), where=denom > 0)
    A = (W * R[None, :]).sum(axis=1)
    out = pd.DataFrame({"cadaster_id": cad_ids, "access": A, "scenario": scenario, "d0": d0, "demand_col": demand_col})
    out["nearest_open_minutes"] = np.where(T.shape[1] > 0, np.nanmin(T.values, axis=1), np.nan) if T.shape[1] else np.nan
    out["is_mock"] = bool(pop["is_mock"].all()) or bool(fac["is_mock"].all())
    return out


def access_by_cadaster(d0: float = 30, demand_col: str = "women_15_49", facilities: str = "all", kind: str = "gaussian",
                       demand_weights: dict | None = None) -> pd.DataFrame:
    pop, m1 = load_dataset("population")
    if demand_col == "weighted_women_15_49":
        pop = weighted_demand(pop, demand_weights)
    fac, m2 = load_dataset("facilities")
    tt, m3 = load_dataset("travel_time")
    cad, _ = load_dataset("cadasters")
    base = e2sfca(pop, fac, tt, d0, demand_col, facilities, "baseline_pre2026", kind)
    cur = e2sfca(pop, fac, tt, d0, demand_col, facilities, "current_2026", kind)
    df = cad[["cadaster_id", "cadaster_name", "district", "lat", "lon"]].merge(
        base[["cadaster_id", "access"]].rename(columns={"access": "access_baseline"})).merge(
        cur[["cadaster_id", "access", "nearest_open_minutes"]].rename(columns={"access": "access_current"}))
    df["access_lost"] = df.access_baseline - df.access_current
    df["access_lost_pct"] = np.where(df.access_baseline > 0, df.access_lost / df.access_baseline, 0.0)
    df["rank_current"] = df.access_current.rank(method="min")           # 1 = least access
    df["is_mock"] = m1 or m2 or m3
    return df


def catchment_sensitivity(demand_col: str = "women_15_49", sizes=(15, 30, 60), demand_weights: dict | None = None) -> pd.DataFrame:
    rows = []
    for d0 in sizes:
        a = access_by_cadaster(d0, demand_col, demand_weights=demand_weights)
        a["d0"] = d0
        rows.append(a[["cadaster_id", "cadaster_name", "district", "d0", "access_current", "rank_current", "is_mock"]])
    return pd.concat(rows, ignore_index=True)


def group_access(acc: pd.DataFrame, d0: float = 30) -> pd.DataFrame:
    """Access by group (where each group lives) + gap vs host Lebanese. Spatial only: legal/financial barriers enter in M5."""
    pop, _ = load_dataset("population")
    g = equity.by_group(acc, pop, ["access_baseline", "access_current"])
    g = g.pivot(index="group", columns="metric", values="value").reindex(equity.GROUPS)
    g["access_lost"] = g.access_baseline - g.access_current
    g["ratio_to_host"] = g.access_current / g.loc["host_lebanese", "access_current"]
    g["gap_vs_host"] = g.access_current - g.loc["host_lebanese", "access_current"]
    g["is_mock"] = bool(acc["is_mock"].all())
    return g.reset_index()


def _cad_minutes(cad: pd.DataFrame) -> np.ndarray:
    lat, lon = cad.lat.values, cad.lon.values
    p = math.pi / 180
    dlat = (lat[:, None] - lat[None, :]) * p / 2
    dlon = (lon[:, None] - lon[None, :]) * p / 2
    x = np.sin(dlat) ** 2 + np.cos(lat[:, None] * p) * np.cos(lat[None, :] * p) * np.sin(dlon) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(x)) * 1.3 / 40 * 60       # same 1.3 detour / 40 km/h as the mock travel times


def mobile_unit_sites(k: int = 3, d0: float = 30, min_district_share: float = 0.0) -> pd.DataFrame:
    """Maximal covering location: pick k cadasters to host mobile units, maximising women 15-49 covered within d0
    among cadasters with NO open ANC facility within d0 (the unserved). Optional equity constraint: each district's
    unserved women must be covered at least `min_district_share` (may be infeasible for small k)."""
    pop, _ = load_dataset("population")
    fac, _ = load_dataset("facilities")
    tt, _ = load_dataset("travel_time")
    cad, _ = load_dataset("cadasters")
    cad = cad.reset_index(drop=True)
    pop = pop.set_index("cadaster_id").loc[cad.cadaster_id]
    open_anc = fac[(fac.status_2026 == "open") & fac.offers_anc.astype(bool)].facility_id
    near = tt[tt.facility_id.isin(open_anc)].groupby("cadaster_id").minutes.min().reindex(cad.cadaster_id)
    unserved = (near > d0).fillna(True).values
    women = pop.women_15_49.values * unserved
    M = _cad_minutes(cad) <= d0
    n = len(cad)
    from scipy.optimize import LinearConstraint, Bounds, milp
    # variables: x_0..x_{n-1} (site chosen), y_0..y_{n-1} (cadaster covered)
    c = np.concatenate([np.zeros(n), -women])
    rows, lo, hi = [], [], []
    r = np.zeros(2 * n); r[:n] = 1; rows.append(r); lo.append(min(k, n)); hi.append(min(k, n))
    for i in range(n):                                    # y_i <= sum_{j covers i} x_j
        r = np.zeros(2 * n); r[n + i] = 1; r[:n] = -M[i].astype(float); rows.append(r); lo.append(-np.inf); hi.append(0)
    if min_district_share > 0:
        for d in cad.district.unique():
            idx = [i for i in range(n) if cad.district[i] == d and women[i] > 0]
            if idx:
                r = np.zeros(2 * n)
                for i in idx:
                    r[n + i] = women[i]
                rows.append(r); lo.append(min_district_share * sum(women[i] for i in idx)); hi.append(np.inf)
    res = milp(c, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=np.ones(2 * n), bounds=Bounds(0, 1))
    if res.x is None:
        raise ValueError("Mobile-unit siting infeasible (equity constraint too strict for k)")
    chosen = [j for j in range(n) if res.x[j] > 0.5]
    covered = [i for i in range(n) if res.x[n + i] > 0.5]
    out = cad.loc[chosen, ["cadaster_id", "cadaster_name", "district", "lat", "lon"]].copy()
    out["women_newly_covered"] = [int(sum(women[i] for i in covered if M[i, j])) for j in chosen]
    out["unserved_women_total"] = int(women.sum())
    out["d0"] = d0
    out["is_mock"] = True if pop["is_mock"].all() else False
    return out.reset_index(drop=True)


def facility_risk(conflict_threshold: int = 15) -> pd.DataFrame:
    """Open facilities with power source and conflict exposure of their cadaster. Fixed assets in exposed cadasters, or on grid power only,
    are the ones that must be pausable / backed up (docs/FEASIBILITY.md F2, F3). Hubs without a cadaster take the nearest cadaster's exposure."""
    fac, mock = load_dataset("facilities")
    cad, _ = load_dataset("cadasters")
    ce, _ = load_dataset("conflict_exposure")
    f = fac[fac.status_2026 == "open"].copy()
    cadx = cad.merge(ce[["cadaster_id", "conflict_incidents"]], on="cadaster_id")
    inc = []
    for r in f.itertuples():
        if isinstance(r.cadaster_id, str) and r.cadaster_id in set(cadx.cadaster_id):
            inc.append(float(cadx.set_index("cadaster_id").loc[r.cadaster_id, "conflict_incidents"]))
        else:
            d = ((cadx.lat - r.lat) ** 2 + (cadx.lon - r.lon) ** 2)
            inc.append(float(cadx.loc[d.idxmin(), "conflict_incidents"]))
    f["conflict_incidents"] = inc
    f["conflict_exposed"] = f.conflict_incidents >= conflict_threshold
    f["grid_only"] = f.power_source == "grid_only"
    f["needs_backup_or_pause_plan"] = f.conflict_exposed | f.grid_only
    f["is_mock"] = bool(mock)
    return f[["facility_id", "name", "type", "power_source", "conflict_incidents", "conflict_exposed", "grid_only", "needs_backup_or_pause_plan", "offers_anc", "is_mock"]]


def access_if_exposed_pause(d0: float = 30, demand_col: str = "women_15_49", conflict_threshold: int = 15) -> pd.DataFrame:
    """Resilience scenario: facilities in conflict-exposed cadasters pause. Compare access with current_2026."""
    pop, _ = load_dataset("population")
    fac, _ = load_dataset("facilities")
    tt, _ = load_dataset("travel_time")
    cad, _ = load_dataset("cadasters")
    risk = facility_risk(conflict_threshold)
    paused = set(risk[risk.conflict_exposed].facility_id)
    cur = e2sfca(pop, fac, tt, d0, demand_col, "all", "current_2026")
    pau = e2sfca(pop, fac, tt, d0, demand_col, "all", "current_2026", exclude=paused)
    out = cad[["cadaster_id", "cadaster_name", "district"]].merge(cur[["cadaster_id", "access"]].rename(columns={"access": "access_current"})).merge(
        pau[["cadaster_id", "access"]].rename(columns={"access": "access_if_paused"}))
    out["access_lost_to_pause"] = out.access_current - out.access_if_paused
    out["pct_lost"] = np.where(out.access_current > 0, out.access_lost_to_pause / out.access_current, 0.0)
    out["n_paused_facilities"] = len(paused)
    out["is_mock"] = True if pop["is_mock"].all() else False
    return out
