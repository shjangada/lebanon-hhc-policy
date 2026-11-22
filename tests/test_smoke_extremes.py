"""Load the interactive sections with every slider at its minimum and at its maximum (real data): no crash, no empty page."""
import pathlib

import pytest

from beqaa import io

ROOT = pathlib.Path(__file__).resolve().parents[1]
need = pytest.mark.skipif(not (io.PROCESSED / "esu_by_district.csv").exists(), reason="run `make ingest`")


@need
@pytest.mark.parametrize("page", ["3b_Pilot", "3_Who_holds", "2_Where"])
@pytest.mark.parametrize("which", ["min", "max"])
def test_sliders_at_extremes_do_not_crash(page, which, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("BEQAA_DATA", "auto")
    at = AppTest.from_file(str(ROOT / "app" / "pages" / f"{page}.py"), default_timeout=900).run()
    assert not at.exception and len(at.subheader) >= 1
    for sl in at.slider:
        sl.set_value(sl.min if which == "min" else sl.max)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.subheader) >= 1                                              # the page still renders its sections


@need
def test_ui_wording_uses_displaced_syrians_not_refugees():
    """Lebanese-facing UI copy says 'displaced Syrians' (LRP term), not 'refugees' (source names such as 'UNHCR refugee scheme' in data tables are exempt)."""
    import re
    bad = []
    for f in sorted((ROOT / "app").rglob("*.py")):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if re.search(r"\brefugees?\b", line, re.I) and not re.search(r"(UNHCR|scheme|Refugee outreach|refugee (women|settlement)|Syrian refugee|refugees at|registered displaced|HAUS|#|\"\"\")", line, re.I):
                bad.append(f"{f.name}:{i}: {line.strip()[:110]}")
    assert not bad, bad


@need
def test_secondary_charts_live_in_the_appendix_tab_not_the_main_sections(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("BEQAA_DATA", "auto")
    moved = {"Health access: centres per 10,000": "0_Why_Beqaa", "Flash Appeal 2026: funded vs required, by sector": "1_Money_now", "Where access was lost, and where it overlaps with exposure": "2_Where",
             "Who decides how it is spent: community, top-down or per capita": "3_Who_holds", "Which allocation policy: regret across scenarios": "4_Resilience"}
    app = AppTest.from_file(str(ROOT / "app" / "pages" / "7_Appendix_charts.py"), default_timeout=900).run()
    assert not app.exception
    titles = [s.value for s in app.subheader]
    for t in ("Health access: centres per 10,000", "Flash Appeal 2026: funded vs required, by sector", "Where access was lost, and where it overlaps with exposure",
              "Who decides how it is spent: community, top-down or per capita", "Stepped rollout"):
        assert t in titles, t
    for t, page in moved.items():
        src = (ROOT / "app" / "pages" / f"{page}.py").read_text()
        if t != "Which allocation policy: regret across scenarios":
            assert f'st.subheader("{t}")' not in src, (t, page)
    assert "Appendix charts" in (ROOT / "app" / "streamlit_app.py").read_text()
