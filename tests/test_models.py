import numpy as np
import pandas as pd
import pytest

from beqaa import allocation, chat, equity, escrow, io, m1_access, m2_need_score as m2, m4_exposure, m5_options, viz


def test_e2sfca_conservation():
    """Sum of demand-weighted access equals total capacity of facilities with demand in their catchment."""
    pop, _ = io.load_dataset("population"); fac, _ = io.load_dataset("facilities"); tt, _ = io.load_dataset("travel_time")
    for scen in ("baseline_pre2026", "current_2026"):
        a = m1_access.e2sfca(pop, fac, tt, 30, "women_15_49", "all", scen)
        f = fac if scen == "baseline_pre2026" else fac[fac.status_2026 == "open"]
        T = tt[tt.facility_id.isin(f.facility_id)].pivot(index="cadaster_id", columns="facility_id", values="minutes")
        has_demand = (T <= 30).any(axis=0)
        cap = f.set_index("facility_id").loc[has_demand[has_demand].index, "capacity_weekly"].sum()
        served = (a.access.values * pop.women_15_49.values).sum()
        assert served == pytest.approx(cap, rel=1e-6)


def test_closures_never_increase_access():
    a = m1_access.access_by_cadaster()
    assert (a.access_lost >= -1e-12).all()


def test_group_access_and_weighted_demand():
    acc = m1_access.access_by_cadaster(30, "weighted_women_15_49", demand_weights={"unregistered_workers_est": 2.0})
    g = m1_access.group_access(acc)
    assert set(g.group) == set(equity.GROUPS) and abs(g.set_index("group").loc["host_lebanese", "ratio_to_host"] - 1) < 1e-9


def test_need_score_bounded_and_weights_sum():
    spec = m2.load_spec()
    assert sum(spec["domain_weights"].values()) == pytest.approx(1.0)
    raw = m2.raw_indicators()
    for geo in (False, True):
        s = m2.compute(raw, geometric=geo)
        assert s.need_score.between(0, 1).all()
        assert sum(s.attrs["weights_used"].values()) == pytest.approx(1.0)


def test_robustness_probabilities():
    r = m2.robustness(m2.raw_indicators(), n=500)
    assert r.p_top_tier.between(0, 1).all() and (r.rank_p05 <= r.rank_p95).all()
    assert r.p_top_tier.sum() == pytest.approx(m2.load_spec()["top_k"], abs=1e-6)


def test_chemstar_hq_sanity():
    p = m4_exposure.load_params()
    assert m4_exposure.cr_hq(230, "child", 0.0, 0, p) == pytest.approx(0.002, abs=5e-4)
    assert m4_exposure.cr_hq(230, "child", 1.0, 0, p) == pytest.approx(0.98, abs=0.01)


def test_no_site_gets_rung_c():
    assert (m4_exposure.screen_sites().evidence_rung != "c").all()


def test_m5_budget_tiers():
    ft = m5_options.fundable_table(1000).set_index("intervention_id")
    assert ft.loc["mobile_maternal_unit", "p_fundable"] == 0 and ft.loc["sunflower_biochar_plot", "p_fundable"] > 0.9
    ev = m5_options.evaluate(["transport_vouchers"], 100_000)
    assert ev.extra_pathways_median.iloc[0] > 0


def test_allocation_three_regimes():
    s, d = allocation.simulate(m2.compute(m2.raw_indicators()), 100_000)
    assert set(s.regime) == set(allocation.REGIMES)
    assert (s.equity_gap_after >= 0).all()
    safe, _ = allocation.simulate(m2.compute(m2.raw_indicators()), 100_000, params={"women_seat_share": 0.3, "worker_seat_share": 0.3})
    assert safe.set_index("regime").loc["community", "capture_loss_rate"] == 0


def test_escrow_conserves_pool():
    sc = m2.compute(m2.raw_indicators())
    d, _, w = escrow.run(sc, 1_000_000, 8, 0.5)
    assert (d.released_usd + d.held_in_escrow_usd).sum() == pytest.approx(1_000_000)
    d2, _, _ = escrow.run(sc, 1_000_000, 8, 0.5, unrestricted=True)
    assert d2.held_in_escrow_usd.sum() == 0


def test_mock_watermark_on_mock_figures(tmp_path):
    sc = m2.compute(m2.raw_indicators())
    assert viz.watermark(__import__("matplotlib.pyplot", fromlist=["x"]).figure(), True) is not None
    assert viz.watermark(__import__("matplotlib.pyplot", fromlist=["x"]).figure(), False) is None
    viz.priority_map(sc, True, tmp_path / "f.png")
    assert (tmp_path / "f.png").exists()


def test_chatbot_refuses_without_match_and_cites_rows():
    assert chat.answer("cryptocurrency mining subsidies")["answer"] == chat.NO_MATCH
    a = chat.answer("World Bank LEAP health")
    assert "F008" in a["citations"] and "http" in a["answer"]


