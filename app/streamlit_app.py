"""Beqaa Health Prioritization dashboard. Run: make app"""
import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from beqaa import (allocation, assumptions, chat, chat_llm, equity, escrow, funding_finder as ff, io, m1_access, m2_need_score as m2,
                   m4_exposure, m5_options)

st.set_page_config(page_title="Beqaa Health Prioritization", layout="wide")
MODE = io.overall_mode()
IS_MOCK = MODE != "REAL"
CFG = m2.load_spec()


def wm(chart, w=640, h=320):
    """Red MOCK DATA watermark on every chart when data is mock."""
    chart = chart.properties(width=w, height=h)
    if not IS_MOCK:
        return chart
    t = alt.Chart(pd.DataFrame({"t": ["MOCK DATA"]})).mark_text(size=54, color="red", opacity=0.22, angle=335, fontWeight="bold").encode(
        text="t:N", x=alt.value(w / 2), y=alt.value(h / 2))
    return chart + t


@st.cache_data
def raw_ind(d0, demand):
    return m2.raw_indicators(d0, demand)


@st.cache_data
def sites_df():
    return m4_exposure.screen_sites()


@st.cache_data
def funding():
    return ff.annotate(ff.load_funding())


# ---------------- sidebar: global controls ----------------
st.sidebar.title("Beqaa health priorities")
color = {"MOCK": "#c0392b", "PARTIAL": "#d68910", "REAL": "#1e8449"}[MODE]
st.sidebar.markdown(f"<div style='background:{color};color:white;padding:8px;border-radius:6px;text-align:center'>"
                    f"<b>DATA MODE: {MODE}</b>{' — synthetic cadasters, placeholder costs' if IS_MOCK else ''}</div>", unsafe_allow_html=True)
budget_label = st.sidebar.selectbox("Budget tier", list(m5_options.BUDGET_TIERS) + ["Custom"], 1)
budget = st.sidebar.number_input("Custom budget (USD)", 100, 10_000_000, 50_000, 1000) if budget_label == "Custom" else m5_options.BUDGET_TIERS[budget_label]
layer = st.sidebar.selectbox("Map layer", ["need", "providership", "referral", "ngo_dependency", "environment"])
d0 = st.sidebar.selectbox("Catchment d0 (min)", [15, 30, 60], 1)
with st.sidebar.expander("Need Score settings"):
    w = {d: st.slider(d.replace("_", " "), 0.0, 1.0, float(CFG["domain_weights"][d]), 0.05) for d in m2.DOMAINS}
    env_on = st.toggle("Environment domain", True)
    unreg = st.toggle("Include unregistered workers", True)
    geo = st.toggle("Non-compensatory (geometric mean)", False)
    top_k = st.slider("Top-k cadasters (priority set)", 3, 15, CFG["top_k"])
with st.sidebar.expander("Demand weighting for access"):
    demand = st.selectbox("Demand", ["women_15_49", "weighted_women_15_49", "pregnant_est", "population_total"])
    dw = {"displaced_lebanese": st.slider("Displaced Lebanese ×", 0.5, 3.0, 1.0, 0.1),
          "registered_displaced_syrians": st.slider("Registered displaced Syrians ×", 0.5, 3.0, 1.0, 0.1),
          "unregistered_workers_est": st.slider("Unregistered workers ×", 0.5, 3.0, 1.0, 0.1)}
st.sidebar.caption("Wording: land- and community-based framing; 'displaced Syrians'.")

spec = {**CFG, "top_k": top_k}
raw = raw_ind(d0, "women_15_49" if demand == "weighted_women_15_49" else demand)
if not unreg:
    raw = raw.assign(unregistered_workers_share=0.0)
on = [d for d in m2.DOMAINS if d != "environment" or env_on]
scored = m2.compute(raw, w, spec, geo, on)
rob = m2.robustness(raw, spec=spec, geometric=geo, domains_on=on)
acc = m1_access.access_by_cadaster(d0, demand, "all", "gaussian", dw if demand == "weighted_women_15_49" else None)
ga = m1_access.group_access(acc)

# ---------------- page ----------------
st.title("Where should Beqaa primary-care money go first, and who should run it?")
st.markdown("**Proposal:** an adaptive funding switch. Money follows measured need; control moves from foreign NGOs to Lebanese entities "
            "(municipalities → MoPH) as measured capacity improves. *Traditional:* funds follow appeals and agency footprint, referrals are untracked, "
            "unregistered workers are invisible.")
