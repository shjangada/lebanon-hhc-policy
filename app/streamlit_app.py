"""Beqaa Health Prioritization dashboard. Run: make app"""
import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from beqaa import (allocation, assumptions, chat, equity, escrow, funding_finder as ff, io, m1_access, m2_need_score as m2,
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
st.sidebar.markdown("**Scenario**")
budget_label = st.sidebar.selectbox("Budget tier", list(m5_options.BUDGET_TIERS) + ["Custom"], 1)
budget = st.sidebar.number_input("Custom budget (USD)", 100, 10_000_000, 50_000, 1000) if budget_label == "Custom" else m5_options.BUDGET_TIERS[budget_label]
layer = st.sidebar.selectbox("Map layer", ["need", "providership", "referral", "ngo_dependency", "environment"])
d0 = st.sidebar.selectbox("Catchment d0 (min)", [15, 30, 60], 1)
st.sidebar.markdown("**Model settings**")
with st.sidebar.expander("Need Score weights and toggles"):
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

spec = {**CFG, "top_k": top_k}
raw = raw_ind(d0, "women_15_49" if demand == "weighted_women_15_49" else demand)
if not unreg:
    raw = raw.assign(unregistered_workers_share=0.0)
on = [d for d in m2.DOMAINS if d != "environment" or env_on]
scored = m2.compute(raw, w, spec, geo, on)
rob = m2.robustness(raw, spec=spec, geometric=geo, domains_on=on)
acc = m1_access.access_by_cadaster(d0, demand, "all", "gaussian", dw if demand == "weighted_women_15_49" else None)
ga = m1_access.group_access(acc)

# ---------------- layout helpers ----------------
st.markdown("""<style>
.block-container{padding-top:1.4rem;max-width:1280px}
[data-testid="stMetricValue"]{font-size:1.45rem}
[data-testid="stMetricLabel"] p{font-size:.8rem}
h3{margin-top:0;padding-top:0}
.nav a{margin-right:1.1rem;text-decoration:none;font-weight:600;font-size:.9rem}
.takeaway{font-size:1.02rem;margin:-.2rem 0 .6rem 0}
</style>""", unsafe_allow_html=True)

NAV = [("s1", "1 Priority & access"), ("s2", "2 Options & budget"), ("s3", "3 Allocation & escrow"), ("s4", "4 Soil & water triggers"), ("s5", "5 Funding sources"), ("ref", "Evidence & data")]
NAV_HTML = "<div class='nav'>" + "".join(f"<a href='#{i}'>{t}</a>" for i, t in NAV) + "</div>"
st.sidebar.markdown("**Jump to**")
st.sidebar.markdown(NAV_HTML.replace("<div class='nav'>", "<div class='nav' style='line-height:2'>"), unsafe_allow_html=True)


def section(anchor, title, takeaway):
    """Bordered card: anchor, title, one-line takeaway. Use as `with section(...):`."""
    st.markdown(f"<a id='{anchor}'></a>", unsafe_allow_html=True)
    box = st.container(border=True)
    box.subheader(title)
    box.markdown(f"<div class='takeaway'>{takeaway}</div>", unsafe_allow_html=True)
    return box


def pretty(df, **rename):
    return df.rename(columns=rename)


# ---------------- header ----------------
st.title("Where should Beqaa primary-care money go first, and who should run it?")
st.caption("Adaptive funding switch: money follows measured need; control moves from foreign NGOs to Lebanese entities (municipalities → MoPH) as measured capacity improves. "
           "Traditional: funds follow appeals and agency footprint, referrals untracked, unregistered workers invisible.")
if IS_MOCK:
    st.error("MOCK DATA: synthetic cadasters and placeholder costs. Do not cite these numbers.", icon="⚠️")
st.markdown(NAV_HTML, unsafe_allow_html=True)

gov, _ = io.load_dataset("governance_capacity")
stf, _ = io.load_dataset("staffing_referrals")
g_ = gov[(~gov.projected.astype(bool))]
g_ = g_[g_.year == g_.year.max()]
gg = ga.set_index("group")
worst_ratio = gg.ratio_to_host.drop("women_15_49").min()
with st.container(border=True):
    c = st.columns(5)
    c[0].metric("Funds managed locally", f"{g_.share_funds_managed_locally.mean():.0%}", help="2030 indicator, current baseline")
    c[1].metric("Referral completion", f"{stf.referral_completed_month.sum() / stf.referral_sent_month.sum():.0%}")
    c[2].metric("Posts filled", f"{stf.posts_filled.sum() / stf.posts_budgeted.sum():.0%}")
    c[3].metric("Access lost to closures", f"{acc.access_lost.sum() / acc.access_baseline.sum():.0%}")
    c[4].metric("Worst-group access vs host", f"{worst_ratio:.2f}×", help="1.00 = parity. Spatial access only.")

top = scored.merge(rob[["cadaster_id", "p_top_tier", "rank_p05", "rank_p95"]], on="cadaster_id").sort_values("rank").head(10)
stable = rob[rob.p_top_tier >= 0.9].cadaster_name.tolist()

# ---------------- 1. Where ----------------
with section("s1", "1 · Priority & access",
             f"Highest need: <b>{top.cadaster_name.iloc[0]}</b>, {top.cadaster_name.iloc[1]}, {top.cadaster_name.iloc[2]}. "
             f"{('Stable across weightings: ' + ', '.join(stable)) if stable else 'Ranking is sensitive to the weights.'}"):
    left, right = st.columns([3, 2])
    col = f"stress_{layer}"
    v = scored[col].fillna(0)
    scored["_r"] = (255 * v).astype(int); scored["_g"] = (200 * (1 - v)).astype(int); scored["_rad"] = scored.population_total.pow(0.5) * 25
    layers = [pdk.Layer("ScatterplotLayer", scored, get_position=["lon", "lat"], get_radius="_rad", get_fill_color=["_r", "_g", 40, 190], pickable=True)]
    ov = left.pills("Overlays", ["Facilities (green open / red closed)", "Soil sites (by tier)"], selection_mode="multi", label_visibility="collapsed")
    if "Facilities (green open / red closed)" in (ov or []):
        fac, _ = io.load_dataset("facilities")
        fac = fac.assign(_c=fac.status_2026.map(lambda s_: [30, 140, 60, 230] if s_ == "open" else [200, 30, 30, 230]))
        layers.append(pdk.Layer("ScatterplotLayer", fac, get_position=["lon", "lat"], get_radius=1200, get_fill_color="_c"))
    if "Soil sites (by tier)" in (ov or []):
        s_ = sites_df().dropna(subset=["lat"]).assign(_c=lambda d: d.tier.map({0: [120, 120, 120, 220], 1: [240, 190, 0, 230], 2: [130, 0, 160, 240]}))
        layers.append(pdk.Layer("ScatterplotLayer", s_, get_position=["lon", "lat"], get_radius=1800, get_fill_color="_c"))
    if IS_MOCK:
        layers.append(pdk.Layer("TextLayer", pd.DataFrame({"lat": [scored.lat.mean()], "lon": [scored.lon.mean()], "t": ["MOCK DATA"]}),
                                get_position=["lon", "lat"], get_text="t", get_size=60, get_color=[220, 0, 0, 120]))
    left.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=scored.lat.mean(), longitude=scored.lon.mean(), zoom=7.4),
                               tooltip={"text": "{cadaster_name}\nNeed {need_score}"}), height=380)
    left.caption(f"Layer: **{layer}** (change in sidebar). Green = low, red = high; size = population.")
    right.markdown("**Top 10 by Need Score**")
    right.dataframe(pretty(top[["cadaster_name", "need_score", "p_top_tier"]].round(2), cadaster_name="Cadaster", need_score="Need", p_top_tier="Top-tier prob."),
                    hide_index=True, height=385)
    right.caption("Top-tier prob. = share of 5,000 random weightings that place it in the top-k.")
    st.markdown("**Access by group** (vs host Lebanese, 1.0 = parity)")
    gl = ga.assign(group=ga.group.map(equity.GROUP_LABELS))
    st.altair_chart(wm(alt.Chart(gl).mark_bar().encode(y=alt.Y("group:N", sort=None, title=None), x=alt.X("ratio_to_host:Q", title=None)), 760, 190))
    with st.expander("Access lost to 2026 closures · official-severity comparison · tiers and triggers · mobile-unit siting"):
        a = acc.sort_values("access_lost", ascending=False).head(10)
        long = a.melt("cadaster_name", ["access_baseline", "access_current"], "scenario", "access")
        long["access"] *= 1000
        st.altair_chart(wm(alt.Chart(long).mark_bar().encode(y=alt.Y("cadaster_name:N", sort=None, title=None), x=alt.X("access:Q", title="capacity per 1,000"),
                                                             color="scenario:N", yOffset="scenario:N"), 700, 300))
        comp, hidden = m2.compare_official(scored)
        st.markdown("**Official severity (JIAF/FSA) vs our district ranking**")
        st.dataframe(comp.round(3), hide_index=True, width="stretch")
        if len(hidden):
            st.warning("Top-10 cadasters inside districts the official map rates below median:")
            st.dataframe(hidden.round(3), hide_index=True)
        st.markdown("**Tiers and triggers**")
        st.table(m2.triggers())
        k = st.slider("Mobile units k", 1, 6, 3)
        st.dataframe(m1_access.mobile_unit_sites(k, d0).drop(columns=["is_mock"]), hide_index=True)

