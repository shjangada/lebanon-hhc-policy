import numpy as np
import pandas as pd
import pytest

from beqaa import escrow, io, unit_costs as uc

need = pytest.mark.skipif(not (io.PROCESSED / "prices_pack.csv").exists(), reason="run ingest")


@need
def test_every_unit_cost_has_a_source_year_and_a_lebanon_flag():
    u = uc.unit_costs()
    assert u.source.notna().all() and u.year.notna().all() and set(u.lebanon_price) == {"y", "n"} and (u.central > 0).all()
    assert (u.low.fillna(u.central) <= u.central).all() and (u.central <= u.high.fillna(u.central)).all()
    n = set(u[u.lebanon_price == "n"].item)
    assert "Cr(VI) speciation in soil" in n and "Household ceramic water filter" in n               # no Lebanese price: flagged, never presented as local


@need
def test_kpis_carry_the_escrow_triggers_and_equity_splits():
    k = uc.kpis()
    r = escrow.DEFAULT_RULES
    t = " ".join(k.escrow_trigger.fillna(""))
    assert f"{r['referral_min']:.2f}" in t and f"{r['posts_filled_min']:.2f}" in t and f"{r['admin_capacity_min']:.2f}" in t
    assert k.splits.str.contains("registration status").all() and k.splits.str.contains("settlement vs village").all()
    assert k.baseline.notna().all() and k.target.notna().all()


@need
def test_cost_metrics_are_positive_ordered_and_flagged_as_upper_bound(monkeypatch):
    monkeypatch.setenv("BEQAA_DATA", "auto")                         # real cadasters and ESU districts (the mock district names do not match the ESU cazas)
    m = uc.cost_metrics()
    c = m["cost_per_household_usd"]
    assert 0 < c["low"] <= c["central"] <= c["high"]
    p = m["cost_per_notified_case_averted_usd"]
    assert p["p05"] <= p["median"] <= p["p95"] and "UPPER BOUND" in m["note"]
