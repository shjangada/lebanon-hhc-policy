"""Shared helpers for the multipage app: data mode, caches, watermark chart wrapper, page header (question, one-line answer, data badges), sidebar (banner, women lens, data gaps)."""
from __future__ import annotations

import pathlib

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from beqaa import io, m1_access, m2_need_score as m2, narrative

ROOT = io.ROOT
MODE = io.overall_mode()
IS_MOCK = MODE != "REAL"
BADGE = io.BADGES


def version() -> float:
    """Cache key: modification times of code, params and data (stale cached frames are never reused after a branch switch or a re-ingest)."""
    files = list((ROOT / "src" / "beqaa").rglob("*.py")) + list((ROOT / "data" / "params").glob("*.yaml")) + list((ROOT / "data" / "mock").glob("*.csv")) \
        + list((ROOT / "data" / "processed").glob("*.csv")) + list((ROOT / "data" / "registry").glob("*.csv"))
    return max((f.stat().st_mtime_ns for f in files), default=0)


VER = version()


def wm(chart, w=640, h=320):
    """Red MOCK DATA watermark on a chart when any input is still mock."""
    chart = chart.properties(width=w, height=h)
    if not IS_MOCK:
        return chart
    t = alt.Chart(pd.DataFrame({"t": ["MOCK DATA"]})).mark_text(size=54, color="red", opacity=0.2, angle=335, fontWeight="bold").encode(text="t:N", x=alt.value(w / 2), y=alt.value(h / 2))
    return chart + t


def pretty(df: pd.DataFrame, **rename) -> pd.DataFrame:
    return df.rename(columns=rename)


@st.cache_data
def scored_cached(env_weight: float | None, d0: int, cr6: float | None, ver: float):
    raw = m2.raw_indicators(d0, "women_15_49", cr6_for_tier=cr6)
    if env_weight is None:
        sc = m2.compute(raw)
    else:
        w = {"clinical_demand": (1 - env_weight) / 3, "capacity_strain": (1 - env_weight) / 3, "vulnerability": (1 - env_weight) / 3, "environment": env_weight}
        sc = m2.compute(raw, weights=w)
    skipped = sc.attrs.get("skipped_indicators", [])
    sc = sc.copy()
    sc.attrs["skipped_indicators"] = skipped
    return sc


@st.cache_data
def panel_cached(d0: int, unknown_weight: float, ver: float):
    return m1_access.access_panel(d0, unknown_weight)


def badges(datasets: list[str]) -> str:
    return " · ".join(f"{d} {BADGE[io.dataset_badge(d)].split(' ')[0]}" for d in datasets)


def header(question: str, sentence: narrative.Sentence | str, datasets: list[str]) -> None:
    """Question as the title, one plain-language answer built from current outputs, and the real / partly real / mock badge of every dataset the page uses."""
    st.title(question)
    if isinstance(sentence, str):
        st.markdown(f"**{sentence}**")
    else:
        st.markdown(f"**{sentence.text}**")
        with st.expander("Where each number in this sentence comes from"):
            st.table(pd.DataFrame([{"number": sentence.facts[k][0], "source": sentence.sources[k]} for k in sentence.facts]))
    st.caption("Data on this page: " + badges(datasets) + "  (✅ real · 🟡 partly real · 🔴 mock)")
    if IS_MOCK:
        st.warning("Some inputs are still mock or assumed (charts carry a watermark). Do not cite model outputs as findings yet.", icon="⚠️")


def women_lens() -> bool:
    return bool(st.session_state.get("women_lens", False))


def sidebar() -> None:
    color = {"MOCK": "#c0392b", "PARTIAL": "#d68910", "REAL": "#1e8449"}[MODE]
    st.sidebar.markdown(f"<div style='background:{color};color:white;padding:8px;border-radius:6px;text-align:center'><b>DATA MODE: {MODE}</b>"
                        f"{' — real places and population, some inputs mock' if MODE == 'PARTIAL' else ''}</div>", unsafe_allow_html=True)
    st.sidebar.toggle("Women-led delivery channel (lens)", False, key="women_lens",
                      help="Page 2: safe-birth need metric. Page 3: women-led partners per rung. Page 5: women-led-eligible funds. Women are the delivery channel and the safe-birth outcome, not the most needy group overall.")
    with st.sidebar.expander("Data gaps (every page)"):
        ds = io.data_status()
        mp = pd.read_csv(ROOT / "data" / "registry" / "mock_provenance.csv")
        g = mp.merge(ds.assign(mock_file=ds.dataset + ".csv")[["mock_file", "status"]], on="mock_file", how="left")
        g = g[~g.status.fillna("").str.contains("real") | g.status.fillna("").str.contains("partly")]
        st.dataframe(g[["mock_file", "status", "obtainability", "how_to_get_it"]], hide_index=True, width="stretch")
        st.caption("'pilot_measured' and 'partner_request' have no public source: scenario inputs, flagged as assumptions. Details: docs/MANUAL_STEPS.md.")
