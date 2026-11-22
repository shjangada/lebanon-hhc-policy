"""Appendix charts: secondary views moved off the main dashboard because they are not needed for the argument (goals and assumptions) but are kept for reference.
Each has its caption. Nothing here is a headline number."""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import allocation, io, start_site as ss, theme_kpi  # noqa: E402

PROC = io.PROCESSED
st.title("Appendix charts")
st.caption("Secondary charts moved here from the main dashboard. They are context or rest on placeholder inputs, so the argument does not depend on them: centres per 10,000, the Flash Appeal funding gap, access lost since the pre-war baseline, "
           "exposure vs access, the district escrow table, the allocation test arms, the stepped-rollout grid and the policy regret bars. Labels and caveats are unchanged.")

st.header("Context")
cad = io.load_dataset("cadasters").df
pop = io.load_dataset("population").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
fac = io.load_dataset("facilities").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
byd = pop.groupby("district").population_total.sum()
phc = fac[fac.type == "PHC"].groupby("district").size().reindex(byd.index).fillna(0)
hosp = fac[fac.type == "hospital_hub"].groupby("district").size().reindex(byd.index).fillna(0)

st.subheader("Health access: centres per 10,000")
h = pd.DataFrame({"PHC": phc / byd * 1e4, "hospital": hosp / byd * 1e4}).reset_index().melt("district", var_name="type", value_name="per_10k")
ch2 = alt.Chart(h).mark_bar().encode(y=alt.Y("district:N", sort="-x", title=None), x=alt.X("per_10k:Q", title="facilities per 10,000 people"), color=alt.Color("type:N", title=None),
                                     tooltip=["district", "type", alt.Tooltip("per_10k:Q", format=".2f")])
st.altair_chart(C.wm(ch2, 400, 220), use_container_width=False)
st.caption("MoPH facility list (centres at village positions). Counts ignore distance and size: the access model on the next sections handles both.")

req = pd.read_csv(PROC / "funding_requirements.csv") if (PROC / "funding_requirements.csv").exists() else None
st.subheader("Flash Appeal 2026: funded vs required, by sector")
if req is None:
    st.info("Data pending: run `make ingest` (FTS requirements).")
else:
    cl = req[(req.plan == "Lebanon Flash Appeal 2026") & (req.cluster != "All clusters (plan total)")].copy()
    cl["gap_usd"] = (cl.requirements_usd - cl.funding_usd).clip(lower=0)
    long = cl.melt(["cluster", "percent_funded"], ["funding_usd", "gap_usd"], "part", "usd")
    long["part"] = long.part.map({"funding_usd": "Funded", "gap_usd": "Gap"})
    order = cl.sort_values("percent_funded").cluster.tolist()
    ch3 = alt.Chart(long).mark_bar().encode(y=alt.Y("cluster:N", sort=order, title=None), x=alt.X("usd:Q", title="USD"), color=alt.Color("part:N", title=None, scale=alt.Scale(domain=["Funded", "Gap"], range=["#2e86c1", "#c0392b"])),
                                            tooltip=["cluster", "part", alt.Tooltip("usd:Q", format=",.0f"), "percent_funded"])
    st.altair_chart(C.wm(ch3, 400, 280), use_container_width=False)
    st.caption("Source: OCHA FTS (real). The Health cluster is 60% funded; sectors that shape recovery (livelihoods, WASH, social stability) are far less funded.")

st.header("Access and exposure")
base = C.scored_cached(None, 30, 0.1, C.VER)
comb = C.scored_cached(0.25, 30, 0.1, C.VER)
panel = C.panel_cached(30, 1.0, C.VER)
P = panel.merge(base[["cadaster_id", "need_score", "D_environment", "access_deficit", "women_15_49", "pregnant_est"]].rename(columns={"women_15_49": "women_15_49_s"}), on="cadaster_id")
P = P.merge(comb[["cadaster_id", "need_score"]].rename(columns={"need_score": "combined_priority"}), on="cadaster_id")

st.subheader("Where access was lost, and where it overlaps with exposure")
g1, g2 = st.columns(2)
with g1:
    lost = P.sort_values("access_lost_pct", ascending=False).head(10)
    long = lost.melt("cadaster_name", ["access_prewar", "access_current"], "period", "access")
    long["period"] = long.period.map({"access_prewar": "Pre-war", "access_current": "Now"})
    ch = alt.Chart(long).mark_bar().encode(y=alt.Y("cadaster_name:N", sort=lost.cadaster_name.tolist(), title=None), x=alt.X("access:Q", title="capacity per 1,000 women (E2SFCA)"),
                                           color=alt.Color("period:N", title=None, scale=alt.Scale(domain=["Pre-war", "Now"], range=["#aab7b8", "#c0392b"])), yOffset="period:N",
                                           tooltip=["cadaster_name", "period", alt.Tooltip("access:Q", format=".1f")])
    st.altair_chart(C.wm(ch, 400, 340), use_container_width=False)
    st.caption("Ten cadasters that lost the most access since the pre-war baseline. Facilities are the MoPH list (PHCCs located at village centroids), and only 4 have a dated 2026 status, so read the ranking of losses, not the levels.")
