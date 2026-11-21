"""Robustness: does the recommendation survive if our assumptions are wrong? (docs/METHODS_DECISIONS.md D10)

2a  Monte Carlo over uncertain parameters (ranges in data/params/uncertainty.yaml): catchment size, Need Score weights and aggregation,
    Cr(VI) share. Output: P(cadaster in top-k), rank intervals.
2b  Six named stress scenarios (S1-S6) applied to M1 access, M2 targets, policy value and the escrow.
2c  Metrics: Kendall tau of the ranking vs baseline, the CORE set (top-k in >= 80% of draws and in every scenario),
    maximum regret of candidate allocation policies across scenarios, graceful degradation of the escrow, breakpoints.
All draws use a fixed seed. With zero variance (a single draw of default parameters) outputs equal the baseline.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import yaml
from scipy.stats import kendalltau

from . import allocation, equity, escrow, m1_access, m2_need_score as m2, m5_options
from .io import ROOT, load_dataset

UNC_PATH = ROOT / "data" / "params" / "uncertainty.yaml"
SCENARIO_IDS = ["S1_escalation", "S2_funding_shock", "S3_power_collapse", "S4_staff_loss", "S5_capacity_stall", "S6_worst_case_contamination"]


def load_uncertainty(path=None) -> dict:
    return yaml.safe_load(open(path or UNC_PATH))


# ---------------------------------------------------------------- scenario worlds for access / targeting
def _access_columns(raw: pd.DataFrame, fac: pd.DataFrame, tt: pd.DataFrame, d0: float, baseline_median: float) -> pd.DataFrame:
    """Recompute the access-dependent Need Score columns for modified facilities / travel times."""
    pop, _ = load_dataset("population")
    open_f = m1_access.effective_facilities(fac)
    cur = m1_access.e2sfca(pop, open_f.assign(status_2026="open", status_date="2026-01-01", hours_per_week=np.nan), tt, d0, "women_15_49", "all", "current_2026")
    out = raw.drop(columns=["access_current", "access_deficit", "phc_30", "anc_share_30min", "phc_per_50k"]).merge(
        cur[["cadaster_id", "access"]].rename(columns={"access": "access_current"}), on="cadaster_id")
    out["access_deficit"] = 1 - (out.access_current / baseline_median).clip(0, 1)
    t = tt[tt.facility_id.isin(open_f.facility_id) & (tt.minutes <= 30)].merge(open_f[["facility_id", "type", "offers_anc"]], on="facility_id")
    phc = t[t.type == "PHC"].groupby("cadaster_id").size().rename("phc_30")
    anc = t.groupby("cadaster_id").offers_anc.mean().rename("anc_share_30min")
    out = out.merge(phc, on="cadaster_id", how="left").merge(anc, on="cadaster_id", how="left")
    out["phc_30"] = out.phc_30.fillna(0)
    out["anc_share_30min"] = out.anc_share_30min.fillna(0)
    out["phc_per_50k"] = out.phc_30 / out.population_total * 50_000
    return out


def scenario_raw(scn: str | None, d0: float, cr6: float | None, unc: dict, severity: dict | None = None) -> pd.DataFrame:
    """Indicator table for one scenario world. `severity` picks values from the scenario ranges (default: the range midpoint)."""
    sv = severity or {}
    base = m2.raw_indicators(d0, "women_15_49", cr6_for_tier=cr6)
    if scn in (None, "baseline", "S2_funding_shock", "S5_capacity_stall", "S6_worst_case_contamination"):
        return base
    fac, _ = load_dataset("facilities")
    tt, _ = load_dataset("travel_time")
    fac, tt = fac.copy(), tt.copy()
    fac["capacity_weekly"] = fac["capacity_weekly"].astype(float)
    bmed = base.access_baseline.median()
    cfg = unc["scenarios"][scn]
    if scn == "S1_escalation":
        risk = m1_access.facility_risk(cfg["exposed_incidents_threshold"])
        dead = set(risk[risk.conflict_exposed].facility_id)
        fac.loc[fac.facility_id.isin(dead), "status_2026"] = "closed"
        cad, _ = load_dataset("cadasters")
        ce, _ = load_dataset("conflict_exposure")
        exposed = set(ce[ce.conflict_incidents >= cfg["exposed_incidents_threshold"]].cadaster_id)
        mult = sv.get("travel_multiplier", float(np.mean(cfg["travel_multiplier"])))
        tt.loc[tt.cadaster_id.isin(exposed), "minutes"] *= mult
    elif scn == "S3_power_collapse":
        hours = sv.get("grid_hours", float(np.mean(cfg["grid_hours_per_day"])))
        grid = fac.get("power_source", pd.Series("generator", index=fac.index)) == "grid_only"
        fac.loc[grid, "capacity_weekly"] = fac.loc[grid, "capacity_weekly"] * min(1.0, hours / cfg["clinic_hours_per_day"])
    elif scn == "S4_staff_loss":
        loss = sv.get("capacity_loss", float(np.mean(cfg["capacity_loss"])))
        fac["capacity_weekly"] = fac["capacity_weekly"] * (1 - loss)
    return _access_columns(base, fac, tt, d0, bmed)


# ---------------------------------------------------------------- 2a/2c rank robustness
def _variants(scn, unc, rng, cache):
    """(d0, cr6) variants available in scenario `scn`; raw tables are cached."""
    d0s = unc["parameters"]["catchment_d0_minutes"]["values"]
    cr6s = [1.0] if scn == "S6_worst_case_contamination" else unc["parameters"]["cr6_fraction"]["grid"]
    out = {}
    for d0 in d0s:
        for c in cr6s:
            key = (scn, d0, c)
            if key not in cache:
                cache[key] = scenario_raw(scn, d0, c, unc)
            out[(d0, c)] = cache[key]
    return out


def rank_robustness(n: int | None = None, seed: int | None = None, top_k: int | None = None, unc: dict | None = None,
                    zero_variance: bool = False) -> dict:
    """Monte Carlo over parameters inside each scenario. Returns per-cadaster P(top-k) by scenario, rank intervals, Kendall tau and the core set."""
    unc = unc or load_uncertainty()
    n = n or unc["n_draws"]
    k = top_k or unc["top_k"]
    rng = np.random.default_rng(seed if seed is not None else unc["seed"])
    spec = m2.load_spec()
    cache: dict = {}
    base_raw = scenario_raw(None, 30, 0.1, unc)    # central baseline: Cr(VI) = 10%. (The dashboard default None = precautionary all-Cr(VI), which is S6.)
    ref = m2.compute(base_raw, spec=spec)                                   # reference ranking: default parameters, no scenario
    ids = ref.cadaster_id.values
    names = ref.set_index("cadaster_id").cadaster_name
    domains = m2.DOMAINS
    scen_list = ["baseline"] + SCENARIO_IDS
    tops = {}
    ranks_all = {}
    taus = []
    for scn in scen_list:
        variants = _variants(None if scn == "baseline" else scn, unc, rng, cache)
        keys = list(variants)
        Ds = {kk: m2.domain_matrix(m2.compute(variants[kk], spec=spec), domains) for kk in keys}
        # default-parameter ranking in this scenario (for Kendall tau): d0=30, cr6 default grid point nearest 0.1 (S6: 1.0)
        dk = (30, 1.0 if scn == "S6_worst_case_contamination" else 0.1)      # default parameters inside this scenario
        dflt = m2.compute(variants[dk], spec=spec)
        a = dflt.set_index("cadaster_id").reindex(ids)
        tau = kendalltau(ref.need_score.values, a.need_score.values)[0]
        topset = set(dflt.nsmallest(k, "rank").cadaster_id)
        taus.append({"scenario": scn, "kendall_tau_vs_baseline": float(tau), "top_k_retained": len(topset & set(ref.nsmallest(k, "rank").cadaster_id)),
                     "top_k": k})
        if zero_variance:
            nd = 1
            choice = [keys.index(dk)]
            W = np.full((1, len(domains)), 1 / len(domains))
            agg = ["arithmetic"]
        else:
            nd = n
            choice = rng.integers(0, len(keys), nd)
            W = rng.dirichlet(np.ones(len(domains)), nd)
            agg = rng.choice(unc["parameters"]["aggregation"]["values"], nd)
        R = np.zeros((len(ids), nd))
        for j in range(nd):
            D = Ds[keys[choice[j]]]
            w = W[j]
            S = m2.aggregate_scores(D, w, agg[j])
            order = (-S).argsort()
            rk = np.empty(len(ids), dtype=int)
            rk[order] = np.arange(1, len(ids) + 1)
            R[:, j] = rk
        # compute() orders rows like raw (same cadaster order in every variant): align to ids
        ranks_all[scn] = R
        tops[scn] = (R <= k).mean(axis=1)
    p = pd.DataFrame({"cadaster_id": ids, "cadaster_name": names.reindex(ids).values}).assign(
        **{f"p_top_{s}": tops[s] for s in scen_list})
    pooled = np.concatenate([ranks_all[s] for s in scen_list], axis=1)
    p["p_top_overall"] = (pooled <= k).mean(axis=1)
    p["rank_p05"], p["rank_p50"], p["rank_p95"] = (np.percentile(pooled, q, axis=1).astype(int) for q in (5, 50, 95))
    thr = unc["core_threshold"]
    scen_cols = [f"p_top_{s}" for s in scen_list]
    p["min_p_top_across_scenarios"] = p[scen_cols].min(axis=1)
    p["core"] = (p.p_top_overall >= thr) & (p.min_p_top_across_scenarios >= thr)
    p["is_mock"] = bool(base_raw.is_mock.all())
    scen = pd.DataFrame(taus)
    warn = None
    core = p[p.core]
    if core.empty:
        warn = (f"No cadaster is top-{k} in >= {thr:.0%} of draws in every scenario: the priority list is not robust. "
                f"Relaxed view: strongest candidates by minimum P(top-k) = " + ", ".join(p.nlargest(3, "min_p_top_across_scenarios").cadaster_name))
        warnings.warn(warn)
    return {"per_cadaster": p.sort_values("p_top_overall", ascending=False).reset_index(drop=True), "scenarios": scen, "core": core.cadaster_name.tolist(),
            "warning": warn, "top_k": k, "threshold": thr, "n_draws": 1 if zero_variance else n}


# ---------------------------------------------------------------- policy regret
POLICIES = ["top_down", "per_capita", "community", "existing_allocation"]


class _Engine:
    """Vectorised policy value (extra completed pathways) so thousands of draws are cheap. Allocations are decided ex ante on baseline data and
    then evaluated in each scenario world: the planner does not know which scenario will happen."""

    def __init__(self, scored: pd.DataFrame, top_k: int, budget: float, unc: dict):
        self.unc, self.budget = unc, budget
        iv, _ = load_dataset("interventions")
        pop, _ = load_dataset("population")
        self.iv = iv[iv.steps.notna() & (iv.steps.astype(str) != "")].reset_index(drop=True)          # interventions that act on the care cascade
        self.names = list(self.iv.intervention_id)
        ue = m5_options.unit_effects(np.random.default_rng(42))
        gain = ue.pivot(index="intervention_id", columns="group", values="gain_per_woman").reindex(self.names)[m5_options.CASCADE_GROUPS].values   # i x g
        gp = equity.group_pops(pop).set_index("cadaster_id")
        sc = scored.set_index("cadaster_id")
        self.cids = list(scored.sort_values("need_score", ascending=False).cadaster_id)
        wg = np.array([[gp.loc[c, g] * m5_options.DEFAULT_REACH_W[g] for g in m5_options.CASCADE_GROUPS] for c in self.cids])
        self.W = wg / np.maximum(wg.sum(axis=1, keepdims=True), 1e-9)                                  # c x g
        self.gain_c = self.W @ gain.T                                                                  # c x i : extra pathways per woman reached
        self.cost_mid = ((self.iv.cost_low_usd + self.iv.cost_high_usd) / 2).values
        self.ppl_mid = ((self.iv.people_low + self.iv.people_high) / 2).values
        self.cpw = self.cost_mid / self.ppl_mid                                                        # $ per woman reached (mid)
        self.ppd = self.gain_c / self.cpw[None, :]                                                     # c x i : pathways per $ (mid)
        self.best = int(np.argmax(self.gain_c.mean(axis=0) / self.cpw))
        n = len(self.cids)
        need = sc.loc[self.cids, "need_score"].values
        popc = sc.loc[self.cids, "population_total"].values
        preg = sc.loc[self.cids, "pregnant_est"].values.astype(float)
        cap = (sc.loc[self.cids, "access_current"] * sc.loc[self.cids, "women_15_49"]).values
        self.exposed = (sc.loc[self.cids, "conflict_incidents"].values >= unc["scenarios"]["S1_escalation"]["exposed_incidents_threshold"])
        self.staff_dep = np.array([i in unc["scenarios"]["S4_staff_loss"]["staff_dependent_interventions"] for i in self.names])
        self.hub = np.array([i == "hub_spoke_ereferral" for i in self.names])
        # Shares over ALL cadasters (money cannot usefully pile onto a handful of small cadasters, so need-based = proportional to need x pregnancies):
        need_share = need * preg / (need * preg).sum()
        self.share = {"top_down": need_share, "per_capita": popc / popc.sum(), "community": need_share.copy(),
                      "existing_allocation": cap / cap.sum()}                                             # follows current facility capacity
        pri = allocation.mock_priorities(self.cids, self.names, 8).set_index("cadaster_id").loc[self.cids, self.names].values    # c x i (mock)
        self.pri = pri
        self.preg = sc.loc[self.cids, "pregnant_est"].values.astype(float)        # annual pregnancies in the cadaster: reach cannot exceed it

    def value(self, policy: str, d: dict) -> float:
        """Extra pathways for `policy` in a world described by draw `d`. Women reached in a cadaster are capped at its pregnancies (saturation)."""   # noqa
        cm, lm = d["cost_mult"], d["lift_mult"]                                                          # per intervention
        eff = np.ones((len(self.cids), len(self.names)))
        eff[self.exposed, :] *= d["exposed_eff"]                                                          # S1
        eff[:, self.staff_dep] *= (1 - d["staff_loss"])                                                   # S4
        eff[:, self.hub] *= d["hub_factor"]                                                               # S3
        b = self.budget * d["budget_factor"] * self.share[policy]                                         # S2
        if policy == "community":
            best = np.zeros_like(self.pri)
            best[:, self.best] = 1.0
            lam = d.get("alignment", 0.0)
            mix = lam * best + (1 - lam) * self.pri
            mult, leak = d["local_fit"], d["capture"] + d["admin_cost"]
        else:
            mix = np.zeros_like(self.pri)
            mix[:, self.best] = 1.0
            mult, leak = 1.0, 0.0
        reached = b[:, None] * mix * (1 - min(leak, 1.0)) / (self.cpw * cm)[None, :]                       # women reached, c x i
        tot = reached.sum(axis=1)
        scale = np.where(tot > self.preg, self.preg / np.maximum(tot, 1e-9), 1.0)                          # saturation
        return float(((reached * scale[:, None]) * self.gain_c * lm[None, :] * eff).sum() * mult)


def _draw(scn: str | None, unc: dict, rng, center: bool = False, n_i: int = 0, iv=None) -> dict:
    P, S = unc["parameters"], unc["scenarios"]
    def u(lo, hi): return (lo + hi) / 2 if center else rng.uniform(lo, hi)
    d = {"capture": u(P["community_capture_rate"]["low"], P["community_capture_rate"]["high"]),
         "local_fit": u(P["community_local_fit"]["low"], P["community_local_fit"]["high"]),
         "admin_cost": u(P["community_admin_cost"]["low"], P["community_admin_cost"]["high"]),
         "budget_factor": 1.0, "exposed_eff": 1.0, "staff_loss": 0.0, "hub_factor": 1.0}
    cl, ch = iv.cost_low_usd.values, iv.cost_high_usd.values
    ll, lh = iv.lift_low.values, iv.lift_high.values
    mid_c, mid_l = (cl + ch) / 2, (ll + lh) / 2
    d["cost_mult"] = ((cl + ch) / 2 if center else rng.uniform(cl, ch)) / mid_c
    d["lift_mult"] = ((ll + lh) / 2 if center else rng.uniform(ll, lh)) / mid_l
    if scn == "S1_escalation":
        d["exposed_eff"] = u(*S[scn]["policy_effect_multiplier_exposed"])
    elif scn == "S2_funding_shock":
        d["budget_factor"] = float(np.mean(S[scn]["pool_factor"])) if center else float(rng.choice(S[scn]["pool_factor"]))
    elif scn == "S3_power_collapse":
        d["hub_factor"] = u(*S[scn]["hub_spoke_effect_factor"])
    elif scn == "S4_staff_loss":
        d["staff_loss"] = u(*S[scn]["capacity_loss"])
    return d


def policy_regret(scored: pd.DataFrame, budget: float = 100_000, n: int | None = None, seed: int | None = None, unc: dict | None = None,
                  top_k: int | None = None) -> dict:
    """Regret of each allocation policy: (best policy's value in that world) - (this policy's value). Prefer the policy that minimises MAXIMUM regret."""
    unc = unc or load_uncertainty()
    n = n or unc["n_draws"]
    k = top_k or unc["top_k"]
    rng = np.random.default_rng(seed if seed is not None else unc["seed"])
    eng = _Engine(scored, k, budget, unc)
    rows = []
    for scn in ["baseline"] + SCENARIO_IDS:
        sid = None if scn == "baseline" else scn
        for j in range(n):
            d = _draw(sid, unc, rng, iv=eng.iv)
            v = {p: eng.value(p, d) for p in POLICIES}
            best = max(v.values())
            for p in POLICIES:
                rows.append({"scenario": scn, "policy": p, "value": v[p], "regret": best - v[p], "regret_pct": (best - v[p]) / best if best > 0 else 0.0})
    df = pd.DataFrame(rows)
    by_s = df.groupby(["scenario", "policy"]).agg(mean_value=("value", "mean"), p05_value=("value", lambda x: np.percentile(x, 5)),
                                                    p95_value=("value", lambda x: np.percentile(x, 95)), mean_regret=("regret", "mean"),
                                                    max_regret=("regret", "max")).reset_index()
    summ = df.groupby("policy").agg(mean_value=("value", "mean"), mean_regret=("regret", "mean"), p95_regret=("regret", lambda x: np.percentile(x, 95)),
                                    max_regret=("regret", "max"), max_regret_pct=("regret_pct", "max")).reset_index()
    summ["minimax_rank"] = summ.max_regret.rank(method="min").astype(int)
    summ["best_on_average_rank"] = summ.mean_value.rank(ascending=False, method="min").astype(int)
    winner = summ.sort_values("max_regret").iloc[0].policy
    avg_winner = summ.sort_values("mean_value", ascending=False).iloc[0].policy
    return {"by_scenario": by_s, "summary": summ.sort_values("max_regret").reset_index(drop=True), "minimax_policy": winner, "best_on_average": avg_winner,
            "disagree": winner != avg_winner, "n_draws": n, "is_mock": True}


# ---------------------------------------------------------------- breakpoints
def breakpoints(scored: pd.DataFrame, budget: float = 100_000, unc: dict | None = None, top_k: int | None = None) -> pd.DataFrame:
    """Assumption values at which 'community beats top-down' flips (everything else at the centre of its range)."""
    unc = unc or load_uncertainty()
    eng = _Engine(scored, top_k or unc["top_k"], budget, unc)
    rng = np.random.default_rng(0)
    base = _draw(None, unc, rng, center=True, iv=eng.iv)
    base["alignment"] = 0.0

    def ratio(**kw):
        d = {**base, **kw}
        return eng.value("community", d) / eng.value("top_down", d)

    def solve(name, lo, hi):
        f = lambda x: ratio(**{name: x}) - 1.0
        if f(lo) * f(hi) > 0:
            return None
        for _ in range(60):
            mid = (lo + hi) / 2
            if f(lo) * f(mid) <= 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    rows = []
    for align, tag in ((0.0, "as modelled (mock community priorities)"), (1.0, "best case (communities pick the most cost-effective option)")):
        for name, lo, hi, text in (("capture", 0.0, 0.9, "community arm beats top-down only while capture <"),
                                   ("admin_cost", 0.0, 0.9, "... only while committee admin cost <"),
                                   ("local_fit", 0.8, 3.0, "... only if the local-fit multiplier >")):
            b2 = {**base, "alignment": align}

            def f(x, name=name, b2=b2):
                d = {**b2, name: x}
                return eng.value("community", d) / eng.value("top_down", d) - 1.0
            x = None
            if f(lo) * f(hi) <= 0:
                l, h = lo, hi
                for _ in range(60):
                    m = (l + h) / 2
                    l, h = (l, m) if f(l) * f(m) <= 0 else (m, h)
                x = (l + h) / 2
            rows.append({"priorities": tag, "assumption": name, "flips_at": x, "reading": f"{text} {x:.2f}" if x is not None else "no flip inside the tested range",
                         "central_value": base[name], "ratio_community_vs_top_down_at_centre": f(base[name]) + 1.0})
        # alignment itself (only once)
        if align == 0.0:
            def fa(x):
                d = {**base, "alignment": x}
                return eng.value("community", d) / eng.value("top_down", d) - 1.0
            x = None
            if fa(0.0) * fa(1.0) <= 0:
                l, h = 0.0, 1.0
                for _ in range(60):
                    m = (l + h) / 2
                    l, h = (l, m) if fa(l) * fa(m) <= 0 else (m, h)
                x = (l + h) / 2
            rows.append({"priorities": tag, "assumption": "alignment", "flips_at": x,
                         "reading": (f"community beats top-down only if the share of its priorities on the most cost-effective option > {x:.2f}" if x is not None
                                     else "no flip inside the tested range"),
                         "central_value": 0.0, "ratio_community_vs_top_down_at_centre": fa(0.0) + 1.0})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- escrow graceful degradation
def escrow_degradation(scored: pd.DataFrame, unc: dict | None = None) -> pd.DataFrame:
    """Does the escrow pause or fall back safely under S2 (funding shock), S5 (capacity stall) and S1 (escalation), and under all three?"""
    unc = unc or load_uncertainty()
    pool = escrow.run(scored)[0]
    base_pool = float(pool.released_usd.sum() + pool.held_in_escrow_usd.sum())
    worlds = {"baseline": {}, "S2 funding -50%": {"pool_factor": 0.5}, "S2 funding -70%": {"pool_factor": 0.3},
              "S5 capacity stall (0 gain/yr)": {"yoy_gain": 0.0}, "S1 escalation from 2028": {"escalation_year": 2028},
              "S1+S2+S5 combined": {"pool_factor": 0.5, "yoy_gain": 0.0, "escalation_year": 2028}}
    rows = []
    for name, kw in worlds.items():
        pf = kw.pop("pool_factor", 1.0)
        d, summ, warns = escrow.run(scored, pool=base_pool * pf, **kw)
        rel, held = float(d.released_usd.sum()), float(d.held_in_escrow_usd.sum())
        rows.append({"world": name, "pool_usd": base_pool * pf, "released_usd": rel, "held_in_escrow_usd": held,
                     "conserved": abs(rel + held - base_pool * pf) < 1.0,
                     "share_lebanese_managed_2030": float(summ.share_lebanese_managed.iloc[-1]),
                     "towns_with_tranche_held": int((d.groupby("cadaster_id").held_in_escrow_usd.sum() > 0).sum()),
                     "need_floor_still_paid": bool((d.need_floor_usd.sum() > 0) and (rel >= d.need_floor_usd.sum() - 1.0)),
                     "n_warnings": len(warns)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- everything
def run_all(n: int | None = None, seed: int | None = None, budget: float = 100_000) -> dict:
    unc = load_uncertainty()
    rk = rank_robustness(n=n, seed=seed, unc=unc)
    scored = m2.compute(scenario_raw(None, 30, 0.1, unc), spec=m2.load_spec())
    pr = policy_regret(scored, budget, n=n, seed=seed, unc=unc)
    return {"rank": rk, "regret": pr, "breakpoints": breakpoints(scored, budget, unc), "escrow": escrow_degradation(scored, unc), "unc": unc, "scored": scored}