# ---------------- 2. What to fund ----------------
iv, _ = io.load_dataset("interventions")
tier_name = budget_label if budget_label != "Custom" else f"${budget:,.0f}"
pick = st.session_state.get("pick", ["transport_vouchers", "chw_women_orgs"])
ev = m5_options.evaluate(pick, budget) if pick else None
best = ev.sort_values("extra_pathways_median", ascending=False).iloc[0] if ev is not None and len(ev) else None
with section("s2", "2 · Options & budget",
             (f"Best of your picks: <b>{best.label}</b>, about {best.extra_pathways_median:,.0f} extra completed care pathways "
              f"(range {best.extra_pathways_p05:,.0f}–{best.extra_pathways_p95:,.0f})." if best is not None else "Pick interventions to compare.")):
    pick = st.multiselect("Compare up to 3 interventions", list(iv.intervention_id), default=pick, max_selections=3, key="pick",
                          format_func=lambda i: iv.set_index("intervention_id").loc[i, "label"])
    if pick:
        ev = m5_options.evaluate(pick, budget)
        st.dataframe(pretty(ev[["label", "women_reached_median", "extra_pathways_median", "cost_per_pathway_median", "equity_gap_after"]].round(1),
                            label="Intervention", women_reached_median="Women reached", extra_pathways_median="Extra pathways",
                            cost_per_pathway_median="$ per pathway", equity_gap_after="Equity gap after"), hide_index=True, width="stretch")
        with st.expander("Collateral-damage check (who could be excluded, capture, dependency)"):
            st.dataframe(pretty(ev[["label", "collateral_exclusion", "collateral_capture", "collateral_dependency", "collateral_displacement", "collateral_conflict"]],
                                label="Intervention", collateral_exclusion="Excludes", collateral_capture="Capture", collateral_dependency="Dependency",
                                collateral_displacement="Displaces local providers", collateral_conflict="Conflict sensitivity"), hide_index=True, width="stretch")
    if budget <= 1000:
        st.info("$1,000 starter: only Cr(VI) speciation tests and a sunflower + biochar plot fit; washing water for a few weeks is borderline.")
    with st.expander("Everything fundable at this tier · baseline care cascade"):
        st.dataframe(m5_options.fundable_table(budget).drop(columns=["is_mock"]).round(2), hide_index=True, width="stretch")
        st.dataframe(m5_options.baseline().assign(group=lambda d: d.group.map(lambda x: equity.GROUP_LABELS.get(x, x))).drop(columns=["is_mock"]).round(3), hide_index=True)