def test_wdi_lebanon_series():
    d = io.load_wdi_population("LBN")
    assert d is None or (d.population.between(1e6, 1e7).all() and 2019 in set(d.year))


def test_every_mock_file_declares_a_real_source():
    """Keeps mock data honest: each mock file must say where the real data would come from and how obtainable it is."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    prov = pd.read_csv(root / "data" / "registry" / "mock_provenance.csv")
    files = {f.name for f in (root / "data" / "mock").glob("*.csv")}
    assert files == set(prov.mock_file), (files ^ set(prov.mock_file))
    assert set(prov.obtainability) <= {"public_download", "public_download+transcribe", "transcribe", "partner_request", "literature", "pilot_measured"}


def test_facility_risk_and_pause_scenario():
    r = m1_access.facility_risk(15)
    assert {"power_source", "conflict_exposed", "needs_backup_or_pause_plan"} <= set(r.columns) and len(r) > 0
    p = m1_access.access_if_exposed_pause(30, "women_15_49", 15)
    assert (p.access_lost_to_pause >= -1e-12).all()
    none = m1_access.access_if_exposed_pause(30, "women_15_49", 10_000)          # nothing exposed -> nothing lost
    assert none.access_lost_to_pause.abs().max() < 1e-12


def test_conflict_indicator_in_need_score():
    raw = m2.raw_indicators()
    assert "conflict_incidents" in raw.columns and raw.conflict_incidents.ge(0).all()
    s = m2.compute(raw)
    assert "s_conflict_incidents" in s.columns and s.need_score.between(0, 1).all()

def test_feasibility_filter_flags():
    ft = m5_options.feasibility_table().set_index("intervention_id")
    assert "F6" in ft.loc["hub_spoke_ereferral", "flags"] and ft.loc["cr_speciation_tests", "feasible"]
    assert not ft.loc["transport_vouchers", "feasible"]


def test_escrow_max_level_escalation_and_capacity_cap():
    sc = m2.compute(m2.raw_indicators())
    d, s, _ = escrow.run(sc, 1_000_000, 8, 0.5)
    assert "MoPH" not in set(d.administered_by_floor) | set(d.administered_by_tranche)
    d2, s2, w2 = escrow.run(sc, 1_000_000, 8, 0.5, escalation_year=2028)
    assert (d2[d2.year >= 2028].admin_capacity_index.values <= d[d.year >= 2028].admin_capacity_index.values + 1e-12).all()
    assert any("escalation" in x for x in w2) and s.share_lebanese_managed.between(0, 1).all()
    gov, _ = io.load_dataset("governance_capacity")
    p = gov.pivot(index="year", columns="district", values="admin_capacity_index").diff().loc[2027:]
    assert p.max().max() <= escrow.MAX_YOY_CAPACITY_GAIN + 1e-9


def test_allocation_sensitivity_grid():
    g = allocation.sensitivity(m2.compute(m2.raw_indicators()), 100_000)
    assert g.shape == (4, 4) and (g.values > 0).all()


def test_method_sensitivity_and_aggregation_options():
    raw = m2.raw_indicators()
    ms = m2.method_sensitivity(raw)
    assert ms.iloc[0].variant == "reference" and ms.iloc[0].spearman_vs_reference == 1.0 and ms.iloc[0].top_k_retained == ms.iloc[0].top_k
    assert ms.spearman_vs_reference.between(-1, 1).all() and ms.top_k_jaccard.between(0, 1).all() and len(ms) >= 10
    for agg in ("arithmetic", "geometric", "max"):
        assert m2.compute(raw, aggregation=agg).need_score.between(0, 1).all()
    assert m2.compute(raw, normalization="percentile").need_score.between(0, 1).all()


def test_default_weights_equal_and_quantile_anchors():
    spec = m2.load_spec()
    assert len(set(spec["domain_weights"].values())) == 1                                  # D4: equal by default
    raw = m2.raw_indicators()
    new = m2.apply_quantile_anchors(spec, raw)
    q = [i for inds in new["domains"].values() for i in inds if i.get("anchor") == "quantile"]
    assert q and all(i["safe"] != i["crisis"] for i in q)
    assert m2.compute(raw, spec=new).need_score.between(0, 1).all()
    phc = next(i for i in spec["domains"]["capacity_strain"] if i["name"] == "phc_per_50k")
    assert (phc["safe"], phc["crisis"]) == (3, 0.5) and phc["anchor"] == "published"


def test_stale_data_missing_an_indicator_does_not_crash():
    """A cached frame built before an indicator existed (e.g. after switching branches) must be skipped visibly, not raise KeyError."""
    raw = m2.raw_indicators().drop(columns=["conflict_incidents"])
    s = m2.compute(raw)
    assert s.attrs["skipped_indicators"] == ["conflict_incidents"] and s.need_score.between(0, 1).all()
