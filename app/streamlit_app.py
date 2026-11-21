"""Beqaa Health Prioritization dashboard. Run: make app"""
import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from beqaa import (robustness, allocation, assumptions, chat, chat_llm, equity, escrow, funding_finder as ff, io, m1_access, m2_need_score as m2,
                   m4_exposure, m5_options, research_gaps, state_capacity)

try:                                   # Sankey for the escrow flow; falls back to a table if plotly is not installed
    import plotly.graph_objects as go
except ImportError:                    # pragma: no cover
    go = None

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


def _version():
    """Cache key: modification times of the code, parameters and data. Switching branches or regenerating data changes it, so stale cached
    frames (e.g. built before an indicator existed) are never reused."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    files = list((root / "src" / "beqaa").rglob("*.py")) + list((root / "data" / "params").glob("*.yaml")) + list((root / "data" / "mock").glob("*.csv")) \
        + list((root / "data" / "derived").glob("*.csv")) + list((root / "data" / "registry").glob("*.csv"))
    return max((f.stat().st_mtime_ns for f in files), default=0)


VER = _version()


@st.cache_data
def raw_ind(d0, demand, cr6, ver):      # `ver` (no leading underscore) is part of the cache key: code/data changes invalidate it
    return m2.raw_indicators(d0, demand, cr6_for_tier=cr6)


@st.cache_data
def sites_df(cr6, ver):
    return m4_exposure.screen_sites(cr6_for_tier=cr6)


@st.cache_data
def funding(ver):
    return ff.annotate(ff.load_funding())


# ---------------- sidebar: global controls ----------------
st.sidebar.title("Beqaa health priorities")
color = {"MOCK": "#c0392b", "PARTIAL": "#d68910", "REAL": "#1e8449"}[MODE]
st.sidebar.markdown(f"<div style='background:{color};color:white;padding:8px;border-radius:6px;text-align:center'>"
                    f"<b>DATA MODE: {MODE}</b>{' — synthetic cadasters, placeholder costs' if IS_MOCK else ''}</div>", unsafe_allow_html=True)
st.sidebar.markdown("**Scenario**")
budget_label = st.sidebar.selectbox("Budget tier", list(m5_options.BUDGET_TIERS) + ["Custom"], 1)
budget = st.sidebar.number_input("Custom budget (USD)", 100, 10_000_000, 50_000, 1000) if budget_label == "Custom" else m5_options.BUDGET_TIERS[budget_label]
layer = st.sidebar.selectbox("Map layer", ["need", "environment"])
d0 = st.sidebar.selectbox("Catchment d0 (min)", [15, 30, 60], 1)
st.sidebar.markdown("**Model settings**")
with st.sidebar.expander("Need Score weights and toggles"):
    w = {d: st.slider(d.replace("_", " "), 0.0, 1.0, float(CFG["domain_weights"][d]), 0.05) for d in m2.DOMAINS}
    env_on = st.toggle("Environment domain", True)
    unreg = st.toggle("Include unregistered workers", True)
    geo = st.toggle("Non-compensatory (geometric mean)", False)
    top_k = st.slider("Top-k cadasters (priority set)", 3, 15, CFG["top_k"])
with st.sidebar.expander("Environmental damage → need and money (M4 links)"):
    precaution = st.toggle("Precautionary Cr tiering (treat all Cr as Cr(VI))", True,
                           help="Until speciation results exist, the Cr tier uses the worst case. Untick to set an assumed Cr(VI) share.")
    cr6 = None if precaution else st.slider("Assumed Cr(VI) share of total Cr", 0.0, 1.0, 0.1, 0.05)
    env_w = st.slider("Environmental exposure weight in allocation / escrow priority", 0.0, 0.5, float(escrow.NEED_GATE["env_priority_weight"]), 0.05,
                      help="Priority = (1 − w)·Need Score + w·M4 environmental exposure. The Need Score already has an environment domain (weight above); "
                           "this is an explicit top-up. 0 = need only.")
    st.caption("M4 soil/water tiers → Need Score environment domain → allocation & escrow priority.")
with st.sidebar.expander("Demand weighting for access"):
    demand = st.selectbox("Demand", ["women_15_49", "weighted_women_15_49", "pregnant_est", "population_total"])
    dw = {"displaced_lebanese": st.slider("Displaced Lebanese ×", 0.5, 3.0, 1.0, 0.1),
          "registered_displaced_syrians": st.slider("Registered displaced Syrians ×", 0.5, 3.0, 1.0, 0.1),
          "unregistered_workers_est": st.slider("Unregistered workers ×", 0.5, 3.0, 1.0, 0.1)}

spec = {**CFG, "top_k": top_k}
raw = raw_ind(d0, "women_15_49" if demand == "weighted_women_15_49" else demand, cr6, VER)
if not unreg:
    raw = raw.assign(unregistered_workers_share=0.0)
on = [d for d in m2.DOMAINS if d != "environment" or env_on]
scored = m2.compute(raw, w, spec, geo, on)
if scored.attrs.get("skipped_indicators"):
    st.warning("Indicators skipped (not in the loaded data): " + ", ".join(scored.attrs["skipped_indicators"]) + ". Press C then Rerun to clear caches.")
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

NAV = [("s1", "1 Priority"), ("s2", "2 Options"), ("s3", "3 Allocation"), ("s4", "4 Exposure"), ("s5", "5 Funding"), ("s6", "6 Robustness"), ("ref", "Evidence")]
NAV_HTML = "<div class='nav'>" + "".join(f"<a href='#{i}'>{t}</a>" for i, t in NAV) + "</div>"
st.sidebar.markdown("**Jump to**")
st.sidebar.markdown(NAV_HTML.replace("<div class='nav'>", "<div class='nav' style='line-height:2'>"), unsafe_allow_html=True)


PURPOSE = {
    "s1": "Ranks cadasters by need, so money is aimed at the places and groups that need care most. Includes access by group and how robust the ranking is.",
    "s2": "Compares what each intervention would achieve for a given budget: reach, cost, who it might exclude, and other side effects.",
    "s3": "Tests who should decide how funds are spent (community, top-down, per capita) and who administers them as measured capacity grows (escrow).",
    "s4": "Screens soil and water findings for plausible health exposure and sets the protective action each tier triggers.",
    "s6": "Re-runs the priority list and the allocation policies under uncertain assumptions and six stress scenarios, and recommends only what holds up.",
    "s5": "Lists the funders that could pay for this, with source, recency and whether the money can go through local organisations; includes the funding assistant.",
}


def section(anchor, title, takeaway):
    """Bordered card: anchor, title, purpose line, one-line takeaway. Use as `with section(...):`."""
    st.markdown(f"<a id='{anchor}'></a>", unsafe_allow_html=True)
    box = st.container(border=True)
    box.subheader(title)
    if anchor in PURPOSE:
        box.caption(PURPOSE[anchor])
    box.markdown(f"<div class='takeaway'>{takeaway}</div>", unsafe_allow_html=True)
    return box


def pretty(df, **rename):
    return df.rename(columns=rename)


# ---------------- header ----------------
st.title("Where should Beqaa primary-care money go first, and who should run it?")
st.caption("Adaptive funding switch: money follows measured need; control moves from foreign NGOs to Lebanese entities (national NGOs, Unions of Municipalities, with MoPH co-governing) as measured capacity improves. "
           "Traditional: funds follow appeals and agency footprint, referrals untracked, unregistered workers invisible.")
if IS_MOCK:
    st.error("MOCK DATA: synthetic cadasters and placeholder costs. Do not cite these numbers.", icon="⚠️")
st.markdown(NAV_HTML, unsafe_allow_html=True)

gg = ga.set_index("group")
worst_ratio = gg.ratio_to_host.drop("women_15_49").min()
_f = ff.annotate(ff.load_funding())
n_active = int((_f.recency_flag == "active or recent").sum())
n_stable = int((rob.p_top_tier >= 0.9).sum())
with st.container(border=True):
    c = st.columns(4)
    c[0].metric("Access lost to closures", f"{acc.access_lost.sum() / acc.access_baseline.sum():.0%}", help="Women 15-49 capacity, pre-2026 vs now (E2SFCA)")
    c[1].metric("Worst-group access vs host", f"{worst_ratio:.2f}×", help="1.00 = parity. Spatial access only.")
    c[2].metric("Stable priority cadasters", f"{n_stable}", help="Top-k in at least 90% of random domain weightings")
    c[3].metric("Active or recent funds", f"{n_active}", help="From the funding registry")

top = scored.merge(rob[["cadaster_id", "p_top_tier", "rank_p05", "rank_p95"]], on="cadaster_id").sort_values("rank").head(10)
stable = rob[rob.p_top_tier >= 0.9].cadaster_name.tolist()

# ---------------- 1. Where ----------------
with section("s1", "1 · Priority",
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
        s_ = sites_df(cr6, VER).dropna(subset=["lat"]).assign(_c=lambda d: d.tier.map({0: [120, 120, 120, 220], 1: [240, 190, 0, 230], 2: [130, 0, 160, 240]}))
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

    with st.expander("Resilience: power source and conflict exposure of open facilities"):
        thr = st.slider("Conflict-exposed = at least this many incidents in the cadaster since Oct 2023", 1, 40, 15, key="conf_thr")
        fr = m1_access.facility_risk(thr)
        c1, c2, c3 = st.columns(3)
        c1.metric("Open facilities", len(fr))
        c2.metric("On grid power only", int(fr.grid_only.sum()), help="Grid supplies ~4-6 h/day: needs generator or solar")
        c3.metric("In conflict-exposed cadasters", int(fr.conflict_exposed.sum()), help="Fixed assets that should be pausable")
        pz = m1_access.access_if_exposed_pause(d0, "women_15_49", thr).sort_values("pct_lost", ascending=False)
        st.markdown(f"**If the {int(pz.n_paused_facilities.iloc[0])} exposed facilities paused, access falls most in:**")
        st.dataframe(pretty(pz[["cadaster_name", "district", "pct_lost"]].head(8).assign(pct_lost=lambda d: (d.pct_lost * 100).round(0)),
                            cadaster_name="Cadaster", district="District", pct_lost="Access lost (%)"), hide_index=True, width="stretch")
        st.caption("Power source is mock (pilot-measured); conflict incidents are mock counts standing in for the LRP 2026 admin-3 incident table. "
                   "Conflict exposure is also a Need Score indicator (vulnerability domain).")

    with st.expander("Method check: does the ranking depend on our formula choices?"):
        ms = m2.method_sensitivity(raw, spec=spec)
        st.dataframe(pretty(ms[["variant", "spearman_vs_reference", "top_k_retained", "top_k_jaccard", "max_rank_shift"]].round(2),
                            variant="Alternative choice", spearman_vs_reference="Rank correlation", top_k_retained=f"Top-{top_k} kept",
                            top_k_jaccard="Top-k overlap", max_rank_shift="Max rank shift"), hide_index=True, width="stretch")
        st.caption("Each row changes one methodological choice (aggregation, normalisation, weights, dropped domain) and compares with the default. "
                   "Low overlap = that choice drives the priority list, so report it as contested. Rationale and precedents: docs/METHODS_DECISIONS.md.")

# ---------------- 2. What to fund ----------------
iv, _ = io.load_dataset("interventions")
tier_name = budget_label if budget_label != "Custom" else f"${budget:,.0f}"
pick = st.session_state.get("pick", ["transport_vouchers", "chw_women_orgs"])
ev = m5_options.evaluate(pick, budget) if pick else None
best = ev.sort_values("extra_pathways_median", ascending=False).iloc[0] if ev is not None and len(ev) else None
with section("s2", "2 · Options",
             (f"Best of your picks: <b>{best.label}</b>, about {best.extra_pathways_median:,.0f} extra completed care pathways "
              f"(range {best.extra_pathways_p05:,.0f}–{best.extra_pathways_p95:,.0f})." if best is not None else "Pick interventions to compare.")):
    feas = m5_options.feasibility_table().set_index("intervention_id")
    only_ok = st.checkbox("Only interventions that pass the feasibility filter (F1–F8)", False, key="only_ok")
    opts = [i for i in iv.intervention_id if not only_ok or feas.loc[i, "feasible"]]
    pick = [i for i in pick if i in opts]
    pick = st.multiselect("Compare up to 3 interventions", opts, default=pick, max_selections=3, key="pick",
                          format_func=lambda i: iv.set_index("intervention_id").loc[i, "label"] + ("" if feas.loc[i, "feasible"] else " ⚠"))
    if pick:
        ev = m5_options.evaluate(pick, budget)
        st.dataframe(pretty(ev[["label", "women_reached_median", "extra_pathways_median", "cost_per_pathway_median", "equity_gap_after"]].round(1),
                            label="Intervention", women_reached_median="Women reached", extra_pathways_median="Extra pathways",
                            cost_per_pathway_median="$ per pathway", equity_gap_after="Equity gap after"), hide_index=True, width="stretch")
        with st.expander("Feasibility filter F1–F8 (no new public money, pausable, low grid power, no new doctors, existing institution, no ID, funding window, measurable)"):
            st.dataframe(pretty(feas.loc[pick, ["label", "flags", "existing_institution", "funding_window", "indicator_source"]].assign(flags=lambda d: d["flags"].replace("", "passes all")),
                                label="Intervention", flags="Fails", existing_institution="Existing institution", funding_window="Funding window",
                                indicator_source="Indicator"), hide_index=True, width="stretch")
            st.caption("Qualitative team judgments from docs/FEASIBILITY.md (assumptions, not data). ⚠ in the picker = fails at least one test.")
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
rules.update(admin_capacity_min=st.session_state.get("cap_min", float(escrow.DEFAULT_RULES["admin_capacity_min"])))
need_min = st.session_state.get("need_min", float(escrow.NEED_GATE["need_score_min"]))
yoy = st.session_state.get("yoy", float(escrow.DEFAULT_YOY_GAIN))
allow_moph = st.session_state.get("allow_moph", False)
summ, det = allocation.simulate(scored, budget, top_k, {"local_fit_multiplier": fit, "women_seat_share": ws, "worker_seat_share": wk}, env_weight=env_w)
esc_on = st.session_state.get("esc", False)
sched, esum, warns = escrow.run(scored, max(budget, 10_000), top_k, floor, rules=rules, unrestricted=unres, escalation_year=2028 if esc_on else None,
                                env_weight=env_w, need_min=need_min, yoy_gain=yoy, max_level="MoPH" if allow_moph else escrow.DEFAULT_MAX_LEVEL)
sm = summ.set_index("regime")
held = esum.held_usd.sum() / max(esum.held_usd.sum() + esum.released_usd.sum(), 1)
with section("s3", "3 · Allocation",
             f"Pilot test arms, not results: with these assumptions the community arm reaches <b>{sm.loc['community', 'women_reached'] / sm.loc['top_down', 'women_reached']:.0%}</b> of the women top-down does. "
             f"Escrow holds back <b>{held:.0%}</b> of funds; <b>{esum.share_lebanese_managed.iloc[-1]:.0%}</b> is administered by Lebanese organisations by {int(esum.year.max())}."):
    l, r = st.columns(2)
    with l:
        st.markdown("**Who decides: pilot test arms (community vs top-down vs per-capita)**")
        st.dataframe(pretty(summ[["regime", "women_reached", "extra_pathways", "unregistered_share_of_reach", "equity_gap_after"]].round(3),
                            regime="Regime", women_reached="Women reached", extra_pathways="Extra pathways",
                            unregistered_share_of_reach="Unregistered share", equity_gap_after="Equity gap"), hide_index=True, width="stretch")
        with st.popover("Adjust assumptions"):
            st.slider("Local-fit multiplier (assumption, 1.0–1.3)", 1.0, 1.3, 1.1, 0.05, key="fit")
            st.slider("Women's decision seats", 0.0, 0.5, 0.3, 0.05, key="ws")
            st.slider("Worker seats", 0.0, 0.5, 0.1, 0.05, key="wk")
        st.caption("The local-choice effect is an assumption to be tested in a stepped-wedge pilot, not a finding. The model does not value legitimacy or sustainability. Priorities are mock.")
        with st.expander("How much does the result depend on the assumptions?"):
            st.dataframe(allocation.sensitivity(scored, budget, top_k).round(2), width="stretch")
            st.caption("Community-arm extra pathways as a ratio of top-down (rows: capture rate 0.1–0.4; columns: local-fit multiplier 1.0–1.3; no safeguards). Above 1.0 the community arm does better.")
    with r:
        st.markdown("**Who administers: escrow by year**")
        st.altair_chart(wm(alt.Chart(esum.melt("year", ["released_usd", "held_usd"])).mark_bar().encode(x="year:O", y=alt.Y("value:Q", title="USD"), color="variable:N"), 420, 190))
        st.caption(f"Share administered by Lebanese organisations: {esum.share_lebanese_managed.iloc[0]:.0%} in {int(esum.year.min())} → {esum.share_lebanese_managed.iloc[-1]:.0%} in {int(esum.year.max())}. "
                   "Pilot target ≥50% (assumption). MoPH co-governs; it is not assumed to administer.")
        with st.popover("Adjust escrow rules"):
            st.slider("Need floor %", 0.0, 1.0, 0.5, 0.05, key="floor")
            st.toggle("Unrestricted (route via a more-foreign intermediary instead of holding)", False, key="unres")
            st.toggle("Renewed escalation from 2028 (capacity drops, recovers slowly)", False, key="esc")
            st.caption("Scenario inputs: capacity, referral and staffing figures are mock defaults that the pilot would measure (no public source).")
            st.slider("Referral completion ≥", 0.0, 1.0, 0.40, 0.05, key="ref_min")
            st.slider("Posts filled ≥", 0.0, 1.0, 0.60, 0.05, key="posts_min")
            st.slider("District admin capacity ≥ (national anchor SC01 = 0.299)", 0.0, 0.7, float(escrow.DEFAULT_RULES["admin_capacity_min"]), 0.01, key="cap_min")
            st.slider("Need gate: Need Score ≥", 0.0, 0.9, float(escrow.NEED_GATE["need_score_min"]), 0.01, key="need_min")
            st.slider("Projected capacity gain per year (cap 0.05)", 0.0, float(escrow.MAX_YOY_CAPACITY_GAIN), float(escrow.DEFAULT_YOY_GAIN), 0.005, key="yoy")
            st.toggle("Allow MoPH as administrator (default: co-governor only)", False, key="allow_moph")
    st.markdown("**P5 pool flow: international funds → pooled escrow → thresholds → administrator → community committee → districts**")
    yrs = ["All years"] + sorted(sched.year.unique().tolist())
    ysel = st.radio("Year", yrs, horizontal=True, key="flow_year", label_visibility="collapsed")
    links = escrow.flow_links(sched, None if ysel == "All years" else int(ysel))
    if go is not None and len(links):
        nodes = list(dict.fromkeys(list(links.source) + list(links.target)))
        ncol = ["#7f8c8d" if n.startswith(("International", "Pooled")) else "#c0392b" if "held" in n else "#2e86c1" if n.startswith("Administrator")
                else "#27ae60" if n.startswith("Community") else "#8e44ad" if n.startswith("District") else "#d68910" for n in nodes]
        fig = go.Figure(go.Sankey(node=dict(label=nodes, pad=14, thickness=14, color=ncol),
                                  link=dict(source=[nodes.index(x) for x in links.source], target=[nodes.index(x) for x in links.target],
                                            value=links.value_usd.round(0).tolist())))
        fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=8), font_size=11)
        if IS_MOCK:
            fig.add_annotation(text="MOCK DATA", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, textangle=-25,
                               font=dict(size=60, color="rgba(220,0,0,0.20)"))
        st.plotly_chart(fig, width="stretch")
    else:
        st.dataframe(links.round(0), hide_index=True, width="stretch")
        st.caption("Install plotly for the Sankey view (pip install plotly).")
    st.caption("Need floor is guaranteed by priority; the capacity tranche needs every threshold to pass. Administrator = who holds the money; "
               "the community committee (women ≥30%, workers incl. unregistered ≥10% of seats) decides use at every rung. Thresholds: data/params/escrow_params.yaml.")
    with st.expander("Who controls money at each capacity level · state-capacity anchor · allocation by district"):
        st.dataframe(escrow.role_table(sched).round(3), hide_index=True, width="stretch")
        st.markdown("**State-capacity anchor (real national values; district series is mock)**")
        st.dataframe(state_capacity.capacity_panel(), hide_index=True, width="stretch",
                     column_config={"url": st.column_config.LinkColumn("url", display_text="open")})
        gcap = state_capacity.anchored_governance(yoy_gain=yoy)
        st.altair_chart(wm(alt.Chart(gcap).mark_line(point=True).encode(x="year:O", y=alt.Y("admin_capacity_index:Q", title="admin capacity (anchored, mock spread)"),
                                                                       color="district:N", strokeDash="projected:N")
                           + alt.Chart(pd.DataFrame({"y": [b for b in escrow.BANDS]})).mark_rule(color="grey", strokeDash=[2, 2]).encode(y="y:Q"), 640, 240))
        st.caption("Grey rules = ladder bands (national NGO 0.28 = WGI 2023 low; Union of Municipalities 0.40; MoPH 0.514 = WGI 2000 high). "
                   "Dashed = projected with the capped yearly gain.")
        st.dataframe(escrow.by_district(sched).round(3), hide_index=True, width="stretch")
        st.dataframe(allocation.by_district(det).round(1), hide_index=True, width="stretch")
    if warns:
        with st.expander(f"Warnings ({len(warns)}): lock-outs and gaming risk", expanded=False):
            for w_ in warns:
                (st.warning if w_.startswith(("Lock", "Gaming", "$")) else st.info)(w_)
    with st.expander("Escrow schedule by town and year"):
        st.dataframe(sched[["cadaster_name", "year", "admin_capacity_index", "released_usd", "held_in_escrow_usd", "administered_by_floor", "administered_by_tranche",
                            "thresholds_failed"]].round(3), hide_index=True, width="stretch")

# ---------------- 4. Soil & water ----------------
sites = sites_df(cr6, VER)
tor = m4_exposure.tornado()
n_t2 = int((sites.tier >= 2).sum())
with section("s4", "4 · Exposure",
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
    gaps = research_gaps.cadaster_gaps(scored, rob)
    cands = research_gaps.research_candidates(gaps)
    st.markdown(f"**Where evidence is weakest → implementation-research candidates** ({len(cands)} high-need cadasters with an evidence gap ≥ {research_gaps.GAP_MIN})")
    if len(cands):
        st.dataframe(pretty(cands[["cadaster_name", "district", "need_score", "evidence_gap_score", "main_gap", "study", "registry_rows"]].round(2),
                            cadaster_name="Cadaster", district="District", need_score="Need", evidence_gap_score="Evidence gap", main_gap="Main gap",
                            study="Study that would close it", registry_rows="Registry rows whose sectors fit"), hide_index=True, width="stretch")
    st.caption("Gap = Cr(VI) speciation decides the tier, rung-b pathway without health data, imputed well nitrate, unstable rank (weights are assumptions). "
               "Registry links are matches on sector keywords only: confirm eligibility; no grant is invented.")
    with st.expander("Evidence gaps by district and by intervention"):
        st.dataframe(research_gaps.district_gaps(gaps).round(3), hide_index=True, width="stretch")
        st.dataframe(research_gaps.intervention_gaps(tor), hide_index=True, width="stretch")

# ---------------- 5. Funders ----------------
f = funding(VER)
next_round = st.session_state.get("next_round", False)
show_closed = st.session_state.get("show_closed", False)
rank_mode = st.session_state.get("rank_mode", "Community decides (low donor involvement first)")
pool_f = ff.filter_funding(f, None, False, True, show_next_round=next_round, show_closed=show_closed, show_closed_to_new=show_closed)
res = ff.rank(pool_f, ["health", "maternal"])
if rank_mode.startswith("Community"):
    res = ff.rank_involvement(res)
res = res.head(8)
with section("s5", "5 · Funding",
             f"{len(res)} funds shown; top match: <b>{res.name.iloc[0]}</b> ({res.channel.iloc[0]}, {res.involvement_level.iloc[0]})." if len(res) else "No active match."):
    c1, c2, c3 = st.columns(3)
    c1.toggle("Show closed annual calls as 'expected next round'", False, key="next_round")
    c2.toggle("Show closed / closed-to-new rows", False, key="show_closed")
    c3.radio("Rank by", ["Community decides (low donor involvement first)", "Priority match (sector, open now, local eligibility)"], key="rank_mode",
             label_visibility="collapsed")
    st.dataframe(pretty(res[["name", "funder", "channel", "availability", "involvement_level", "fits_escrow", "url", "verified_on"]], name="Fund", funder="Funder",
                        channel="Channel", availability="Status", involvement_level="Donor involvement", fits_escrow="Fits escrow?", url="Source",
                        verified_on="Verified"),
                 hide_index=True, width="stretch", column_config={"Source": st.column_config.LinkColumn("Source", display_text="open")})
    st.caption("Only rows from data/registry/funding_registry.csv (never invented). Closed rows are hidden by default; 'expected next round' = recurring call, "
               "this round closed. Donor involvement: core / flexible / institutional funding ranks highest because the community committee decides use. "
               "'Fits escrow' = poolable money open to local organisations; direct grants to local orgs complement the pool.")
    with st.expander("Funding-flow data sources (where real allocation data comes from)"):
        try:
            st.dataframe(ff.load_datasets(), hide_index=True, width="stretch", column_config={"url": st.column_config.LinkColumn("url", display_text="open")})
            st.caption("data/registry/funding_datasets.csv: datasets, not grants. Use D01–D03 to measure the localisation share of LHF allocations (baseline for 'share managed locally').")
        except FileNotFoundError:
            st.info("data/registry/funding_datasets.csv not found.")

    st.markdown("**Ask the funding assistant**")
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


# ---------------- 6. Robustness ----------------
@st.cache_data
def robust(n, ver):
    return robustness.run_all(n=n)


rb_n = st.session_state.get("rb_n", 300)
RB = robust(rb_n, VER)
_core = RB["rank"]["core"]
_pol = RB["regret"]
with section("s6", "6 · Robustness",
             (f"<b>{len(_core)}</b> cadaster(s) stay in the top {RB['rank']['top_k']} in at least {RB['rank']['threshold']:.0%} of draws and in every scenario: <b>{', '.join(_core)}</b>. "
              if _core else "<b>No cadaster</b> holds a top-k place across every scenario: the priority list is not robust. ")
             + f"Allocation policy with the smallest worst-case regret: <b>{_pol['minimax_policy'].replace('_', ' ')}</b>"
             + (" (differs from the best on average)." if _pol["disagree"] else " (also best on average).")):
    st.markdown("**Priority cadasters across draws and scenarios** (share of draws in which it is top-k)")
    pc = RB["rank"]["per_cadaster"].head(12)
    cols = [c for c in pc.columns if c.startswith("p_top_") and c != "p_top_overall"]
    show = pc[["cadaster_name", "p_top_overall"] + cols + ["rank_p05", "rank_p95", "core"]].rename(columns={c: c.replace("p_top_", "") for c in cols})
    st.dataframe(show.round(2).rename(columns={"cadaster_name": "Cadaster", "p_top_overall": "overall", "rank_p05": "rank 5%", "rank_p95": "rank 95%", "core": "core"}),
                 hide_index=True, width="stretch")
    if RB["rank"]["warning"]:
        st.warning(RB["rank"]["warning"])
    a, b = st.columns(2)
    with a:
        st.markdown("**How far each scenario reshuffles the ranking**")
        st.dataframe(pretty(RB["rank"]["scenarios"].round(2), scenario="Scenario", kendall_tau_vs_baseline="Kendall τ vs baseline",
                            top_k_retained="Top-k kept", top_k="of"), hide_index=True, width="stretch")
        st.caption("τ = 1: same order as baseline. Funding shock and capacity stall do not change who is a priority; they change how much money flows and who administers it.")
    with b:
        st.markdown("**Allocation policies: regret across scenarios** (pathways lost vs the best policy in that world)")
        st.dataframe(pretty(_pol["summary"][["policy", "mean_value", "mean_regret", "max_regret", "minimax_rank"]].round(0),
                            policy="Policy", mean_value="Mean pathways", mean_regret="Mean regret", max_regret="Max regret", minimax_rank="Minimax rank"),
                     hide_index=True, width="stretch")
        st.caption("Allocations are fixed in advance on baseline data, then judged in each world. Prefer the smallest max regret, not the best average.")
    st.markdown("**Breakpoints: where does 'community beats top-down' flip?**")
    st.dataframe(pretty(RB["breakpoints"][["priorities", "assumption", "reading"]], priorities="Community priorities", assumption="Assumption", reading="Reading"),
                 hide_index=True, width="stretch")
    with st.expander("Escrow under funding shock, capacity stall and escalation (graceful degradation)"):
        st.dataframe(pretty(RB["escrow"].round(2), world="World", pool_usd="Pool $", released_usd="Released $", held_in_escrow_usd="Held $", conserved="Money conserved",
                            share_lebanese_managed_2030="Lebanese-managed 2030", towns_with_tranche_held="Towns with tranche held",
                            need_floor_still_paid="Need floor paid", n_warnings="Warnings"), hide_index=True, width="stretch")
    with st.expander("Scenario definitions and parameter ranges (data/params/uncertainty.yaml)"):
        st.dataframe(pd.DataFrame([{"scenario": v["label"], "what changes": ", ".join(f"{k}={val}" for k, val in v.items() if k not in ("label", "status")), "status": v["status"]}
                                   for v in RB["unc"]["scenarios"].values()]), hide_index=True, width="stretch")
        st.slider("Draws per scenario (preview; the pipeline uses 1,000)", 100, 1000, 300, 100, key="rb_n")
    st.caption("Mock data: scenario effects, costs and community priorities are assumptions; the structure and the method are what carry over to real data.")

# ---------------- Evidence ----------------
st.markdown("<a id='ref'></a>", unsafe_allow_html=True)
st.subheader("Evidence")

with st.expander("Assumptions log"):
    asm = assumptions.build()
    st.dataframe(asm, hide_index=True, width="stretch")
    st.download_button("Download assumptions CSV", asm.to_csv(index=False), "tab_assumptions.csv")
with st.expander("Data status and context"):
    st.dataframe(pd.concat([io.data_status(), io.reference_status()]), hide_index=True, width="stretch")
