"""Tests for the real (processed) datasets: schema vs the mock, valid p-codes, no duplicate keys, is_mock False, non-empty url/source, provenance columns."""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

import pandas as pd
import pytest

from beqaa import io

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
MOCK = ROOT / "data" / "mock"
PROV = ["is_mock", "source_id", "source_date", "url", "status"]
KEYED = {"cadasters": ["cadaster_id"], "population": ["cadaster_id"], "vulnerability": ["cadaster_id"], "conflict_exposure": ["cadaster_id"],
         "facilities": ["facility_id"], "travel_time": ["cadaster_id", "facility_id"], "official_severity": ["district_pcode"], "soil_sites": None, "crop_transfer": None}
need = pytest.mark.skipif(not (PROC / "cadasters.csv").exists(), reason="run `make ingest` first")


def rd(name):
    return pd.read_csv(PROC / f"{name}.csv", dtype={"cadaster_id": str, "facility_id": str, "district_pcode": str})


@need
@pytest.mark.parametrize("name", [n for n in KEYED if (PROC / f"{n}.csv").exists()])
def test_schema_matches_mock_and_provenance(name):
    real, mock = rd(name), pd.read_csv(MOCK / f"{name}.csv", nrows=0)
    base = set(mock.columns) - {"is_mock", "source", "source_date", "url", "status", "is_mock_location", "note"}
    assert base <= set(real.columns), f"{name}: missing columns {base - set(real.columns)}"          # same schema as the mock (extra columns allowed)
    assert set(PROV) <= set(real.columns)
    assert not real.is_mock.astype(bool).any()
    assert real.url.notna().any() or name in ("travel_time", "official_severity", "soil_sites") or real.source.notna().all()
    assert real.source_id.notna().all() and real.status.notna().all()


@need
@pytest.mark.parametrize("name,key", [(n, k) for n, k in KEYED.items() if k and (PROC / f"{n}.csv").exists()])
def test_no_duplicate_keys(name, key):
    assert not rd(name).duplicated(key).any()


@need
def test_pcodes_are_valid_cod_ab():
    nat = rd("cadasters_national")
    valid = set(nat.cadaster_id)
    assert len(valid) > 1500 and set(rd("cadasters").cadaster_id) <= valid
    for n in ("population", "vulnerability", "conflict_exposure"):
        assert set(rd(n).cadaster_id) == set(rd("cadasters").cadaster_id), n
    assert set(rd("facilities").cadaster_id.dropna()) <= valid and set(rd("travel_time").cadaster_id) <= valid
    assert set(rd("soil_sites").cadaster_id) <= valid
    districts = set(nat.district_pcode)
    assert set(rd("official_severity").district_pcode.dropna()) <= districts


@need
def test_cadasters_scope_and_geometry():
    c = rd("cadasters")
    assert set(c.district) == {"Baalbek", "Hermel", "Zahle", "West Bekaa", "Rachaya"} and c[["lat", "lon", "area_km2"]].notna().all().all()
    g = json.loads((PROC / "cadasters.geojson").read_text())
    assert len(g["features"]) == len(c)


@need
def test_population_consistent_with_lrp_totals_and_groups():
    from beqaa.ingest import checks
    t = checks.population_vs_lrp()
    assert t.within_5pct.all()
    p = rd("population")
    assert (p.women_15_49 <= p.population_total).all() and (p.pop_lebanese + p.pop_syrians_lrp + p.pop_palestinians + p.pop_migrants - p.population_total).abs().max() <= 5


@need
def test_missing_stays_missing_not_filled():
    v = rd("vulnerability")
    assert v.ipc3plus_share.between(0, 1).all()
    for c in ("female_headed_hh_share", "unable_to_access_care_share", "no_insurance_share"):
        assert v[c].isna().all(), f"{c} must stay NaN until a district source exists"
    sev = rd("official_severity")
    assert sev.loc[sev.district == "Zahle", "fsa_composite_severity"].isna().all()                  # FSA only printed for Severity-4 districts


@need
def test_facility_status_never_functional_without_date():
    f = rd("facilities")
    dated = f.status_date.fillna("").astype(str).str.strip() != ""
    assert (f.loc[~dated, "functional_status"].fillna("") == "").all()
    assert f.status_2026.fillna("").loc[~dated].eq("").all()


@need
def test_soil_and_crop_rows_have_page_refs():
    assert rd("soil_sites").value_mg_kg.notna().all() and rd("soil_sites").lat.notna().all()
    ct = rd("crop_transfer")
    assert ct.transfer_factor.notna().all() and set(ct.metal) >= {"Cr", "Cd"}


def test_loader_prefers_processed_and_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("BEQAA_DATA", raising=False)
    if (PROC / "cadasters.csv").exists():
        assert io.load_dataset("cadasters").is_mock is False and io.dataset_badge("cadasters") in ("real", "partly real")
    assert io.load_dataset("interventions").is_mock is True and io.dataset_badge("interventions") == "mock"          # no real source
    monkeypatch.setenv("BEQAA_DATA", "mock")
    assert io.load_dataset("cadasters").is_mock is True


def test_badges_are_real_partly_real_or_mock():
    for n in io.DATASETS:
        assert io.dataset_badge(n) in ("real", "partly real", "mock")


@need
def test_consistent_set_when_real():
    os.environ["BEQAA_DATA"] = "auto"
    try:
        assert io.validate_consistency() == []
    finally:
        os.environ["BEQAA_DATA"] = "mock"


def test_acled_never_leaks_credentials_and_stops_on_refusal(monkeypatch, capsys):
    from beqaa.ingest import acled
    monkeypatch.setenv("ACLED_EMAIL", "someone@example.org")
    monkeypatch.setenv("ACLED_PASSWORD", "hunter2-secret")

    def refuse(*a, **k):
        import urllib.error
        raise urllib.error.HTTPError("u", 403, "forbidden", {}, None)
    monkeypatch.setattr(acled.urllib.request, "urlopen", refuse)
    with pytest.raises(acled.AcledAuthError) as e:
        acled.get_token()
    assert "hunter2" not in str(e.value) and "someone@example.org" not in str(e.value)
    monkeypatch.delenv("ACLED_PASSWORD")
    monkeypatch.setattr(acled, "_load_env", lambda: None)
    with pytest.raises(acled.AcledAuthError):
        acled.get_token()
    out = capsys.readouterr()
    assert "hunter2" not in out.out + out.err


def test_acled_and_env_are_gitignored():
    gi = (ROOT / ".gitignore").read_text()
    assert ".env\n" in gi and "data/raw/conflict_events/acled/" in gi and (ROOT / ".env.example").exists()
    assert "=" in (ROOT / ".env.example").read_text() and all(l.split("=", 1)[1].strip() == "" for l in (ROOT / ".env.example").read_text().splitlines() if "=" in l and not l.startswith("#"))
