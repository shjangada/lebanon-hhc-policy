import os
import pathlib

import pandas as pd
import pytest

from beqaa import io

ROOT = pathlib.Path(__file__).resolve().parents[1]
needs_raw = pytest.mark.skipif(not (ROOT / "data/raw/admin_boundaries/lbn_admin_boundaries.geojson.zip").exists()
                               or not (ROOT / "data/raw/population/worldpop").exists(), reason="raw downloads absent (python scripts/fetch_sources.py)")


def test_default_mode_is_consistent_mock():
    assert io.validate_consistency() == []


def test_mixed_real_and_mock_is_detected(monkeypatch, tmp_path):
    d = tmp_path
    pd.DataFrame({"cadaster_id": ["X1"], "cadaster_name": ["x"], "district": ["a"], "lat": [1.0], "lon": [1.0]}).to_csv(d / "cadasters.csv", index=False)
    monkeypatch.setattr(io, "PROCESSED", d)
    monkeypatch.delenv("BEQAA_DATA", raising=False)               # auto mode: processed first, mock otherwise
    assert io.validate_consistency()                      # real cadasters + mock population/vulnerability: flagged


@needs_raw
def test_cadasters_population_converter(tmp_path, monkeypatch):
    from beqaa.ingest import cadasters_population as cp
    cad = cp.build_cadasters()
    assert set(cad.district) == {"Baalbek", "Hermel", "Zahle", "West Bekaa", "Rachaya"} and cad.cadaster_id.is_unique and not (cad.cadaster_name == "Litige").any()
    pop = cp.build_population(cad)
    assert pop.merge(cad[["cadaster_id"]]).shape[0] == len(cad)
    host = pop.population_total - pop.displaced - pop.displaced_syrians_registered - pop.unregistered_workers_est
    assert (host >= 0).all() and (pop.women_15_49 <= pop.population_total).all()
    lrp = cp._lrp_district().set_index("lrp_district")
    inv = {v: k for k, v in cp.DISTRICT_LABEL.items()}
    by = pop.merge(cad[["cadaster_id", "district"]]).groupby("district").population_total.sum()
    for dist, tot in by.items():                          # rescaled to the LRP 2026 district totals (within rounding)
        assert tot == pytest.approx(lrp.loc[inv[dist], "total"], rel=1e-3)
    assert (pop.status == "assumption").all() and not pop.is_mock.any()


@needs_raw
def test_facilities_converter_and_coverage():
    from beqaa.ingest import cadasters_population as cp, facilities as fc
    cad = cp.build_cadasters()
    fac = fc.build_facilities(cad)
    assert len(fac) > 0 and fac.facility_id.is_unique and set(fac.type) <= {"PHC", "hospital_hub"} and fac.cadaster_id.isin(cad.cadaster_id).all()
    assert (fac.status == "assumption").all()
    cov = fc.coverage(fac, cad)
    assert cov.iloc[-1].phc_in_mophnetwork_lrp2026 == 61 and 0.9 <= cov.iloc[-1].coverage <= 1.2      # MoPH list (62 network PHCCs + 6 locator-only, minus 3 without coordinates) vs LRP's 61
    tt = fc.build_travel_time(cad.head(3), fac.head(4))
    assert len(tt) == 12 and (tt.minutes >= 0).all()
