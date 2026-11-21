import numpy as np
import pytest

from beqaa import breakeven, m2_need_score as m2, robustness as rb


@pytest.fixture(scope="module")
def setup():
    unc = rb.load_uncertainty()
    scored = m2.compute(rb.scenario_raw(None, 30, 0.1, unc), spec=m2.load_spec())
    return scored, unc


def test_centre_ratios_match_the_engine_ordering(setup):
    """With every parameter at the centre of its range, the break-even report's ratios equal the allocation engine's values (same ordering as the regret ranking)."""
    scored, unc = setup
    be = breakeven.allocation_breakevens(scored, 100_000, unc)
    eng, base = breakeven._engine(scored, 100_000, unc)
    v = {p: eng.value(p, base) for p in rb.POLICIES}
    r = be[(be.comparison == "community vs status quo") & (be.parameter == "capture") & be.priorities.str.startswith("community priorities as modelled")].iloc[0]
    assert np.isclose(r.ratio_at_centre, v["community"] / v["existing_allocation"])
    r2 = be[(be.comparison == "community vs top-down by need") & (be.parameter == "local_fit") & be.priorities.str.startswith("community priorities as modelled")].iloc[0]
    assert np.isclose(r2.ratio_at_centre, v["community"] / v["top_down"])


def test_flip_points_are_real_flips(setup):
    scored, unc = setup
    be = breakeven.allocation_breakevens(scored, 100_000, unc)
    eng, base = breakeven._engine(scored, 100_000, unc)
    for r in be[be.flips_at.notna()].itertuples():
        a, b = ("community", "existing_allocation") if "status quo" in r.comparison else ("community", "top_down")
        bb = {**base, "alignment": 1.0 if r.priorities.startswith("community picks") else 0.0}
        eps = 1e-3
        lo, hi = ({**bb, r.parameter: r.flips_at - eps}, {**bb, r.parameter: r.flips_at + eps})
        ra, rb_ = eng.value(a, lo) / eng.value(b, lo), eng.value(a, hi) / eng.value(b, hi)
        assert (ra - 1) * (rb_ - 1) <= 0, r


def test_escrow_breakevens_follow_the_rules():
    t = breakeven.escrow_breakevens()
    assert set(t.threshold) == {"referral completion", "posts filled", "transparent reporting", "district admin capacity"}
    assert "40%" in t.loc[t.threshold == "referral completion", "release_needs"].iloc[0]
