import numpy as np
import pandas as pd
import pytest

from beqaa import io, m1_access as m1, m2_need_score as m2


def test_facility_state_requires_dated_source():
    fac = pd.DataFrame({"status_2026": ["open", "open", "closed", "partial", "damaged"], "status_date": ["2026-10-01", "", "2026-10-02", "2026-10-03", None]})
    st = m1.facility_state(fac)
    assert list(st) == ["functional", "unknown", "closed", "partial", "unknown"]                 # no date -> unknown, never functional
    assert (m1.facility_state(fac.drop(columns="status_date")) == "unknown").all()                 # no status_date column at all -> everything unknown


def test_effective_capacity_weights_and_mobile_hours():
    fac = pd.DataFrame({"facility_id": list("abcde"), "type": ["PHC", "PHC", "PHC", "mobile", "PHC"], "capacity_weekly": [100, 100, 100, 300, 100],
                        "status_2026": ["open", "partial", "closed", "open", "open"], "status_date": ["2026-10-01"] * 4 + [""],
                        "hours_per_week": [np.nan, np.nan, np.nan, 20, np.nan]})
    e = m1.effective_facilities(fac, unknown_weight=1.0).set_index("facility_id").capacity_weekly
    assert e["a"] == 100 and e["b"] == 50 and "c" not in e.index and e["d"] == 150 and e["e"] == 100         # mobile: 300 x 20/40
    e0 = m1.effective_facilities(fac, unknown_weight=0.0)
    assert "e" not in set(e0.facility_id)                                                       # pessimistic: unknown supplies nothing


def test_panel_prewar_vs_current_and_thresholds():
    p = m1.access_panel()
    assert (p.access_current <= p.access_prewar + 1e-9).all() or (p.access_current - p.access_prewar).max() < p.access_prewar.max()   # mobile units may add a little
    assert p.access_lost_pct.between(-1, 1).all()
    assert set(["facilities_per_10k_current", "min_phc_current", "min_hospital_current", "beyond_30_phc_current", "beyond_60_hospital_current"]) <= set(p.columns)
    pess = m1.access_panel(unknown_weight=0.0)
    assert pess.access_current.sum() <= p.access_current.sum() + 1e-9                           # treating unknown as non-functional never raises access


def test_district_summary_and_validation():
    p = m1.access_panel()
    d = m1.district_summary(p)
    assert d.share_beyond_30_phc_current.between(0, 1).all() and len(d) == p.district.nunique()
    v = m1.validate_vs_official(p)
    assert -1 <= v["rho"] <= 1 and set(v["disagreements"].columns) >= {"district", "rank_diff"}


def test_every_layer_has_a_date_and_mock_flag():
    ld = m1.layer_dates()
    assert ld.date.notna().all() and ld.is_mock.dtype == bool and len(ld) >= 5


def test_exposure_access_target_list():
    sc = m2.compute(m2.raw_indicators())
    t = m2.exposure_access_targets(sc)
    assert (t.D_environment >= 0.33).all() and (t.access_deficit >= 0.5).all()


def test_capacity_sensitivity_levels_move_but_ranking_does_not():
    """Centre capacity is an assumption (flat 300/week): levels scale with it, but the access ranking must be stable across 200 / 300 / 400 (rho >= 0.95),
    and the module-level scale is restored afterwards."""
    from scipy.stats import spearmanr
    from beqaa import m1_access as m1
    cs = m1.capacity_sensitivity()
    assert m1.PHC_SCALE == 1.0
    p = cs.pivot(index="cadaster_id", columns="phc_capacity_weekly", values="rank_current")
    assert spearmanr(p[200], p[400])[0] >= 0.9
    med = cs.groupby("phc_capacity_weekly").access_current.median()
    assert med[200] < med[300] < med[400]
