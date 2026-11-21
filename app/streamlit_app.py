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


# ---------------- sidebar ----------------
st.sidebar.title("Beqaa health priorities")
color = {"MOCK": "#c0392b", "PARTIAL": "#d68910", "REAL": "#1e8449"}[MODE]
st.sidebar.markdown(f"<div style='background:{color};color:white;padding:8px;border-radius:6px;text-align:center'>"
                    f"<b>DATA MODE: {MODE}</b>{' — synthetic cadasters, placeholder costs' if IS_MOCK else ''}</div>", unsafe_allow_html=True)
PAGES = ["0 · Story timeline", "1 · Overview", "2 · Priority map", "3 · Access", "4 · Options & budget", "5 · Community allocation",
         "6 · Environment & evidence", "7 · Funding finder", "8 · Escrow & funding switch", "9 · Ask the registry", "10 · Assumptions log"]
page = st.sidebar.radio("Page", PAGES)
group = st.sidebar.selectbox("Group filter", ["All"] + [equity.GROUP_LABELS[g] for g in equity.GROUPS])
budget_label = st.sidebar.selectbox("Budget tier", list(m5_options.BUDGET_TIERS) + ["Custom"])
budget = st.sidebar.number_input("Custom budget (USD)", 100, 10_000_000, 50_000, 1000) if budget_label == "Custom" else m5_options.BUDGET_TIERS[budget_label]
st.sidebar.caption("Lebanese-facing wording: land- and community-based framing; 'displaced Syrians'.")
GL = {v: k for k, v in equity.GROUP_LABELS.items()}

if IS_MOCK:
    st.error("MOCK DATA: all figures below use synthetic cadasters and placeholder costs. Do not cite them. Real files in data/raw/ replace mock files automatically.")


def footer():
    st.divider()
    st.subheader("2030 indicators (baseline)")
    gov, _ = io.load_dataset("governance_capacity")
    stf, _ = io.load_dataset("staffing_referrals")
    g = gov[(~gov.projected.astype(bool))]
    g = g[g.year == g.year.max()]
    acc = m1_access.access_by_cadaster()
    ga = m1_access.group_access(acc).set_index("group")
    c = st.columns(6)
    c[0].metric("Funds managed locally", f"{g.share_funds_managed_locally.mean():.0%}")
    c[1].metric("Referral completion", f"{stf.referral_completed_month.sum() / stf.referral_sent_month.sum():.0%}")
    c[2].metric("Clinics reporting a Need Score", "0%", help="Target of the pilot; none report one today")
    c[3].metric("Posts filled", f"{stf.posts_filled.sum() / stf.posts_budgeted.sum():.0%}")
    c[4].metric("Access ratio (worst group / host)", f"{ga.ratio_to_host.drop('women_15_49').min():.2f}")
    c[5].metric("Days soil finding → protective action", "n/a", help="Not measured yet: baseline to be set in pilot")


# ---------------- pages ----------------
if page == PAGES[0]:
    st.title("Story: from crisis to a state-led system")
    st.write("2019 economic crisis → 2020 Beirut blast → 2024 war → 2026 war → 2030 target. **Theme:** an adaptive funding switch: money follows "
             "measured need, and administrative control shifts from foreign NGOs to Lebanese entities (municipalities → MoPH) as measured capacity improves.")
    gov, _ = io.load_dataset("governance_capacity")
    m = gov.groupby(["year", "projected"]).agg(admin_capacity_index=("admin_capacity_index", "mean"),
                                                 share_funds_managed_locally=("share_funds_managed_locally", "mean")).reset_index()
    long = m.melt(["year", "projected"], var_name="indicator", value_name="value")
    base = alt.Chart(long).encode(x=alt.X("year:O"), y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1])), color="indicator:N")
    solid = base.transform_filter(alt.datum.year <= 2026).mark_line(point=True)
    dashed = base.transform_filter(alt.datum.year >= 2026).mark_line(strokeDash=[5, 4])
    st.altair_chart(wm(solid + dashed, 760, 340), width='content')
    st.caption("Dashed = projected. Liquid-model curve: capacity dips at each shock, local control follows capacity.")
    wdi = io.load_wdi_population("LBN")
    if wdi is not None:
        st.subheader("Lebanon resident population (World Bank WDI, real data)")
        st.line_chart(wdi.set_index("year").population)
        st.caption("Source: World Bank WDI SP.POP.TOTL. National level; includes the post-2011 Syrian influx and later decline.")
    st.subheader("Four stresses and where they are measured")
    st.markdown("- **High need** → Priority map (2)\n- **Low providership** → Priority map, stress layer *providership*\n"
                "- **Disjointed referrals** → Priority map, stress layer *referral*; Escrow (8)\n"
                "- **NGO dependency** → Priority map, stress layer *NGO dependency*; Escrow (8); Funding finder (7)")

