"""Beqaa dashboard: the UN funding line. Put the money and the decisions where the damage is.

One scrolling Dashboard page (six sections stacked in order) plus a separate Methods page. Run: make app"""
import importlib
import pathlib
import runpy
import sys

import streamlit as st

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))      # the beqaa package lives in src/ and is not pip-installed on Streamlit Cloud
st.set_page_config(page_title="The UN funding line: Beqaa health", layout="wide")



@st.cache_resource
def _src_stamp() -> dict:
    return {"t": 0.0}


def _purge_stale_modules() -> None:
    """A long-running server (Streamlit Cloud after a redeploy, or local) keeps old `beqaa.*` modules in memory, which raises AttributeError for functions added later.
    When any file under src/beqaa changed since the last run, drop every cached `beqaa` module so the imports below load the current code."""
    newest = max(f.stat().st_mtime for f in (HERE.parent / "src" / "beqaa").rglob("*.py"))
    stamp = _src_stamp()
    if newest > stamp["t"]:
        for name in [m for m in sys.modules if m == "beqaa" or m.startswith("beqaa.")]:
            del sys.modules[name]
        stamp["t"] = newest


_purge_stale_modules()
import common  # noqa: E402

importlib.reload(common)        # app/common.py is a plain module: reload it on every rerun so edits are never stale (the beqaa package is reloaded by Streamlit's watcher)

SECTIONS = [("0 · Why Beqaa", "Why Beqaa", "why", "pages/0_Why_Beqaa.py"),
            ("1 · Funding today", "Funding today", "funding", "pages/1_Money_now.py"),
            ("2 · Priority areas", "Priority areas", "areas", "pages/2_Where.py"),
            ("3 · Control of the money", "Control of the money", "control", "pages/3_Who_holds.py"),
            ("4 · Resilience", "Resilience", "resilience", "pages/4_Resilience.py"),
            ("5 · Funding sources", "Funding sources", "sources", "pages/5_Get_the_money.py")]


def dashboard():
    st.title("The UN funding line: Beqaa health")
    st.caption("Put the money and the decisions where the damage is. One page, six sections: scroll, or jump:")
    st.markdown(" · ".join(f"[{label}](#{anchor})" for label, _, anchor, _ in SECTIONS))
    common.ONE_PAGE = True
    common.ANCHORS = {title: anchor for _, title, anchor, _ in SECTIONS}
    try:
        for _, _, _, path in SECTIONS:
            common.SCENARIO_ON = path.endswith("4_Resilience.py")      # section 4 compares options on assumed inputs
            runpy.run_path(str(HERE / path), run_name="__main__")
    finally:
        common.ONE_PAGE = False
        common.SCENARIO_ON = False


common.sidebar()
st.navigation([st.Page(dashboard, title="Dashboard", default=True, url_path="dashboard"),
               st.Page("pages/6_Methods.py", title="Methods")]).run()