# ---------------- 3. Who decides ----------------
fit = st.session_state.get("fit", 1.1); ws = st.session_state.get("ws", 0.3); wk = st.session_state.get("wk", 0.1)
floor = st.session_state.get("floor", 0.5); unres = st.session_state.get("unres", False)
rules = {"referral_min": st.session_state.get("ref_min", 0.40), "posts_filled_min": st.session_state.get("posts_min", 0.60)}
summ, det = allocation.simulate(scored, budget, top_k, {"local_fit_multiplier": fit, "women_seat_share": ws, "worker_seat_share": wk})
sched, esum, warns = escrow.run(scored, max(budget, 10_000), top_k, floor, rules=rules, unrestricted=unres)
sm = summ.set_index("regime")
held = esum.held_usd.sum() / max(esum.held_usd.sum() + esum.released_usd.sum(), 1)
with section("s3", "3 · Allocation & escrow",
             f"Community-decided allocation reaches <b>{sm.loc['community', 'women_reached'] / sm.loc['top_down', 'women_reached']:.0%}</b> of the women top-down does under these assumptions; "
             f"escrow holds back <b>{held:.0%}</b> of funds and ends at <b>{esum.share_managed_locally.iloc[-1]:.0%}</b> locally administered by {int(esum.year.max())}."):
    l, r = st.columns(2)
    with l:
        st.markdown("**Who decides: community vs top-down vs per-capita**")
        st.dataframe(pretty(summ[["regime", "women_reached", "extra_pathways", "unregistered_share_of_reach", "equity_gap_after"]].round(3),
                            regime="Regime", women_reached="Women reached", extra_pathways="Extra pathways",
                            unregistered_share_of_reach="Unregistered share", equity_gap_after="Equity gap"), hide_index=True, width="stretch")
        with st.popover("Adjust assumptions"):
            st.slider("Local-fit multiplier (assumption, 1.0–1.3)", 1.0, 1.3, 1.1, 0.05, key="fit")
            st.slider("Women's decision seats", 0.0, 0.5, 0.3, 0.05, key="ws")
            st.slider("Worker seats", 0.0, 0.5, 0.1, 0.05, key="wk")
        st.caption("The local-choice effect is an assumption. The model does not value legitimacy or sustainability. Priorities are mock.")
    with r:
        st.markdown("**Who administers: escrow by year**")
        st.altair_chart(wm(alt.Chart(esum.melt("year", ["released_usd", "held_usd"])).mark_bar().encode(x="year:O", y=alt.Y("value:Q", title="USD"), color="variable:N"), 420, 190))
        with st.popover("Adjust escrow rules"):
            st.slider("Need floor %", 0.0, 1.0, 0.5, 0.05, key="floor")
            st.toggle("Unrestricted (route via a more-foreign intermediary instead of holding)", False, key="unres")
            st.slider("Referral completion ≥", 0.0, 1.0, 0.40, 0.05, key="ref_min")
            st.slider("Posts filled ≥", 0.0, 1.0, 0.60, 0.05, key="posts_min")
    if warns:
        with st.expander(f"Warnings ({len(warns)}): lock-outs and gaming risk", expanded=False):
            for w_ in warns:
                (st.warning if w_.startswith(("Lock", "Gaming", "$")) else st.info)(w_)
    with st.expander("Escrow schedule by town and year"):
        st.dataframe(sched[["cadaster_name", "year", "admin_capacity_index", "released_usd", "held_in_escrow_usd", "administered_by_floor", "administered_by_tranche",
                            "thresholds_failed"]].round(3), hide_index=True, width="stretch")

