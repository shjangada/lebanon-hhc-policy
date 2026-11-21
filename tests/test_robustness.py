import numpy as np
import pandas as pd
import pytest

from beqaa import m2_need_score as m2, robustness as rb

UNC = rb.load_uncertainty()


@pytest.fixture(scope="module")
def scored():
    return m2.compute(rb.scenario_raw(None, 30, 0.1, UNC), spec=m2.load_spec())


def test_seeded_runs_reproduce():
    a = rb.rank_robustness(n=60, seed=7)["per_cadaster"].set_index("cadaster_id").p_top_overall
    b = rb.rank_robustness(n=60, seed=7)["per_cadaster"].set_index("cadaster_id").p_top_overall
    pd.testing.assert_series_equal(a, b)


def test_zero_variance_equals_baseline():
    """One draw of default parameters must reproduce the baseline top-k exactly."""
    r = rb.rank_robustness(zero_variance=True)
    ref = m2.compute(rb.scenario_raw(None, 30, 0.1, UNC), spec=m2.load_spec())
    top = set(ref.nsmallest(r["top_k"], "rank").cadaster_id)
    p = r["per_cadaster"].set_index("cadaster_id")
    assert set(p[p.p_top_baseline == 1.0].index) == top and r["n_draws"] == 1
    assert r["scenarios"].iloc[0].kendall_tau_vs_baseline == 1.0


def test_core_set_is_nonempty_or_warns():
    r = rb.rank_robustness(n=120)
    assert r["core"] or r["warning"]
    p = r["per_cadaster"]
    assert p.p_top_overall.between(0, 1).all() and (p.rank_p05 <= p.rank_p95).all()
    assert set(p[p.core].cadaster_name) == set(r["core"])


def test_scenarios_change_the_world_in_the_right_direction():
    base = rb.scenario_raw(None, 30, 0.1, UNC)
    for scn in ("S1_escalation", "S3_power_collapse", "S4_staff_loss"):
        w = rb.scenario_raw(scn, 30, 0.1, UNC)
        assert w.access_current.sum() <= base.access_current.sum() + 1e-12, scn           # access never improves
    s1 = rb.scenario_raw("S1_escalation", 30, 0.1, UNC)
    assert s1.access_current.sum() < base.access_current.sum()
    assert rb.scenario_raw("S6_worst_case_contamination", 30, 1.0, UNC).soil_hotspot_proximity.sum() >= base.soil_hotspot_proximity.sum()


def test_regret_properties(scored):
    r = rb.policy_regret(scored, 100_000, n=80, seed=3)
    s = r["summary"]
    assert set(s.policy) == set(rb.POLICIES) and (s.mean_regret >= -1e-9).all()
    assert r["minimax_policy"] == s.sort_values("max_regret").iloc[0].policy                  # minimax = smallest maximum regret
    bs = r["by_scenario"]
    for scn, g in bs.groupby("scenario"):
        assert g.mean_regret.min() == pytest.approx(0.0, abs=g.mean_value.max() * 0.2)        # someone is (nearly) best in each world


def test_funding_shock_cannot_raise_value(scored):
    eng = rb._Engine(scored, 8, 100_000, UNC)
    rng = np.random.default_rng(0)
    d0 = rb._draw(None, UNC, rng, center=True, iv=eng.iv)
    d1 = {**d0, "budget_factor": 0.5}
    for p in rb.POLICIES:
        assert eng.value(p, d1) <= eng.value(p, d0) + 1e-9


def test_breakpoints_are_inside_tested_ranges(scored):
    b = rb.breakpoints(scored, 100_000, UNC)
    ok = b.dropna(subset=["flips_at"])
    assert (ok.flips_at >= 0).all() and set(b.assumption) >= {"capture", "admin_cost", "local_fit", "alignment"}


def test_escrow_degrades_gracefully(scored):
    d = rb.escrow_degradation(scored, UNC)
    assert d.conserved.all() and d.need_floor_still_paid.all()                                # money conserved; the need floor is still paid out
    comb = d.set_index("world").loc["S1+S2+S5 combined"]
    assert comb.share_lebanese_managed_2030 <= d.set_index("world").loc["baseline"].share_lebanese_managed_2030 + 1e-9
