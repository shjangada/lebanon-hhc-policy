"""Page 5: Where can we get the money? (the action step)"""
import pathlib
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import chat_llm, funding_finder as ff, m2_need_score as m2, m4_exposure, narrative, research_gaps  # noqa: E402

f = ff.annotate(ff.load_funding())
a, b, c = st.columns(3)
next_round = a.toggle("Show closed annual calls as 'expected next round'", False, key="p5_next")
show_closed = b.toggle("Show closed / closed-to-new rows", False, key="p5_closed")
rank_mode = c.radio("Rank by", ["Community decides (low donor involvement first)", "Priority match (sector, open now, local eligibility)"], key="p5_rank", label_visibility="collapsed")
pool_f = ff.filter_funding(f, None, False, True, show_next_round=next_round, show_closed=show_closed, show_closed_to_new=show_closed)
res = ff.rank(pool_f, ["health", "maternal"])
if rank_mode.startswith("Community"):
    res = ff.rank_involvement(res)
women = C.women_lens()
if women:
    txt = (res.name.fillna("") + " " + res.sectors.fillna("") + " " + res.notes.fillna("")).str.lower()
    res = res[txt.str.contains("women|feminist|girls|gender")]
pooled = res[res.can_pool]
direct = res[res.channel.isin(ff.DIRECT_LOCAL_CHANNELS) & ~res.can_pool]
sent = narrative.page5(len(pooled), len(direct), int(res[(res.name.fillna("") + res.sectors.fillna("") + res.notes.fillna("")).str.lower().str.contains("women|feminist")].shape[0]))
C.header("Funding sources", sent, ["funding_flows"], purpose="Real funds and partners that could pay for this, split by whether they can be pooled or go straight to local groups.")
st.caption("Only rows of data/registry/funding_registry.csv (never invented), each with its source URL and verified date. Closed rows are hidden by default. "
           + ("Women lens ON: only funds open to women-led organisations." if women else "Turn on the women lens in the sidebar to filter to women-led-eligible funds."))
cols = ["name", "funder", "channel", "availability", "involvement_level", "fits_escrow", "url", "verified_on"]
ren = dict(name="Fund", funder="Funder", channel="Channel", availability="Status", involvement_level="Donor involvement", fits_escrow="Fits escrow?", url="Source", verified_on="Verified")
cfg = {"Source": st.column_config.LinkColumn("Source", display_text="open")}
l, r = st.columns(2)
with l:
    st.subheader("Can be pooled into the escrow")
    st.caption("Government and pooled-fund money that can sit in a ring-fenced window inside an existing fund (LHF/LFF).")
    st.dataframe(C.pretty(pooled[cols].head(12), **ren), hide_index=True, width="stretch", column_config=cfg)
with r:
    st.subheader("Goes straight to local groups")
    st.caption("Grants to local and women-led organisations that complement the pool; the community decides use.")
    st.dataframe(C.pretty(direct[cols].head(12), **ren), hide_index=True, width="stretch", column_config=cfg)
if pooled.empty and direct.empty:
    st.info("No rows match the current filters. Nothing is invented: add a verified row to the registry.")

st.subheader("Fund the evidence: weak-evidence candidates linked to registry rows")
scored = C.scored_cached(None, 30, 0.1, C.VER)
try:
    tor = m4_exposure.tornado()
    gaps = research_gaps.intervention_gaps(tor)
    st.dataframe(gaps, hide_index=True, width="stretch")
    st.caption("Where evidence is weakest, the matching funding rows (by sector keywords) are listed in the last columns; 'No verified entry' means the registry has none. Implementation-research funding turns these gaps into proposals.")
except Exception as e:                                   # keep the page usable if the research-gap module changes
    st.info(f"Research-gap table unavailable: {e}")
with st.expander("Funding-flow data sources (where real allocation data comes from)"):
    st.dataframe(ff.load_datasets(), hide_index=True, width="stretch", column_config={"url": st.column_config.LinkColumn("url", display_text="open")})
    st.caption("data/registry/funding_datasets.csv: datasets, not grants. CBPF / FTS are already processed (`make ingest`) and drive Page 1.")

st.subheader("Ask the funding assistant")
client = chat_llm.get_client()
st.caption(("LLM assistant (" + chat_llm.MODEL + ") loops through the funding, organisation and source registries; every claim cites a registry id and URL. It never uses outside knowledge for grants.")
           if client else "No ANTHROPIC_API_KEY found (set it in .env): showing retrieval-only answers from the registries.")
if "chat_hist" not in st.session_state:
    st.session_state.chat_hist = []
for m_ in st.session_state.chat_hist:
    with st.chat_message(m_["role"]):
        st.markdown(m_["content"])
if q_ := st.chat_input("e.g. Which funders could let local communities decide how maternal-health money is spent?"):
    st.session_state.chat_hist.append({"role": "user", "content": q_})
    with st.chat_message("user"):
        st.markdown(q_)
    with st.chat_message("assistant"):
        with st.spinner("Searching the registries…"):
            top3 = ", ".join(scored.nsmallest(3, "rank").cadaster_name)
            r_ = chat_llm.ask(q_, history=st.session_state.chat_hist[:-1], client=client, context=f"priority cadasters: {top3}; theme: community-decided, locally administered funding")
        st.markdown(r_["answer"])
        st.caption(f"Mode: {r_['mode']}" + (f" · cited: {', '.join(r_['citations'])}" if r_["citations"] else ""))
        if r_["trace"]:
            with st.expander("Registry lookups"):
                st.json(r_["trace"])
    st.session_state.chat_hist.append({"role": "assistant", "content": r_["answer"]})
