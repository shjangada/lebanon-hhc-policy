"""Page 3: Who should hold the money, and when does control move? (the centrepiece)"""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import escrow, funding_finder as ff, io, narrative, theme_kpi  # noqa: E402

try:
    import plotly.graph_objects as go
except ImportError:                                    # table fallback
    go = None

scored = C.scored_cached(None, 30, 0.1, C.VER)
kt = theme_kpi.kpi_table(scored=scored)
base, stall = kt[kt.scenario == "baseline"].set_index("year"), kt[kt.scenario == "S5_capacity_stall"].set_index("year")
sent = narrative.page3(base.local_control_share.loc[2026], base.local_control_share.loc[2030], "baseline", stall.local_control_share.loc[2030])
C.header("Control of the money", sent, ["cadasters", "population", "governance_capacity", "funding_flows"], purpose="The escrow window: who holds the money at each stage from 2026 to 2030, what moves control up the ladder, and who decides how it is used.")
st.caption("Mechanism: international funds go into a ring-fenced window inside an existing pooled fund (LHF/LFF), pass a need gate, then a need floor (guaranteed) plus a capacity tranche (only if thresholds pass). "
           "An administrator ladder decides who holds the money: INGO → national NGO → union of municipalities, with MoPH co-governing. A community committee decides use at every rung. Capacity starts at the national anchor in every district (no district series is public) and grows at most 0.05 a year; referral completion and posts filled are scenario values, not data.")

a, b = st.columns([1, 2])
scn = a.selectbox("Scenario", list(theme_kpi.SCENARIOS), format_func=lambda k: theme_kpi.SCENARIO_LABELS[k], key="p3_scn")
year = b.select_slider("Year", options=["All years", 2026, 2027, 2028, 2029, 2030], value=2026, key="p3_year")
path, sched = theme_kpi._escrow_path(scn, scored)
yr = None if year == "All years" else int(year)
sel = path if yr is None else path[path.year == yr]
tot = float(sel.released_usd.sum())
lw = sum(float(sel[f"usd_{l}"].sum()) * escrow.LEVEL_LOCAL_WEIGHT[l] for l in escrow.LEVELS) / tot if tot else 0.0
m = st.columns(4)
m[0].metric("Local control (theme KPI)", f"{lw:.0%}", help="Released money weighted by the rung that holds it (INGO 0, national NGO 1/3, union 2/3, MoPH 1; escrow.LEVEL_LOCAL_WEIGHT, assumption). Status: assumption, mock district capacity inputs.")
m[1].metric("Released to towns", f"${tot:,.0f}", help="Need floor + capacity tranche released. Illustrative pool of $1M over 2026-2030 (assumption; compare the Health Sector requirement of $74.2M, SC/FEASIBILITY §1).")
m[2].metric("Held in escrow", f"${float(sel.held_usd.sum()):,.0f}", help="Capacity tranche withheld because a threshold failed (restricted mode).")
m[3].metric("Held by donors (INGO rung)", f"${float(sel['usd_INGO'].sum()):,.0f}", help="Money administered by an international NGO or UN agency as fiduciary.")

st.subheader("Who holds the money")
LADDER_COLORS = {"INGO": "#9aa5b1", "National NGO": "#7fb3d5", "Union of Municipalities": "#2874a6", "MoPH": "#0b3d63", "Held in escrow": "#e59866"}
def holder_frame(pth):
    long = pth.melt("year", [f"usd_{l}" for l in escrow.LEVELS] + ["held_usd"], "holder", "usd")
    long["holder"] = long.holder.str.replace("usd_", "", regex=False).replace({"held_usd": "Held in escrow"})
    long["share"] = long.usd / long.groupby("year").usd.transform("sum")
    return long