if IS_MOCK:
    st.error("MOCK DATA: synthetic cadasters and placeholder costs. Do not cite these numbers. Real files in data/raw/ replace mock files automatically.")

gov, _ = io.load_dataset("governance_capacity")
stf, _ = io.load_dataset("staffing_referrals")
g_ = gov[(~gov.projected.astype(bool))]
g_ = g_[g_.year == g_.year.max()]
gg = ga.set_index("group")
c = st.columns(6)
c[0].metric("Funds managed locally", f"{g_.share_funds_managed_locally.mean():.0%}")
c[1].metric("Referral completion", f"{stf.referral_completed_month.sum() / stf.referral_sent_month.sum():.0%}")
c[2].metric("Posts filled", f"{stf.posts_filled.sum() / stf.posts_budgeted.sum():.0%}")
c[3].metric("Access lost to 2026 closures", f"{acc.access_lost.sum() / acc.access_baseline.sum():.0%}")
c[4].metric("Worst-group access vs host", f"{gg.ratio_to_host.drop('women_15_49').min():.2f}×")
c[5].metric("Soil finding → action", "n/a", help="Baseline to be set in the pilot")
st.caption("2030 indicators, current baseline. Clinics reporting a Need Score: 0% today (pilot target).")

# 1. Where
st.header("1 · Where to act and whose access is most constrained")
left, right = st.columns([3, 2])
col = f"stress_{layer}"
v = scored[col].fillna(0)
scored["_r"] = (255 * v).astype(int); scored["_g"] = (200 * (1 - v)).astype(int); scored["_rad"] = scored.population_total.pow(0.5) * 25
layers = [pdk.Layer("ScatterplotLayer", scored, get_position=["lon", "lat"], get_radius="_rad", get_fill_color=["_r", "_g", 40, 190], pickable=True)]
ov = left.columns(2)
if ov[0].checkbox("Facilities (green open / red closed)"):
    fac, _ = io.load_dataset("facilities")
    fac = fac.assign(_c=fac.status_2026.map(lambda s_: [30, 140, 60, 230] if s_ == "open" else [200, 30, 30, 230]))
    layers.append(pdk.Layer("ScatterplotLayer", fac, get_position=["lon", "lat"], get_radius=1200, get_fill_color="_c"))
if ov[1].checkbox("Soil sites (by tier)"):
    s_ = sites_df().dropna(subset=["lat"]).assign(_c=lambda d: d.tier.map({0: [120, 120, 120, 220], 1: [240, 190, 0, 230], 2: [130, 0, 160, 240]}))
    layers.append(pdk.Layer("ScatterplotLayer", s_, get_position=["lon", "lat"], get_radius=1800, get_fill_color="_c"))
if IS_MOCK:
    layers.append(pdk.Layer("TextLayer", pd.DataFrame({"lat": [scored.lat.mean()], "lon": [scored.lon.mean()], "t": ["MOCK DATA"]}),
                            get_position=["lon", "lat"], get_text="t", get_size=60, get_color=[220, 0, 0, 120]))
left.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=scored.lat.mean(), longitude=scored.lon.mean(), zoom=7.6),
                           tooltip={"text": "{cadaster_name}\nNeed {need_score}"}))
left.caption(f"Colour = {layer} stress (0 green → 1 red); size = population.")
top = scored.merge(rob[["cadaster_id", "p_top_tier", "rank_p05", "rank_p95"]], on="cadaster_id").sort_values("rank").head(10)
right.markdown("**Top 10 cadasters** (p_top_tier = share of random weightings placing it in the top-k)")
right.dataframe(top[["cadaster_name", "need_score", "p_top_tier", "rank_p05", "rank_p95"]].round(2), hide_index=True)
stable = rob[rob.p_top_tier >= 0.9].cadaster_name.tolist()
right.info(f"Top-{top_k} in ≥90% of weightings: {', '.join(stable) if stable else 'none: ranking is weight-sensitive'}")
a1, a2 = st.columns(2)
gl = ga.assign(group=ga.group.map(equity.GROUP_LABELS))
a1.altair_chart(wm(alt.Chart(gl).mark_bar().encode(y=alt.Y("group:N", sort=None, title=None), x=alt.X("ratio_to_host:Q", title="access vs host Lebanese (1 = parity)")), 420, 220))
a1.caption("Spatial access by group. Legal and financial barriers show up in the care cascade below.")
a = acc.sort_values("access_lost", ascending=False).head(10)
long = a.melt("cadaster_name", ["access_baseline", "access_current"], "scenario", "access")
long["access"] *= 1000
a2.altair_chart(wm(alt.Chart(long).mark_bar().encode(y=alt.Y("cadaster_name:N", sort=None, title=None), x=alt.X("access:Q", title="capacity per 1,000"), color="scenario:N", yOffset="scenario:N"), 420, 260))
a2.caption("Most affected cadasters: pre-2026 vs current.")
with st.expander("Official-severity comparison, tiers and triggers, mobile-unit siting"):
    comp, hidden = m2.compare_official(scored)
    st.dataframe(comp.round(3), hide_index=True, width="stretch")
    if len(hidden):
        st.warning("Top-10 cadasters inside districts the official map rates below median:")
        st.dataframe(hidden.round(3), hide_index=True)
    st.table(m2.triggers())
    k = st.slider("Mobile units k", 1, 6, 3)
    st.dataframe(m1_access.mobile_unit_sites(k, d0).drop(columns=["is_mock"]), hide_index=True)

