import numpy as np
import pandas as pd
import pytest

from beqaa import riders


def test_every_price_traces_to_a_cost_item():
    p = riders.unit_prices()
    assert p.cost_item.notna().all() and (p.usd_low <= p.usd_central).all() and (p.usd_central <= p.usd_high).all()
    assert set(p.unit) == {"nitrate_water", "cr_water", "soil_total_cr", "chw_month", "phc_service"}


def _projects():
    return pd.DataFrame([dict(project_id="T1", name="t", funder="f", implementers="i", hook_type="water_testing", location_precision="district", district_list="Baalbek",
                              cadaster_ids="", recency_ok="yes", attachability_score=3, verified="no", budget_usd=450_000.0),
                         dict(project_id="T2", name="t2", funder="f", implementers="i", hook_type="water_testing", location_precision="district", district_list="Zahle",
                              cadaster_ids="", recency_ok="yes", attachability_score=2, verified="no", budget_usd=np.nan)])


def test_budget_missing_gives_nan_percent_and_costs_scale_linearly():
    a = riders.build(_projects())
    assert np.isnan(a.loc[a.project_id == "T2", "rider_pct_of_budget_central"].iloc[0])        # never imputed
    assert a.loc[a.project_id == "T1", "rider_pct_of_budget_central"].iloc[0] == pytest.approx(a.loc[a.project_id == "T1", "rider_cost_central_usd"].iloc[0] / 450_000, rel=1e-3)
    b = riders.build(_projects(), params={"water_testing": {"n_nitrate": 80, "n_cr_water": 80, "n_screenings": 200}})
    assert b.rider_cost_central_usd.iloc[0] == pytest.approx(2 * a.rider_cost_central_usd.iloc[0], abs=2)      # doubling every count doubles the cost


def test_water_hygiene_lists_what_is_unpriced_and_direct_health_gets_no_rider():
    p = _projects()
    p.loc[0, "hook_type"] = "water_hygiene"
    r = riders.build(p)
    assert "microbial" in r.unpriced_items.iloc[0]
    q = _projects()
    q["hook_type"] = "direct_health"
    assert riders.build(q).empty


def test_rows_have_a_receiving_centre_and_a_cost_range():
    r = riders.build(_projects())
    assert r.nearest_phc.notna().all() and (r.phc_minutes > 0).all()
    assert (r.rider_cost_low_usd <= r.rider_cost_central_usd).all() and (r.rider_cost_central_usd <= r.rider_cost_high_usd).all()
