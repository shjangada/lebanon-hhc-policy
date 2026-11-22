import pathlib

import pandas as pd
import pytest

from beqaa import io
from beqaa.ingest import pilot_data

PROC = io.PROCESSED
ROOT = pathlib.Path(__file__).resolve().parents[1]
need = pytest.mark.skipif(not (PROC / "esu_by_month.csv").exists(), reason="run `python -m beqaa.ingest pilot_data`")


@need
def test_esu_months_sum_to_published_total_and_cazas_sum_to_total():
    m = pd.read_csv(PROC / "esu_by_month.csv")
    tot = m[m.month == "TOTAL"].set_index(["year", "mohafaza_file", "disease"]).cases
    s = m[m.month != "TOTAL"].groupby(["year", "mohafaza_file", "disease"]).cases.sum()
    both = pd.concat([tot.rename("t"), s.rename("s")], axis=1).dropna()
    assert (both.t == both.s).all()
    d = pd.read_csv(PROC / "esu_by_district.csv")
    cz = d[d.geo_level == "caza"].groupby(["year", "mohafaza_file", "disease"]).cases.sum()
    c2 = pd.concat([tot.rename("t"), cz.rename("c")], axis=1).dropna()
    bad = c2[c2.t != c2.c]
    assert list(bad.index) == [(2022, "Bekaa", "Meningitis")]          # the one inconsistency in the source (68 vs 67), kept as published


@need
def test_hepatitis_a_corrected_figures():
    m = pd.read_csv(PROC / "esu_by_month.csv")
    h = m[(m.disease.str.contains("Hepatitis A")) & (m.month == "TOTAL") & (m.mohafaza_file == "Bekaa")].set_index("year").cases
    assert (h[2025], h[2026], h[2024], h[2023]) == (270, 67, 779, 690)      # NOT 256 for Jan-Sep this year; 2026 runs to August only
    lag = m[(m.year == 2026) & (m.month == "Aug") & (m.mohafaza_file == "Bekaa")]
    assert lag.reporting_lag.all()                                          # the last month is flagged partial


def test_read_loose_folds_extra_commas_into_the_last_column(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("a,b,notes\n1,2,fine\n3,4,has, a comma, inside\n5,6\n")
    d = pilot_data.read_loose(f)
    assert list(d.repaired) == [False, True, True] and d.notes.iloc[1] == "has, a comma, inside" and pd.isna(d.notes.iloc[2])


@need
def test_settlements_are_2016_and_matched_to_real_cadasters():
    s = pd.read_csv(PROC / "informal_settlements.csv", dtype={"cadaster_id": str})
    cad = pd.read_csv(PROC / "cadasters.csv", dtype={"cadaster_id": str})
    assert (s.data_year == 2016).all() and s.cadaster_id.dropna().isin(cad.cadaster_id).all() and s.cadaster_id.notna().mean() > 0.9


def test_evidence_table_has_all_pack_rows_and_the_corrections():
    ev = (ROOT / "docs" / "EVIDENCE_TABLE.md").read_text()
    assert all(f"| E{i:02d} |" in ev for i in range(1, 38))
    assert "Spanish" in ev and "Bekaa and Koura" in ev and "NOT significant" in ev and "TOTAL chromium" in ev
