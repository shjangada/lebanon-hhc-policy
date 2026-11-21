"""Model linkage: funding registry statuses, state-capacity anchor, P5 escrow flow, M4 -> M2 -> priority, research gaps."""
import pandas as pd
import pytest

from beqaa import allocation, escrow, funding_finder as ff, m2_need_score as m2, research_gaps, state_capacity


@pytest.fixture(scope="module")
def scored_rob():
    raw = m2.raw_indicators()
    return m2.compute(raw), m2.robustness(raw, n=500)


def test_funding_statuses_and_toggles():
    f = ff.annotate(ff.load_funding())
    default = ff.filter_funding(f)
    assert not set(default.status) & {"closed", "closed_recurring", "active_closed_to_new"}
    nr = ff.filter_funding(f, show_next_round=True)
    rec = nr[nr.status == "closed_recurring"]
    assert len(rec) and (rec.availability == "expected next round").all() and "closed" not in set(nr.status)
    assert "closed" in set(ff.filter_funding(f, active_only=False, show_closed=True).status) or "closed" not in set(f.status)


def test_involvement_ranking_puts_core_flexible_first():
    f = ff.annotate(ff.load_funding())
    r = ff.rank_involvement(f)
    top = r.iloc[0]
    assert top.involvement_level.startswith("low donor involvement") and top.low_donor_involvement
    assert set(r.fund_id) == set(ff.load_funding().fund_id)          # ranking never adds rows


def test_funding_datasets_load():
    d = ff.load_datasets()
    assert {"dataset_id", "url", "use"} <= set(d.columns) and d.dataset_id.str.match(r"D\d{2}").all()


def test_state_capacity_anchor_and_cap():
    nb = state_capacity.national_baseline()
    assert nb["admin_anchor"] == pytest.approx(0.299) and nb["fiscal_anchor"] == pytest.approx(0.134)
    g = state_capacity.anchored_governance()
    actual = g[~g.projected]
    ay = actual[actual.year == 2026]
    assert ay.admin_capacity_index.mean() == pytest.approx(nb["admin_anchor"], abs=1e-6)
    p = g.pivot(index="year", columns="district", values="admin_capacity_index").diff().loc[2027:]
    assert p.max().max() <= escrow.MAX_YOY_CAPACITY_GAIN + 1e-9
    assert g.is_mock.all() and g.capacity_status.str.contains("mock").all()


def test_escrow_flow_conserves_and_roles(scored_rob):
    sc, _ = scored_rob
    d, s, w = escrow.run(sc, 1_000_000)
    links = escrow.flow_links(d)
    inflow = links[links.source == escrow.SOURCE_NODE].value_usd.sum()
    to_districts = links[links.target.str.startswith("District:")].value_usd.sum()
    assert inflow == pytest.approx(1_000_000) and to_districts == pytest.approx(d.released_usd.sum())
    held = links[links.target == "Capacity tranche: held in escrow"].value_usd.sum()
    assert to_districts + held == pytest.approx(1_000_000)
    roles = escrow.role_table(d)
    assert roles.set_index("level").loc["MoPH", "town_years_at_level"] == 0 and not roles.set_index("level").loc["MoPH", "allowed_by_default"]
    assert roles.decides_use.str.contains("Community committee").all()
    assert any("Capacity anchor" in x for x in w)


def test_need_gate_and_env_weight(scored_rob):
    sc, _ = scored_rob
    d, _, _ = escrow.run(sc, 1_000_000, need_min=0.5)
    assert (d.need_score >= 0.5).all()
    p0, p1 = escrow.priority_score(sc, 0.0), escrow.priority_score(sc, 0.5)
    assert (p0 == sc.need_score).all() and not (p1 == p0).all()
    a0, d0 = allocation.simulate(sc, 100_000, env_weight=0.0)
    a1, d1 = allocation.simulate(sc, 100_000, env_weight=0.5)
    assert not d0.set_index(["regime", "cadaster_id"]).budget_usd.equals(d1.set_index(["regime", "cadaster_id"]).budget_usd)


def test_m4_feeds_m2_via_cr6_assumption():
    hi = m2.compute(m2.raw_indicators())                    # precautionary (all Cr(VI))
    lo = m2.compute(m2.raw_indicators(cr6_for_tier=0.0))     # all Cr(III)
    assert lo.soil_hotspot_proximity.sum() < hi.soil_hotspot_proximity.sum()
    assert lo.D_environment.mean() < hi.D_environment.mean()


def test_research_candidates_link_only_registry_rows(scored_rob):
    sc, rob = scored_rob
    g = research_gaps.cadaster_gaps(sc, rob)
    assert g.evidence_gap_score.between(0, 1).all()
    c = research_gaps.research_candidates(g)
    reg = ff.load_funding().set_index("fund_id")
    ids = {i for s in c.registry_fund_ids for i in s.split("; ") if i}
    assert ids <= set(reg.index) and not (reg.loc[list(ids), "status"] == "closed").any()
    assert (c.need_score >= 0.33).all()
