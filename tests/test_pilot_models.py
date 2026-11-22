import numpy as np
import pandas as pd
import pytest

from beqaa import io, m6_illness_averted as m6, pilot_flow as pf, start_site as ss

need = pytest.mark.skipif(not (io.PROCESSED / "esu_by_district.csv").exists(), reason="run `python -m beqaa.ingest pilot_data`")


def test_funnel_arithmetic_is_conserved_and_monotone():
    f = pf.funnel(10_000, {"coverage": 0.5, "screened_share": 0.4, "positive_rate": 0.2, "chw_share": 0.75, "completion": 0.6}).set_index("stage").people
    assert f["reached"] == 5000 and f["screened"] == 2000 and f["symptomatic / positive"] == pytest.approx(400)
    assert f["handled by CHWs"] + f["red flags referred"] == pytest.approx(f["symptomatic / positive"])          # nothing lost between stages
    assert f["referral completed"] == pytest.approx(f["red flags referred"] * 0.6)
    assert (f.diff().dropna()[:4] <= 0).all()                                                                      # each stage is a subset of the previous one


def test_water_floor_quarterly_fails_monthly_passes():
    d = pf.compare_schedules(2000, 5)
    assert d.set_index("water_interval_months").gdwq_floor_ok.to_dict() == {1: True, 3: False}


def test_schedule_costs_use_sourced_prices_and_longer_intervals_cost_less():
    a, b = pf.schedule(2000, 5, 1, 1), pf.schedule(2000, 5, 2, 3)
    assert b["cost_per_month_usd"] < a["cost_per_month_usd"] and b["expected_wait_days"] == 7.0 and a["expected_wait_days"] == 3.5


def test_routing_breaks_even_share_when_spare_is_tiny():
    cent = pd.DataFrame({"facility_id": ["A", "B"], "capacity_weekly": [300, 300]})
    sites = pd.DataFrame({"cadaster_id": ["x", "y"], "cadaster_name": ["x", "y"], "settlement_people_2016": [40_000, 40_000]})
    tt = pd.DataFrame({"cadaster_id": ["x", "x", "y"], "facility_id": ["A", "B", "A"], "minutes": [10, 20, 10]})
    people = {"x": 40_000.0, "y": 40_000.0}
    be = pf.break_even_chw_share(sites, cent, tt, people, {"spare_share": 0.05, "positive_rate": 0.3, "screened_share": 0.9, "coverage": 1.0})
    assert 0 < be < 1
    below = pf.route_red_flags(sites, cent, tt, {c: pf.funnel(n, {"coverage": 1.0, "screened_share": 0.9, "positive_rate": 0.3, "chw_share": be - 0.01}).set_index("stage").people["red flags referred"] for c, n in people.items()}, {"spare_share": 0.05})
    assert below.over_limit.any()


@need
def test_m6_baseline_and_effects():
    b = m6.baseline_cases()
    assert set(b.index) == {"Baalbek", "Hermel", "Rachaya", "West Bekaa", "Zahle"} and (b > 0).all()
    r = m6.simulate("Baalbek", 5000, 100_000, "filtration", 1.0, chw_months=0)
    assert r["cases_averted_p05"] <= r["cases_averted_median"] <= r["cases_averted_p95"]
    none = m6.simulate("Baalbek", 5000, 100_000, "filtration", 0.0)
    assert none["cases_averted_median"] == 0                                                                     # transfer 0 = no effect
    big = m6.simulate("Baalbek", 10_000, 100_000, "filtration", 1.0, chw_months=0)
    assert big["cases_averted_median"] == pytest.approx(2 * r["cases_averted_median"], rel=0.05)                 # linear in coverage
    assert big["cost_per_case_averted_median"] == pytest.approx(r["cost_per_case_averted_median"], rel=0.1)


@need
def test_start_site_scores_are_bounded_and_costs_nonnegative():
    r = ss.score()
    assert r.start_score.between(0, 1).all() and (r.startup_low_usd <= r.startup_central_usd).all() and (r.startup_central_usd <= r.startup_high_usd).all()
    heavy = ss.score(weights={"soil": 20.0})
    assert heavy.iloc[0].soil == 1.0                                                                             # a heavy soil weight puts a soil-covered site first
    assert (r.start_rank >= 1).all() and r.cadaster_id.is_unique


@need
def test_rank_stability_is_reproducible_and_shares_are_valid():
    a, b = ss.rank_stability(n=200, seed=1), ss.rank_stability(n=200, seed=1)
    pc = a["per_cadaster"]
    assert pc.equals(b["per_cadaster"])                                                                           # seeded
    assert pc.top1_random.sum() == pytest.approx(1.0) and pc.top3_random.sum() == pytest.approx(3.0)              # exactly one first place and three top-3 places per draw
    assert (pc.top10_random >= pc.top3_random).all() and (pc.top3_random >= pc.top1_random).all()
    assert set(a["summary"]["district_of_first_site"]["random"]) <= {"Baalbek", "Hermel", "Zahle", "West Bekaa", "Rachaya"}


@need
def test_docs_quote_the_current_start_site_numbers(monkeypatch):
    """The start-site result quoted in FEASIBILITY.md and NARRATIVE.md must equal what the code computes (guards against the documents drifting from the model)."""
    import pathlib
    monkeypatch.setenv("BEQAA_DATA", "auto")
    root = pathlib.Path(__file__).resolve().parents[1]
    r = ss.score()
    st = ss.rank_stability(ss.criteria())["summary"]
    first = r.iloc[0].cadaster_name
    feas, nar = (root / "docs" / "FEASIBILITY.md").read_text(), (root / "docs" / "NARRATIVE.md").read_text()
    assert first in feas and first in nar and st["random"]["baseline_first_site"] == first
    pct = lambda x: f"{x * 100:.0f}%"
    assert f"first in {pct(st['perturb']['baseline_first_share_top1'])} of draws" in feas
    assert f"first in {pct(st['random']['baseline_first_share_top1'])}" in feas and f"top 3 in {pct(st['random']['baseline_first_share_top3'])}" in feas
    d = st["district_of_first_site"]["random"]
    for name, v in d.items():
        assert f"{name} {pct(v)}" in feas
    for name in ("Bouday", "Chmistar"):
        assert f"rank {int(r[r.cadaster_name == name].start_rank.iloc[0])}" in nar


@need
def test_implementation_doc_matches_the_model(monkeypatch):
    import importlib.util
    import pathlib
    monkeypatch.setenv("BEQAA_DATA", "auto")
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("mk", root / "scripts" / "make_implementation.py")
    mk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mk)
    assert (root / "docs" / "IMPLEMENTATION.md").read_text() == mk.render()           # regenerate with scripts/make_implementation.py


def test_memo_support_docs_exist_with_their_required_columns():
    import pathlib
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs"
    tr = (docs / "TRIGGERS.md").read_text()
    assert "| Medium | Finding | Threshold | Action | Who acts | Referral | Follow-up |" in tr and "total P cannot establish munition exposure" in tr
    au = (docs / "HEADLINE_AUDIT.md").read_text()
    assert "| Number | Where used | File | Source | Status |" in au and "drop" in au and "ok" in au
    assert all((docs / f).exists() for f in ("OPTIONS.md", "DECISION_ROUTE.md", "OBJECTIONS.md", "IMPLEMENTATION.md"))


@need
def test_all_zero_weights_fall_back_to_equal_weights():
    z = ss.score(weights={k: 0.0 for k in ss.CRITERIA})
    e = ss.score()
    assert z.start_score.notna().all() and (z.set_index("cadaster_id").start_score == e.set_index("cadaster_id").start_score).all()
