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
    monkeypatch.setattr(io, "DERIVED", d)
    monkeypatch.setenv("BEQAA_DATA", "derived")
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