# ---------------- 4. Soil & water ----------------
sites = sites_df()
tor = m4_exposure.tornado()
n_t2 = int((sites.tier >= 2).sum())
with section("s4", "4 · Soil & water triggers",
             f"{n_t2} of {len(sites)} soil results reach tier 2 (plausible exposure pathway, rung b); none is confirmed harm (rung c). "
             f"Biggest uncertainty: <b>{tor.iloc[0].driver.split(' (')[0].lower()}</b>."):
    e1, e2 = st.columns(2)
    e1.markdown("**Soil results and screening tier**")
    e1.dataframe(pretty(sites[["site_name", "parameter", "value_mg_kg", "hq_soil_only_low", "hq_soil_only_high", "tier"]].round(3), site_name="Site", parameter="Metal",
                        value_mg_kg="mg/kg", hq_soil_only_low="HQ low", hq_soil_only_high="HQ high", tier="Tier"), hide_index=True, height=300)
    e2.markdown("**What evidence would change the response**")
    e2.altair_chart(wm(alt.Chart(tor).mark_bar().encode(y=alt.Y("driver:N", sort="-x", title=None), x=alt.X("swing:Q", title="HQ swing")), 420, 200))
    e2.caption("Most valuable next evidence: " + tor.iloc[0].evidence_that_would_change_response)
    st.caption("Soil values are real (CNRS-L/MoE 2026); locations are mock. Chemstar child, soil only: HQ ≈ 0.002 (all Cr III) to ≈ 0.98 (all Cr VI).")
    with st.expander("Evidence table (rungs a/b/c) and trigger protocol"):
        ev_t = m4_exposure.evidence_table(sites)
        st.dataframe(ev_t, hide_index=True, width="stretch")
        st.download_button("Download evidence table", ev_t.to_csv(index=False), "tab_evidence.csv")
        st.table(pd.DataFrame([(t, r_, a_) for t, (r_, a_) in m4_exposure.ACTIONS.items()], columns=["tier", "rung", "action"]))

# ---------------- 5. Funders ----------------
f = funding()
res = ff.rank(ff.filter_funding(f, None, False, True), ["health", "maternal"]).head(5)
with section("s5", "5 · Funding sources",
             f"{len(res)} active or recent funds match health and maternal care; top match: <b>{res.name.iloc[0]}</b> ({res.channel.iloc[0]})." if len(res) else "No active match."):
    st.dataframe(pretty(res[["name", "funder", "channel", "recency_flag", "fits_escrow", "url", "verified_on"]], name="Fund", funder="Funder", channel="Channel",
                        recency_flag="Status", fits_escrow="Fits escrow?", url="Source", verified_on="Verified"),
                 hide_index=True, width="stretch", column_config={"Source": st.column_config.LinkColumn("Source", display_text="open")})
    st.caption("From data/registry/funding_registry.csv. 'Fits escrow' = can be pooled and open to local organisations.")

# ---------------- Reference ----------------
st.markdown("<a id='ref'></a>", unsafe_allow_html=True)
st.subheader("Evidence, assumptions and data")
with st.expander("Ask the registry (grounded; no match → 'No verified entry')"):
    q = st.text_input("Question", "maternal health funding for national NGOs")
    if q:
        st.markdown(chat.answer(q)["answer"])
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