hf = holder_frame(path)
order = [h for h in LADDER_COLORS if h in set(hf.holder)]
bars = alt.Chart(hf).mark_bar().encode(
    y=alt.Y("year:O", title=None, sort="ascending"),
    x=alt.X("share:Q", title="share of released money", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
    color=alt.Color("holder:N", title="Held by", scale=alt.Scale(domain=order, range=[LADDER_COLORS[h] for h in order]), legend=alt.Legend(orient="bottom")),
    order=alt.Order("holder:N", sort="ascending"),
    tooltip=["year", "holder", alt.Tooltip("usd:Q", title="USD", format=",.0f"), alt.Tooltip("share:Q", title="share", format=".0%")])
st.altair_chart(C.wm(bars, 760, 230), use_container_width=False)
st.caption("Pool of $1M over 2026-2030 (illustrative). Grey = international fiduciary; blues = Lebanese rungs, darker = more local control; orange = capacity tranche held back because a threshold failed. "
           "Flow: pooled window inside LHF/LFF → need gate → need floor (guaranteed) + capacity tranche (only if every threshold passes) → administrator at the district's rung → community committee decides use "
           "(women ≥30%, workers incl. unregistered ≥10% of seats).")

st.subheader("Who controls money in each district" + (" (all years)" if yr is None else f" ({yr})"))
d = sched if yr is None else sched[sched.year == yr]
dd = d.groupby("district").agg(towns=("cadaster_id", "nunique"), released_usd=("released_usd", "sum"), held_usd=("held_in_escrow_usd", "sum"),
                               rung=("administered_by_floor", lambda x: x.value_counts().index[0]), capacity_index=("admin_capacity_index", "mean")).reset_index()
st.dataframe(C.pretty(dd.round(2), district="District", towns="Towns in window", released_usd="Released $", held_usd="Held $", rung="Rung holding the need floor (most common)", capacity_index="Capacity index"),
             hide_index=True, width="stretch")
st.caption("Only districts that contain priority towns appear. Capacity index = mock district series rescaled to the national anchor (SC01, World Bank WGI Government Effectiveness 29.9/100 for 2025).")

st.subheader("Local control over time, by scenario")
line = alt.Chart(kt.assign(scenario=kt.scenario.map(theme_kpi.SCENARIO_LABELS))).mark_line(point=True).encode(x=alt.X("year:O", title=None), y=alt.Y("local_control_share:Q", scale=alt.Scale(domain=[0, 1]), title="local control"),
                                                                                                       color=alt.Color("scenario:N", title=None, legend=alt.Legend(orient="bottom")))
st.altair_chart(C.wm(line, 760, 260), use_container_width=False)
st.caption("The theme KPI by year: it rises as capacity lets control move up the ladder, stays flat if capacity stalls (S5), and drops in 2028 under renewed escalation (S1) when the ladder falls back to an international fiduciary. Funding shock (S2) changes the dollars, not the ladder.")

st.subheader("Who decides how it is spent: community, top-down or per capita")
from beqaa import allocation  # noqa: E402
summ, _det = allocation.simulate(scored, 100_000, 8)
long = summ.melt("regime", ["women_reached", "extra_pathways"], "metric", "value")
long["metric"] = long.metric.map({"women_reached": "Women reached", "extra_pathways": "Extra completed care pathways"})
long["regime"] = long.regime.map({"top_down": "Top-down by need", "per_capita": "Equal per capita", "community": "Community-decided"})
al = alt.Chart(long).mark_bar().encode(x=alt.X("regime:N", title=None, sort=["Top-down by need", "Equal per capita", "Community-decided"]), y=alt.Y("value:Q", title=None), color=alt.Color("regime:N", legend=None),
                                       column=alt.Column("metric:N", title=None), tooltip=["regime", "metric", alt.Tooltip("value:Q", format=",.0f")])
st.altair_chart(al.properties(width=300, height=240), use_container_width=False)
st.warning("ASSUMED INPUTS: community priorities, local-fit and capture are scenario values, so these bars are test arms, not results.", icon="ℹ️")
st.caption("These are PILOT TEST ARMS, not results: the community arm's effect rests on assumptions (local-fit 1.0-1.3, capture 10-40%, mock community priorities), and the model does not value legitimacy or sustainability. "
           "Community-driven development delivers local public goods but does not transform governance by itself (see precedents), so the claim is better targeting, not institution-building. Breakpoints are on the Resilience page.")

st.subheader("Thresholds (data/params/escrow_params.yaml)")
P = yaml.safe_load(open(io.ROOT / "data" / "params" / "escrow_params.yaml"))
rows = []
src = {"expected_realisation": "LRP 2026 39% funded (FEASIBILITY §1)", "admin_capacity_min": "national anchor SC01 (WGI GE 2025 = 29.9/100)", "max_yoy_gain": "FEASIBILITY §5 (>0.05/yr not credible)"}
for sec in ("pool", "need_gate", "capacity_thresholds", "national_anchor"):
    for k, v in (P.get(sec) or {}).items():
        if isinstance(v, (dict, list)):
            continue
        rows.append({"section": sec, "parameter": k, "value": v, "source": src.get(k, "SC01/SC02 (state_capacity_sources.csv)" if sec == "national_anchor" else "assumption")})
for lv in P.get("ladder", []):
    rows.append({"section": "ladder", "parameter": f"{lv['level']}: minimum capacity", "value": lv["min_capacity"], "source": "assumption (anchored to SC01)"})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
st.caption("Thresholds are objective and pre-agreed (the Gavi lesson), process indicators rather than outcomes (Cochrane 2021: pay-for-performance effects mixed); all are assumptions the dashboard lets you vary on the Methods page.")

if C.women_lens():
    st.subheader("Women lens: which partners at each rung are women-led?")
    o = ff.load_orgs()
    rung = {"National NGO": o[o.type.str.contains("NGO|women|cooperative", case=False, na=False)], "Union of Municipalities": o[o.type.str.contains("municipal", case=False, na=False)],
            "MoPH (co-governs)": o[o.type.str.contains("government", case=False, na=False)], "INGO (fiduciary of last resort)": o.iloc[0:0]}
    t = pd.concat([x.assign(rung=k) for k, x in rung.items() if len(x)], ignore_index=True)
    st.dataframe(C.pretty(t[["rung", "name", "type", "women_led", "status"]], rung="Rung", name="Partner", type="Type", women_led="Women-led", status="Registry status"), hide_index=True, width="stretch")
    st.caption("`women_led` is `to_verify` unless a source says otherwise (org_registry.csv). The channel argument: women-led funds already exist (WPHF, Doria Feminist Fund, Global Fund for Women: Page 5) and midwife/nurse/CHW teams pass the 'no new doctors' filter (docs/WORKFORCE_RETENTION.md).")

st.subheader("Precedents")
st.markdown("- **Model, Gavi co-financing:** 19 countries are now fully self-financing; thresholds are published in advance and predictable ([Gavi](https://www.gavi.org/vaccineswork/how-gavis-pioneering-co-financing-model-ensures-sustainable-vaccine-programmes), [eligibility](https://www.gavi.org/support/sustainability/countries-eligible-for-support/)). Lesson: objective, pre-agreed thresholds.\n"
            "- **Caution, Liberia GEMAP:** co-signature controls were seen as a sovereignty intrusion and worked only with domestic buy-in ([USIP](https://www.usip.org/sites/default/files/PB-May2008-Is-Liberias-Governance.PDF)). Lesson: Lebanese co-design and a published exit date.\n"
            "- **Caution, Afghanistan ARTF:** a single central channel that stopped when the government fell ([SIGAR](https://www.sigar.mil/Portals/147/Files/Reports/Audits-and-Inspections/Evaluation/SIGAR-22-15-IP.pdf)). Lesson: spread control across several rungs and fall back if one fails.\n"
            "- **Community-driven development** delivers local public goods but does not transform governance by itself ([Casey 2018](https://www.gsb.stanford.edu/faculty-research/publications/radical-decentralization-does-community-driven-development-work); [Casey, Glennerster & Miguel 2012](https://www.nber.org/papers/w17012); [Beath, Christia & Enikolopov 2015](https://openknowledge.worldbank.org/handle/10986/22653)). We claim targeting, not institution-building: the ladder is what builds capacity.")