# 2. What to fund
st.header(f"2 · What {budget_label if budget_label != 'Custom' else f'${budget:,.0f}'} buys")
iv, _ = io.load_dataset("interventions")
pick = st.multiselect("Compare 2–3 interventions", list(iv.intervention_id), default=["transport_vouchers", "chw_women_orgs"], max_selections=3)
if pick:
    ev = m5_options.evaluate(pick, budget)
    st.dataframe(ev[["label", "units_median", "women_reached_median", "extra_pathways_median", "extra_pathways_p05", "extra_pathways_p95",
                     "cost_per_pathway_median", "equity_gap_after"]].round(2), hide_index=True, width="stretch")
    st.markdown("**Collateral-damage check**")
    st.dataframe(ev[["label", "collateral_exclusion", "collateral_capture", "collateral_dependency", "collateral_displacement", "collateral_conflict"]],
                 hide_index=True, width="stretch")
if budget <= 1000:
    st.info("$1,000 starter: only Cr(VI) speciation tests and a sunflower + biochar plot fit; washing water for a few weeks is borderline.")
with st.expander("Everything fundable at this tier, and the baseline care cascade"):
    st.dataframe(m5_options.fundable_table(budget).drop(columns=["is_mock"]).round(2), hide_index=True, width="stretch")
    st.dataframe(m5_options.baseline().assign(group=lambda d: d.group.map(lambda x: equity.GROUP_LABELS.get(x, x))).drop(columns=["is_mock"]).round(3), hide_index=True)

# 3. How money flows
st.header("3 · Who decides and who administers")
l, r = st.columns(2)
with l:
    st.markdown("**Community-decided vs top-down vs per-capita**")
    fit = st.slider("Local-fit multiplier (assumption 1.0–1.3)", 1.0, 1.3, 1.1, 0.05)
    ws = st.slider("Women's decision seats", 0.0, 0.5, 0.3, 0.05)
    wk = st.slider("Worker seats", 0.0, 0.5, 0.1, 0.05)
    summ, det = allocation.simulate(scored, budget, top_k, {"local_fit_multiplier": fit, "women_seat_share": ws, "worker_seat_share": wk})
    st.dataframe(summ[["regime", "women_reached", "extra_pathways", "cost_per_pathway", "unregistered_share_of_reach", "equity_gap_after"]].round(3), hide_index=True)
    st.caption("Local-choice effect is an ASSUMPTION (CDD syntheses show mixed effects and capture risk). The model does not value legitimacy or sustainability. Priorities are MOCK.")
with r:
    st.markdown("**Escrow: need floor + capacity tranche**")
    floor = st.slider("Need floor %", 0.0, 1.0, 0.5, 0.05)
    unres = st.toggle("Unrestricted funds (route via more-foreign intermediary instead of holding)", False)
    rc = st.columns(2)
    rules = {"referral_min": rc[0].slider("Referral ≥", 0.0, 1.0, 0.40, 0.05), "posts_filled_min": rc[1].slider("Posts filled ≥", 0.0, 1.0, 0.60, 0.05)}
    sched, esum, warns = escrow.run(scored, max(budget, 10_000), top_k, floor, rules=rules, unrestricted=unres)
    st.altair_chart(wm(alt.Chart(esum.melt("year", ["released_usd", "held_usd"])).mark_bar().encode(x="year:O", y="value:Q", color="variable:N"), 400, 200))
    st.caption("Share administered locally by 2030: " + f"{esum.share_managed_locally.iloc[-1]:.0%}")
for w_ in warns[:4]:
    (st.warning if w_.startswith(("Lock", "Gaming", "$")) else st.info)(w_)