elif page == PAGES[1]:
    st.title("Overview: traditional approach vs proposed approach")
    c1, c2 = st.columns(2)
    c1.subheader("Traditional")
    c1.markdown("- Funds allocated by appeal and agency footprint\n- Foreign NGOs administer, state capacity stays low\n- Referrals untracked\n"
                "- Unregistered workers invisible in statistics")
    c2.subheader("Proposed")
    c2.markdown("- Need Score directs money to the highest-need cadasters, with a guaranteed floor\n- Control shifts INGO → national NGO → municipality → MoPH as capacity is measured\n"
                "- Communities decide how funds are spent, with capture safeguards\n- Equity gaps reported for every group, including unregistered workers (estimated)")
    st.subheader("The five challenge questions")
    st.table(pd.DataFrame({"Question": ["Q1 Which need, whose access is most constrained?", "Q2 How do soil/water/food findings trigger action?",
                                        "Q3 How can aid support local services and reach all groups?", "Q4 What is justified now, what needs investigating?",
                                        "Q5 How to measure access, continuity, equity?"],
                           "Answered on": ["2 Priority map, 3 Access", "6 Environment & evidence", "4 Options, 5 Community allocation, 8 Escrow",
                                           "6 Environment (tornado), 4 Options", "2030 indicators footer, 3 Access (group gaps)"]}))
    st.subheader("Data status")
    st.dataframe(pd.concat([io.data_status(), io.reference_status()]), hide_index=True, width='stretch')

