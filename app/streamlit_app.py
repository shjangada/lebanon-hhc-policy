"""Beqaa dashboard: the UN funding line. Put the money and the decisions where the damage is.

One scrolling Dashboard page (five sections stacked in order) plus a separate Methods page. Run: make app"""
import importlib
import pathlib
import runpy
import sys

import streamlit as st

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
st.set_page_config(page_title="The UN funding line: Beqaa health", layout="wide")

import common  # noqa: E402

importlib.reload(common)        # app/common.py is a plain module: reload it on every rerun so edits are never stale (the beqaa package is reloaded by Streamlit's watcher)

SECTIONS = [("1 · Funding today", "Funding today", "funding", "pages/1_Money_now.py"),
            ("2 · Priority areas", "Priority areas", "areas", "pages/2_Where.py"),
            ("3 · Control of the money", "Control of the money", "control", "pages/3_Who_holds.py"),
            ("4 · Resilience", "Resilience", "resilience", "pages/4_Resilience.py"),
            ("5 · Funding sources", "Funding sources", "sources", "pages/5_Get_the_money.py")]


def dashboard():
    st.title("The UN funding line: Beqaa health")
    st.caption("Put the money and the decisions where the damage is. One page, five sections: scroll, or jump:")
    st.markdown(" · ".join(f"[{label}](#{anchor})" for label, _, anchor, _ in SECTIONS))
    common.ONE_PAGE = True
    common.ANCHORS = {title: anchor for _, title, anchor, _ in SECTIONS}
    try:
        for _, _, _, path in SECTIONS:
            runpy.run_path(str(HERE / path), run_name="__main__")
    finally:
        common.ONE_PAGE = False


common.sidebar()
st.navigation([st.Page(dashboard, title="Dashboard", default=True, url_path="dashboard"),
               st.Page("pages/6_Methods.py", title="Methods")]).run()
