import os
import pathlib
import re

import pandas as pd
import pytest

from beqaa import io, m2_need_score as m2, narrative, theme_kpi

PROC = io.PROCESSED
ROOT = pathlib.Path(__file__).resolve().parents[1]
need = pytest.mark.skipif(not (PROC / "cadasters.csv").exists(), reason="run `make ingest` first")


@pytest.fixture(scope="module")
def auto():
    os.environ["BEQAA_DATA"] = "auto"
    yield
    os.environ["BEQAA_DATA"] = "mock"


@need
def test_baseline_uses_only_processed_real_data_or_is_missing(tmp_path, auto):
    miss = theme_kpi.local_control_share(2025, processed_dir=tmp_path)
    assert miss["status"] == "missing" and miss["value"] is None                     # no processed file -> never an invented number
    if (PROC / theme_kpi.LHF_FILE).exists():
        r = theme_kpi.local_control_share(2025)
        assert r["status"] == "real" and 0 <= r["value"] <= 1 and r["kind"] == "observed" and "cbpf" in r["source"].lower()


@need
def test_projection_monotone_baseline_flat_under_capacity_stall(auto):
    sc = m2.compute(m2.raw_indicators())
    base = [theme_kpi.local_control_share(y, "baseline", scored=sc)["value"] for y in range(2027, 2031)]
    stall = [theme_kpi.local_control_share(y, "S5_capacity_stall", scored=sc)["value"] for y in range(2027, 2031)]
    assert all(b2 >= b1 - 1e-9 for b1, b2 in zip(base, base[1:]))                 # non-decreasing under baseline settings
    assert max(stall) - min(stall) < 1e-9                                         # flat when capacity stalls
    assert base[-1] > stall[-1]
    r = theme_kpi.local_control_share(2030, "baseline", scored=sc)
    assert r["status"] == "assumption" and r["kind"] == "projection"             # mock capacity inputs: labelled, never 'real'


@need
def test_escalation_falls_back_and_table_columns(auto):
    sc = m2.compute(m2.raw_indicators())
    t = theme_kpi.kpi_table(scored=sc)
    assert set(theme_kpi.SCENARIOS) == set(t.scenario)
    e = t[t.scenario == "S1_escalation"].set_index("year").local_control_share
    assert e.loc[2028] < e.loc[2027]                                              # ladder falls back to an international fiduciary
    assert t.local_control_share.between(0, 1).all()


def test_narrative_templates_contain_no_digits_and_every_number_has_a_source():
    sents = [narrative.page1(0.47, 2026, 0.54, 0.134, 0.043), narrative.page2(["A", "B", "C"], "Baalbek", 0.8, 5), narrative.page3(0.33, 0.67, "baseline", 0.33),
             narrative.page4(1, 8, 0.8, "per_capita"), narrative.page5(4, 6, 3)]
    for s in sents:
        assert not narrative.template_has_digits(re.sub(r"\{[^}]*\}", "", s.template)), s.template        # numbers only via sourced placeholders
        assert all(src for src in s.sources.values()) and len(s.facts) >= 3
        assert not re.search(r"\{[^}]*\}", s.text)                                                                   # all placeholders filled
        for k in re.findall(r"\{(\w+)\}", s.template):
            assert k in s.facts, f"{k} has no sourced fact"


@need
@pytest.mark.parametrize("page", ["1_Money_now", "2_Where", "3_Who_holds", "5_Get_the_money", "6_Methods", "4_Resilience"])
def test_pages_run_headless_and_show_question_badges_and_answer(page, auto):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app" / "pages" / f"{page}.py"), default_timeout=600).run()
    assert not at.exception, [e.value for e in at.exception]
    if page != "6_Methods":
        txt = " ".join(c.value for c in at.caption)
        assert "Data on this page" in txt and "✅" in txt or "🟡" in txt or "🔴" in txt
        assert len(at.title) == 1 and not at.title[0].value.endswith("?")                       # short descriptive titles, not questions
        assert any(m.value.strip() for m in at.markdown)                            # the one-line answer


@need
def test_main_entry_opens_on_page_one(auto):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=300).run()
    assert not at.exception and at.title[0].value == "Funding today"