with g2:
    sc = P.assign(target=(P.D_environment >= 0.33) & (P.access_deficit >= 0.5))
    pts = alt.Chart(sc).mark_circle(opacity=0.7).encode(x=alt.X("access_deficit:Q", title="access deficit (share of pre-war access lost)", scale=alt.Scale(domain=[0, 1])),
                                                       y=alt.Y("D_environment:Q", title="environmental exposure (M4 tier score)", scale=alt.Scale(domain=[0, 1])), size=alt.Size("population_total:Q", legend=None, scale=alt.Scale(range=[20, 400])),
                                                       color=alt.Color("district:N", title="District"), stroke=alt.condition("datum.target", alt.value("black"), alt.value(None)), tooltip=["cadaster_name", "district", alt.Tooltip("access_deficit:Q", format=".2f"), alt.Tooltip("D_environment:Q", format=".2f")])
    rules = alt.Chart(pd.DataFrame({"x": [0.5], "y": [0.33]}))
    quad = rules.mark_rule(strokeDash=[4, 4], color="#555").encode(x="x:Q") + rules.mark_rule(strokeDash=[4, 4], color="#555").encode(y="y:Q")
    st.altair_chart(C.wm(pts + quad, 400, 340), use_container_width=False)
    st.caption("Top-right quadrant (outlined) = high exposure and low access: the core target list below. Exposure only exists where soil was sampled, so empty space is 'not measured', not 'safe'.")

st.header("Control of the money")
scored = C.scored_cached(None, 30, 0.1, C.VER)
_path, sched = theme_kpi._escrow_path("baseline", scored)
yr = None

st.subheader("Who controls money in each district" + (" (all years)" if yr is None else f" ({yr})"))
d = sched if yr is None else sched[sched.year == yr]
dd = d.groupby("district").agg(towns=("cadaster_id", "nunique"), released_usd=("released_usd", "sum"), held_usd=("held_in_escrow_usd", "sum"),
                               rung=("administered_by_floor", lambda x: x.value_counts().index[0]), capacity_index=("admin_capacity_index", "mean")).reset_index()
st.dataframe(C.pretty(dd.round(2), district="District", towns="Towns in window", released_usd="Released $", held_usd="Held $", rung="Rung holding the need floor (most common)", capacity_index="Capacity index"),
             hide_index=True, width="stretch")
st.caption("Only districts that contain priority towns appear. Capacity index = the national anchor applied to every district (SC01, World Bank WGI Government Effectiveness 29.9/100 for 2025).")


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
st.caption("These are PILOT TEST ARMS, not results: the community arm's effect rests on assumptions (local-fit 1.0-1.3, capture 10-40%, placeholder community priorities), and the model does not value legitimacy or sustainability. "
           "Community-driven development delivers local public goods but does not transform governance by itself (see precedents), so the claim is better targeting, not institution-building. Breakpoints are on the Resilience page.")


st.header("Pilot and robustness")
top = ss.score().head(8)

st.subheader("Stepped rollout")
order = top.head(8).cadaster_name.tolist()
grid = pd.DataFrame([{"site": s, "month": m, "state": "pilot" if m >= 2 * i else "comparison"} for i, s in enumerate(order) for m in range(0, 13)])
sr = alt.Chart(grid).mark_rect().encode(x=alt.X("month:O", title="month"), y=alt.Y("site:N", sort=order, title=None), color=alt.Color("state:N", scale=alt.Scale(domain=["pilot", "comparison"], range=["#2874a6", "#d5d8dc"]), title=None))
st.altair_chart(C.wm(sr, 520, 260, scenario=True), use_container_width=False)
st.caption("Illustrative stepped-wedge: one site starts every two months in score order; sites not yet started are the comparison. Randomised or matched ordering and the ESU comparison cazas are to be fixed with the implementer.")


RB = C.robust_cached(300, C.VER)
pol = RB["regret"]

st.subheader("Which allocation policy: maximum regret")
rg = alt.Chart(pol["summary"]).mark_bar().encode(y=alt.Y("policy:N", sort="x", title=None), x=alt.X("max_regret:Q", title="maximum regret (pathways lost vs the best policy in that world)"),
                                                  color=alt.condition(alt.datum.policy == pol["minimax_policy"], alt.value("#27ae60"), alt.value("#aab7b8")), tooltip=["policy", alt.Tooltip("max_regret:Q", format=".0f"), alt.Tooltip("mean_regret:Q", format=".0f")])
st.altair_chart(C.wm(rg, 560, 200), use_container_width=False)
st.caption("The green policy has the smallest worst-case regret. Placeholder costs, effects and community priorities drive the gaps.")