with st.expander("Escrow schedule by town and year"):
    st.dataframe(sched[["cadaster_name", "year", "admin_capacity_index", "released_usd", "held_in_escrow_usd", "administered_by_floor", "administered_by_tranche",
                        "thresholds_failed"]].round(3), hide_index=True, width="stretch")

# 4. Environment
st.header("4 · What a soil or water finding triggers")
sites = sites_df()
e1, e2 = st.columns([3, 2])
e1.dataframe(sites[["site_name", "parameter", "value_mg_kg", "hq_soil_only_low", "hq_soil_only_high", "tier", "evidence_rung"]].round(3), hide_index=True)
tor = m4_exposure.tornado()
e2.altair_chart(wm(alt.Chart(tor).mark_bar().encode(y=alt.Y("driver:N", sort="-x", title=None), x=alt.X("swing:Q", title="HQ swing")), 360, 200))
e2.caption("Evidence that would most change the response: " + tor.iloc[0].evidence_that_would_change_response)
st.caption("Soil values are real (CNRS-L/MoE 2026), locations mock. Tier 2 = plausible pathway (rung b), never demonstrated harm (rung c). Chemstar child, soil only: HQ ≈ 0.002–0.98.")
with st.expander("Evidence table and trigger protocol"):
    ev_t = m4_exposure.evidence_table(sites)
    st.dataframe(ev_t, hide_index=True, width="stretch")
    st.download_button("Download evidence table", ev_t.to_csv(index=False), "tab_evidence.csv")
    st.table(pd.DataFrame([(t, r_, a_) for t, (r_, a_) in m4_exposure.ACTIONS.items()], columns=["tier", "rung", "action"]))

# 5. Who to approach
st.header("5 · Funders and partners to approach")
f = funding()
res = ff.rank(ff.filter_funding(f, None, False, True), ["health", "maternal"]).head(5)
st.dataframe(res[["name", "funder", "amount", "currency", "channel", "recency_flag", "fits_escrow", "url", "verified_on"]], hide_index=True, width="stretch")
st.caption("From data/registry/funding_registry.csv. 'Fits escrow' = can be pooled and open to local orgs.")

# Assistant
st.subheader("Ask the funding assistant")
_client = chat_llm.get_client()
st.caption(("LLM assistant (" + chat_llm.MODEL + ") loops through the funding, organisation and source registries; every claim cites a registry id and URL. "
            "It never uses outside knowledge for grants.") if _client else
           "No ANTHROPIC_API_KEY found (set it in .env): showing retrieval-only answers from the registries.")
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
            ctx = f"budget tier {budget_label}; priority cadasters: {', '.join(top.cadaster_name.head(3))}; theme: community-decided, locally administered funding"
            r_ = chat_llm.ask(q_, history=st.session_state.chat_hist[:-1], client=_client, context=ctx)
        st.markdown(r_["answer"])
        st.caption(f"Mode: {r_['mode']}" + (f" · cited: {', '.join(r_['citations'])}" if r_["citations"] else ""))
        if r_["trace"]:
            with st.expander("Registry lookups"):
                st.json(r_["trace"])
    st.session_state.chat_hist.append({"role": "assistant", "content": r_["answer"]})

# Reference
st.header("Evidence, assumptions and data")
with st.expander("Assumptions log"):
    asm = assumptions.build()
    st.dataframe(asm, hide_index=True, width="stretch")
    st.download_button("Download assumptions CSV", asm.to_csv(index=False), "tab_assumptions.csv")
with st.expander("Data status and context"):
    st.dataframe(pd.concat([io.data_status(), io.reference_status()]), hide_index=True, width="stretch")
    gm = gov.groupby(["year", "projected"]).agg(admin_capacity_index=("admin_capacity_index", "mean"), share_funds_managed_locally=("share_funds_managed_locally", "mean")).reset_index()
    long = gm.melt(["year", "projected"], var_name="indicator", value_name="value")
    base = alt.Chart(long).encode(x="year:O", y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1])), color="indicator:N")
    st.altair_chart(wm(base.transform_filter(alt.datum.year <= 2026).mark_line(point=True) + base.transform_filter(alt.datum.year >= 2026).mark_line(strokeDash=[5, 4]), 640, 260))
    st.caption("Capacity vs local control, 2019–2030 (dashed = projected; mock). 2019 crisis → 2020 blast → 2024 war → 2026 war.")
    wdi = io.load_wdi_population("LBN")
    if wdi is not None:
        st.line_chart(wdi.set_index("year").population)
        st.caption("Lebanon resident population, World Bank WDI (real).")