elif page == PAGES[2]:
    st.title("Priority map")
    c = st.columns(4)
    d0 = c[0].selectbox("Catchment d0 (min)", [15, 30, 60], 1)
    demand = c[1].selectbox("Demand population", ["women_15_49", "pregnant_est", "population_total"], 0)
    env_on = c[2].toggle("Environment domain", True)
    unreg = c[3].toggle("Include unregistered workers", True)
    st.markdown("**Domain weights** (renormalised)")
    wc = st.columns(4)
    w = {d: wc[i].slider(d.replace("_", " "), 0.0, 1.0, float(CFG["domain_weights"][d]), 0.05) for i, d in enumerate(m2.DOMAINS)}
    tc = st.columns(3)
    hi = tc[0].slider("High ≥", 0.3, 0.9, CFG["tiers"]["high"], 0.01)
    mo = tc[1].slider("Moderate ≥", 0.1, 0.7, CFG["tiers"]["moderate"], 0.01)
    geo = tc[2].toggle("Non-compensatory (geometric mean)", False)
    spec = {**CFG, "tiers": {"high": hi, "moderate": mo}}
    raw = raw_ind(d0, demand)
    if not unreg:
        raw = raw.assign(unregistered_workers_share=0.0)
    on = [d for d in m2.DOMAINS if d != "environment" or env_on]
    scored = m2.compute(raw, w, spec, geo, on)
    rob = m2.robustness(raw, spec=spec, geometric=geo, domains_on=on)
    layer = st.selectbox("Stress layer", ["need", "providership", "referral", "ngo_dependency", "environment"])
    col = f"stress_{layer}"
    r, g, b = [], [], []
    v = scored[col].fillna(0)
    scored["_r"] = (255 * v).astype(int); scored["_g"] = (200 * (1 - v)).astype(int)
    scored["_rad"] = scored.population_total.pow(0.5) * 25
    layers = [pdk.Layer("ScatterplotLayer", scored, get_position=["lon", "lat"], get_radius="_rad", get_fill_color=["_r", "_g", 40, 190], pickable=True)]
    if st.checkbox("Overlay facilities (green open / red closed)"):
        fac, _ = io.load_dataset("facilities")
        fac = fac.assign(_c=fac.status_2026.map(lambda s: [30, 140, 60, 230] if s == "open" else [200, 30, 30, 230]))
        layers.append(pdk.Layer("ScatterplotLayer", fac, get_position=["lon", "lat"], get_radius=1200, get_fill_color="_c"))
    if st.checkbox("Overlay soil sites (by tier)"):
        s = sites_df().dropna(subset=["lat"]).assign(_c=lambda d: d.tier.map({0: [120, 120, 120, 220], 1: [240, 190, 0, 230], 2: [130, 0, 160, 240]}))
        layers.append(pdk.Layer("ScatterplotLayer", s, get_position=["lon", "lat"], get_radius=1800, get_fill_color="_c"))
    if IS_MOCK:
        layers.append(pdk.Layer("TextLayer", pd.DataFrame({"lat": [scored.lat.mean()], "lon": [scored.lon.mean()], "t": ["MOCK DATA"]}),
                                get_position=["lon", "lat"], get_text="t", get_size=60, get_color=[220, 0, 0, 120]))
    left, right = st.columns([3, 2])
    left.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=scored.lat.mean(), longitude=scored.lon.mean(), zoom=7.6),
                               tooltip={"text": "{cadaster_name}\nNeed {need_score}"}))
    left.caption(f"Color = {layer} stress (0 green → 1 red); size = population. Mock locations are synthetic.")
    top = scored.merge(rob[["cadaster_id", "p_top_tier", "rank_p05", "rank_p95"]], on="cadaster_id").sort_values("rank").head(10)
    right.markdown("**Top 10 cadasters**")
    right.dataframe(top[["cadaster_name", "district", "need_score", "tier", "p_top_tier", "rank_p05", "rank_p95"]].round(3), hide_index=True)
    st.markdown("**Comparison with official district severity (JIAF 2.0 / FSA)**")
    comp, hidden = m2.compare_official(scored)
    st.dataframe(comp.round(3), hide_index=True, width='stretch')
    if len(hidden):
        st.warning("Cadasters in the top 10 inside districts the official map rates below median:")
        st.dataframe(hidden.round(3), hide_index=True)
    st.markdown("**Need by group (population-weighted)**")
    st.dataframe(m2.group_need(scored).assign(group=lambda d: d.group.map(equity.GROUP_LABELS)).round(3), hide_index=True)
    st.markdown("**Tiers & triggers**")
    st.table(m2.triggers())

