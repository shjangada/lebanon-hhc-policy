"""Beqaa dashboard: the UN funding line. Put the money and the decisions where the damage is.

Five question-led pages plus Methods. Run: make app"""
import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
st.set_page_config(page_title="The UN funding line: Beqaa health", layout="wide")
import common  # noqa: E402

common.sidebar()
pages = [st.Page("pages/1_Money_now.py", title="1 · Money now", default=True), st.Page("pages/2_Where.py", title="2 · Where should it go"),
         st.Page("pages/3_Who_holds.py", title="3 · Who holds it"), st.Page("pages/4_Resilience.py", title="4 · Does it keep reaching people"),
         st.Page("pages/5_Get_the_money.py", title="5 · Where to get it"), st.Page("pages/6_Methods.py", title="Methods")]
st.navigation(pages).run()
