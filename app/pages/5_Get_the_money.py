"""Page 5: Where can we get the money? (the action step)"""
import pathlib
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import chat_llm, eligibility, escrow, funding_finder as ff, m2_need_score as m2, m4_exposure, narrative, research_gaps  # noqa: E402

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
ver = eligibility.registry_last_verified()
st.info(f"**Registry last verified on {ver['last_verified']}** (oldest row {ver['oldest_verified']}). {ver['rows']} funds, {ver['to_verify_rows']} still `to_verify`, {ver['stale_rows']} older than six months. "
        "Nothing here is invented: every row is a registry row with its source URL. Registry owner (proposal, needed for the 2030 feasibility test): the Lebanon Humanitarian Fund's localisation staff, "
        "a Lebanese NGO network or the municipal union, re-checking every row older than six months. Real users need this in **Arabic**; the prototype is English-only.")

st.subheader("Funding and eligibility assistant: which funds can our organisation apply to?")
a1, a2, a3, a4 = st.columns(4)
org_type = a1.selectbox("Organisation type", eligibility.ORG_TYPES, key="p5_org")
women_led = a2.toggle("Women-led", C.women_lens(), key="p5_wl")
district = a3.selectbox("Based in", ["Baalbek", "Hermel", "Zahle", "West Bekaa", "Rachaya"], key="p5_dist")
registered = a4.toggle("Registered in Lebanon", True, key="p5_reg")
prof = eligibility.Profile(org_type=org_type, women_led=women_led, district=district, registered_in_lebanon=registered)
el = eligibility.eligible_funds(prof, show_next_round=True)
if not registered:
    st.warning("Most registry rows need a legally registered organisation or a registered fiscal host. Unregistered groups usually have to apply through a registered partner: the registry does not list fiscal-host schemes yet.")
st.dataframe(C.pretty(el[["name", "eligibility", "why", "status", "involvement_level", "how_to_access", "url", "verified_on"]], name="Fund", eligibility="Eligibility", why="Why", status="Status",
                      involvement_level="Donor involvement", how_to_access="How to apply (registry)", url="Source", verified_on="Verified"), hide_index=True, width="stretch",
             column_config={"Source": st.column_config.LinkColumn("Source", display_text="open")})
st.caption(f"{len(el)} funds for this profile ({int((el.eligibility == 'eligible').sum())} eligible per the registry, the rest conditional or to be checked). Closed annual calls appear as 'expected next round'. "
           "Eligibility is read from the registry (`local_org_eligible`, status, channel; women-only funds by keyword), so 'check eligibility' means the registry has not verified it.")

st.subheader("What do we need to move up a rung?")
b1, b2, b3, b4 = st.columns(4)
cap = b1.slider("Capacity index (0-1)", 0.0, 0.8, 0.30, 0.01, key="p5_cap", help="Self-assessed administrative capacity. The national anchor is 0.299 (World Bank WGI Government Effectiveness 29.9/100, SC01).")
tr = b2.toggle("Publishes quarterly spend + third-party spot check", False, key="p5_tr")
rc = b3.slider("Referral completion", 0.0, 1.0, 0.30, 0.05, key="p5_rc")
pf = b4.slider("Budgeted posts filled", 0.0, 1.0, 0.50, 0.05, key="p5_pf")
gp = eligibility.threshold_gaps(cap, tr, rc, pf)
m1_, m2_ = st.columns(2)
m1_.metric("Current rung", gp["current_rung"])
m2_.metric("Next rung", gp["next_rung"])
st.dataframe(C.pretty(gp["table"], requirement="Requirement", yours="Yours", required="Required", met="Met", gap="Gap", what_it_unlocks="Unlocks"), hide_index=True, width="stretch")
st.caption("Thresholds are the escrow's (data/params/escrow_params.yaml): process indicators, pre-agreed and published, all assumptions except the SC01 anchor. "
           + ("All capacity-tranche thresholds are met." if gp["all_tranche_thresholds_met"] else f"{len(gp['gaps'])} requirement(s) not yet met: these are the concrete steps to close."))

st.subheader("Donor view: high-need cadasters and whether a funded partner is known")
sc0 = C.scored_cached(None, 30, 0.1, C.VER)
st.dataframe(C.pretty(eligibility.uncovered_priority_cadasters(sc0).round(2), cadaster_name="Cadaster", district="District", need_score="Need score", access_deficit="Access deficit",
                      D_environment="Exposure", open_facilities_within_30_min="Open facilities within 30 min", partner_presence="Funded partner present?"), hide_index=True, width="stretch")
st.caption("Funded-partner locations are not public: FTS and the Lebanon Humanitarian Fund report funding for Lebanon as a whole, with no district or cadaster. The column is 'unknown' until the Health Sector 4W/5W is obtained (docs/MANUAL_STEPS.md). "
           "Never guessed.")

st.subheader("All registry funds: pooled vs straight to local groups")
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

st.subheader("Ask the registry (optional chat)")
use_llm = st.checkbox("Phrase answers with Claude (optional; needs ANTHROPIC_API_KEY)", False, key="p5_llm")
client = chat_llm.get_client() if use_llm else None
st.caption(("Claude loops through the funding, organisation and source registries and only phrases what it finds; every claim cites a registry id and URL; invented ids are flagged. " + chat_llm.MODEL)
           if client else "Retrieval-only (default): answers are rows of the registries with their source URLs. This chat is an optional layer on top of the eligibility checker above.")
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