elif page == PAGES[3]:
    st.title("Access to care (E2SFCA)")
    c = st.columns(4)
    d0 = c[0].selectbox("Catchment d0 (min)", [15, 30, 60], 1)
    demand = c[1].selectbox("Demand", ["women_15_49", "pregnant_est", "population_total", "weighted_women_15_49"], 0)
    fac_f = c[2].selectbox("Facilities", ["all", "offers_anc"])
    kind = c[3].selectbox("Decay", ["gaussian", "stepped"])
    dw = None
    if demand == "weighted_women_15_49":
        st.caption("Women 15–49 per group (WorldPop age/sex share × displacement counts) × demand multiplier.")
        wc = st.columns(3)
        dw = {"displaced_lebanese": wc[0].slider("Displaced Lebanese ×", 0.5, 3.0, 1.0, 0.1),
              "registered_displaced_syrians": wc[1].slider("Registered displaced Syrians ×", 0.5, 3.0, 1.0, 0.1),
              "unregistered_workers_est": wc[2].slider("Unregistered workers ×", 0.5, 3.0, 1.0, 0.1)}
    acc = m1_access.access_by_cadaster(d0, demand, fac_f, kind, dw)
    a = acc.sort_values("access_lost", ascending=False).head(15)
    long = a.melt("cadaster_name", ["access_baseline", "access_current"], "scenario", "access")
    long["access"] *= 1000
    st.altair_chart(wm(alt.Chart(long).mark_bar().encode(y=alt.Y("cadaster_name:N", sort=None), x="access:Q", color="scenario:N", yOffset="scenario:N"), 720, 420))
    st.caption("Weekly capacity per 1,000 women (or chosen demand): pre-2026 (all open) vs current (closed/damaged dropped).")
    st.subheader("Access by group vs host Lebanese")
    ga = m1_access.group_access(acc).assign(group=lambda d: d.group.map(equity.GROUP_LABELS))
    st.dataframe(ga[["group", "access_baseline", "access_current", "access_lost", "ratio_to_host", "gap_vs_host"]].round(4), hide_index=True)
    st.caption("Spatial access only (where each group lives). Legal and financial barriers enter via the cascade in page 4. Mock groups are spread near-uniformly, so gaps are small here.")
    st.subheader("Catchment-size sensitivity")
    sens = m1_access.catchment_sensitivity(demand if demand != "weighted_women_15_49" else "women_15_49")
    piv = sens.pivot(index="cadaster_name", columns="d0", values="rank_current"); piv.columns = [f"d0={c}" for c in piv.columns]
    st.dataframe(piv.assign(rank_range=piv.max(axis=1) - piv.min(axis=1)).sort_values("d0=30").head(15), width='stretch')
    st.subheader("Mobile-unit siting")
    k = st.slider("Number of mobile units k", 1, 6, 3)
    sites = m1_access.mobile_unit_sites(k, d0)
    st.dataframe(sites.drop(columns=["is_mock"]), hide_index=True)

elif page == PAGES[4]:
    st.title("Options & budget")
    scored = m2.compute(raw_ind(30, "women_15_49"))
    iv, _ = io.load_dataset("interventions")
    st.subheader(f"What is fundable at {budget_label if budget_label != 'Custom' else f'${budget:,.0f}'}")
    ft = m5_options.fundable_table(budget)
    st.dataframe(ft.drop(columns=["is_mock"]).round(2), hide_index=True, width='stretch')
    if budget <= 1000:
        st.info("$1,000 starter: Cr(VI) speciation tests and a sunflower + biochar plot are the only options that fit; washing-water for a few weeks is borderline.")
    pick = st.multiselect("Choose 2–3 interventions", list(iv.intervention_id), default=["transport_vouchers", "chw_women_orgs"][: 2], max_selections=3)
    if pick:
        ev = m5_options.evaluate(pick, budget)
        st.dataframe(ev[["label", "budget_usd", "units_median", "women_reached_median", "extra_pathways_median", "extra_pathways_p05",
                         "extra_pathways_p95", "cost_per_pathway_median", "equity_gap_before", "equity_gap_after"]].round(2), hide_index=True)
        st.altair_chart(wm(alt.Chart(ev).mark_bar().encode(x="label:N", y="extra_pathways_median:Q",
                                                            tooltip=["extra_pathways_p05", "extra_pathways_p95"]), 560, 280))
        st.subheader("Collateral-damage checklist")
        st.dataframe(ev[["label", "collateral_exclusion", "collateral_capture", "collateral_dependency", "collateral_displacement", "collateral_conflict"]],
                     hide_index=True, width='stretch')
        top = m5_options.where_it_goes(scored, ev.women_reached_median.sum())
        if len(top):
            st.subheader("Where it goes (highest Need Score cadasters first)")
            st.dataframe(top.round(3), hide_index=True)
    st.subheader("Baseline care cascade by group (pathway completion = product of steps)")
    st.dataframe(m5_options.baseline().assign(group=lambda d: d.group.map(lambda x: equity.GROUP_LABELS.get(x, x))).drop(columns=["is_mock"]).round(3), hide_index=True)
    st.caption("Costs, lifts and cascade values are MOCK until UNFPA/WHO/K2P figures replace them.")

