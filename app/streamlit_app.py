"""Beqaa dashboard: the UN funding line. Put the money and the decisions where the damage is.

Five question-led pages plus Methods. Run: make app"""
import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
st.set_page_config(page_title="The UN funding line: Beqaa health", layout="wide")
import importlib  # noqa: E402

import common  # noqa: E402

importlib.reload(common)        # app/common.py is a plain module: reload it on every rerun so edits are never stale (the beqaa package is reloaded by Streamlit's watcher)

common.sidebar()
pages = [st.Page("pages/1_Money_now.py", title="1 · Funding today", default=True), st.Page("pages/2_Where.py", title="2 · Priority areas"),
         st.Page("pages/3_Who_holds.py", title="3 · Control of the money"), st.Page("pages/4_Resilience.py", title="4 · Resilience"),
         st.Page("pages/5_Get_the_money.py", title="5 · Funding sources"), st.Page("pages/6_Methods.py", title="Methods")]
st.navigation(pages).run()