elif page == PAGES[5]:
    st.title("Community allocation simulator")
    scored = m2.compute(raw_ind(30, "women_15_49"))
    c = st.columns(5)
    k = c[0].slider("Top-k cadasters", 3, 15, 8)
    fit = c[1].slider("Local-fit multiplier (assumption)", 1.0, 1.3, 1.1, 0.05)
    ws = c[2].slider("Women's decision seats", 0.0, 0.5, 0.3, 0.05)
    wk = c[3].slider("Worker seats", 0.0, 0.5, 0.1, 0.05)
    ru = c[4].slider("Reach of unregistered (relative)", 0.2, 1.0, 0.5, 0.05)
    summ, det = allocation.simulate(scored, budget, k, {"local_fit_multiplier": fit, "women_seat_share": ws, "worker_seat_share": wk,
                                                          "share_reaching_unregistered": ru})
    st.dataframe(summ.drop(columns=["is_mock"]).round(3), hide_index=True, width='stretch')
    st.altair_chart(wm(alt.Chart(summ).mark_bar().encode(x="regime:N", y="extra_pathways:Q", color="regime:N"), 480, 260))
    st.subheader("What local choice changes")
    st.dataframe(allocation.what_local_choice_changes(summ).round(3), hide_index=True)
    st.warning("The effect of community decision-making is an ASSUMPTION with a literature range (CDD syntheses, e.g. 3ie 2018 and Mansuri & Rao 2013, "
               "find mixed effects and elite-capture risk), not an estimate. The model does not value legitimacy, uptake or sustainability, "
               "which are the main arguments for local choice. Community priority weights are MOCK. Capture falls as women's and worker seats rise.")
    st.dataframe(det.round(3), hide_index=True, width='stretch')

elif page == PAGES[6]:
    st.title("Environment & evidence")
    sites = sites_df()
    st.caption("Soil values are the real CNRS-L/MoE (Apr 2026) values; their locations are MOCK. Reference doses are EPA defaults (status: verify).")
    st.dataframe(sites[["site_name", "parameter", "value_mg_kg", "hq_soil_only_low", "hq_soil_only_high", "hq_low", "hq_high", "screening_ratio", "tier",
                        "evidence_rung", "action"]].round(4), hide_index=True, width='stretch')
    st.info("Chemstar Cr 230 mg/kg, child, soil only: HQ ≈ 0.002 (all Cr III) to ≈ 0.98 (all Cr VI). Adding the crop pathway pushes the Cr(VI) end above 1 "
            "(crop transfer factors are MOCK): tier 2 = plausible exposure (rung b), never demonstrated harm (rung c).")
    st.subheader("What evidence would change the response (tornado)")
    tor = m4_exposure.tornado()
    st.altair_chart(wm(alt.Chart(tor).mark_bar().encode(y=alt.Y("driver:N", sort="-x"), x=alt.X("swing:Q", title="HQ swing"),
                                                         tooltip=["evidence_that_would_change_response"]), 640, 220))
    st.dataframe(tor[["rank_voi", "driver", "swing", "evidence_that_would_change_response"]].round(2), hide_index=True)
    mc = m4_exposure.monte_carlo(230)
    st.write(f"Monte Carlo (Chemstar, child, soil+food): HQ 5th–95th = {mc['p5']:.2f}–{mc['p95']:.2f}, P(HQ ≥ 1) = {mc['p_exceed_1']:.0%}.")
    st.subheader("Evidence table (rungs a / b / c)")
    ev = m4_exposure.evidence_table(sites)
    st.dataframe(ev, hide_index=True, width='stretch')
    st.download_button("Download evidence table", ev.to_csv(index=False), "tab_evidence.csv")
    st.subheader("Trigger protocol")
    st.table(pd.DataFrame([(t, r, a) for t, (r, a) in m4_exposure.ACTIONS.items()], columns=["tier", "rung", "action"]))

elif page == PAGES[7]:
    st.title("Funding finder")
    f = funding()
    c = st.columns(4)
    sectors = c[0].multiselect("Priority sectors", ["health", "maternal", "SRH", "humanitarian", "recovery", "water", "civil society"], ["health", "maternal"])
    chans = c[1].multiselect("Channel", sorted(f.channel.unique()), list(f.channel.unique()))
    local = c[2].toggle("Local orgs eligible (or to verify)", False)
    active = c[3].toggle("Active or recent only (last 6 months)", True)
    res = ff.rank(ff.filter_funding(f, chans, local, active), sectors)
    st.dataframe(res[["fund_id", "name", "funder", "amount", "currency", "channel", "period", "recency_flag", "fits_escrow", "score", "url", "verified_on"]],
                 hide_index=True, width='stretch')
    st.caption("Every row is from data/registry/funding_registry.csv with its source URL and verified_on date. 'Fits escrow?' = can the money be pooled and are local orgs eligible.")
    st.subheader("Money by channel over time (dependency metric)")
    fl, _ = io.load_dataset("funding_flows")
    st.altair_chart(wm(alt.Chart(fl).mark_area().encode(x="year:O", y=alt.Y("usd_m:Q", stack="normalize", title="share of funding"), color="channel:N"), 640, 280))
    st.subheader("Implementing organisations (to verify)")
    st.dataframe(ff.load_orgs(), hide_index=True, width='stretch')

elif page == PAGES[8]:
    st.title("Escrow & funding switch")
    scored = m2.compute(raw_ind(30, "women_15_49"))
    c = st.columns(4)
    pool = c[0].number_input("Pool (USD)", 10_000, 50_000_000, int(budget) if budget >= 10_000 else 1_000_000, 10_000)
    n = c[1].slider("Priority towns", 3, 15, 8)
    floor = c[2].slider("Need floor %", 0.0, 1.0, 0.5, 0.05)
    unres = c[3].toggle("Unrestricted funds", False)
    r = st.columns(4)
    rules = {"referral_min": r[0].slider("Referral completion ≥", 0.0, 1.0, 0.40, 0.05), "posts_filled_min": r[1].slider("Posts filled ≥", 0.0, 1.0, 0.60, 0.05),
             "transparent_required": r[2].toggle("Transparent reporting required", True), "admin_capacity_min": r[3].slider("Admin capacity index ≥", 0.0, 1.0, 0.40, 0.05)}
    sched, summ, warns = escrow.run(scored, pool, n, floor, rules=rules, unrestricted=unres)
    st.altair_chart(wm(alt.Chart(summ.melt("year", ["released_usd", "held_usd"])).mark_bar().encode(x="year:O", y="value:Q", color="variable:N"), 560, 260))
    st.dataframe(summ.round(3), hide_index=True)
    for w_ in warns:
        (st.warning if w_.startswith(("Lock", "Gaming", "$")) else st.info)(w_)
    st.dataframe(sched[["cadaster_name", "year", "admin_capacity_index", "need_floor_usd", "tranche_released_usd", "held_in_escrow_usd", "administered_by_floor",
                        "administered_by_tranche", "thresholds_failed", "share_managed_locally"]].round(3), hide_index=True, width='stretch')
    st.caption("Administrator by capacity band: INGO → national NGO → municipality → MoPH. All thresholds and bands are assumptions.")

elif page == PAGES[9]:
    st.title("Ask the registry")
    st.caption("Grounded retrieval over funding_registry.csv and org_registry.csv only. No match → 'No verified entry'.")
    q = st.text_input("Question", "maternal health funding for national NGOs")
    if q:
        a = chat.answer(q)
        st.markdown(a["answer"])

else:
    st.title("Assumptions log")
    a = assumptions.build()
    st.dataframe(a, hide_index=True, width='stretch')
    st.download_button("Download assumptions CSV", a.to_csv(index=False), "tab_assumptions.csv")

footer()
