"""Page 4: Does the money keep reaching people when things go wrong?"""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import narrative, robustness, theme_kpi  # noqa: E402


n = st.session_state.get("p4_n", 300)
RB = C.robust_cached(n, C.VER)
rk, pol = RB["rank"], RB["regret"]
core = rk["core"]
C.header("Resilience", narrative.page4(len(core), rk["top_k"], rk["threshold"], pol["minimax_policy"]),
         ["cadasters", "population", "facilities", "travel_time", "conflict_exposure", "governance_capacity", "interventions"], purpose="Which recommendations survive uncertain assumptions and six stress scenarios; only the robust core is recommended.")
st.caption("Scenarios: S1 renewed escalation, S2 funding −30/−50/−70%, S3 power collapse, S4 staff loss, S5 capacity stall, S6 worst-case Cr(VI). Parameter ranges and their sources: data/params/uncertainty.yaml. "
           "The ranking inputs are real (cadasters, population, IPC, LRP incidents, soil, MoPH facilities). The allocation and regret comparisons use placeholder community priorities, five placeholder option costs and mostly placeholder effect sizes: read them as a comparison of options and break-evens, not a forecast.")

st.subheader("Recommended: only the robust core")
if core:
    st.success("Recommended target cadasters (top-%d in at least %.0f%% of draws and in every scenario): %s" % (rk["top_k"], 100 * rk["threshold"], ", ".join(core)))
else:
    st.error("No cadaster is robustly in the top %d: nothing is recommended on this evidence. %s" % (rk["top_k"], rk["warning"] or ""))
pc = rk["per_cadaster"].head(12)
cols = [c for c in pc.columns if c.startswith("p_top_") and c != "p_top_overall"]
st.dataframe(pc[["cadaster_name", "p_top_overall"] + cols + ["rank_p05", "rank_p95", "core"]].rename(columns={c: c.replace("p_top_", "") for c in cols}).round(2).rename(
    columns={"cadaster_name": "Cadaster", "p_top_overall": "overall", "rank_p05": "rank 5%", "rank_p95": "rank 95%", "core": "recommended (core)"}), hide_index=True, width="stretch")
st.caption("Share of random draws in which each cadaster is in the top-k. Cadasters outside the core are not recommended, however high they rank in the baseline.")

hm = pc.melt("cadaster_name", [c for c in pc.columns if c.startswith("p_top_") and c != "p_top_overall"], "scenario", "p")
hm["scenario"] = hm.scenario.str.replace("p_top_", "").str.replace("_", " ")
heat = alt.Chart(hm).mark_rect().encode(x=alt.X("scenario:N", title=None, axis=alt.Axis(labelAngle=-35)), y=alt.Y("cadaster_name:N", title=None, sort=pc.cadaster_name.tolist()),
                                        color=alt.Color("p:Q", title="P(top-k)", scale=alt.Scale(domain=[0, 1], scheme="redyellowgreen")), tooltip=["cadaster_name", "scenario", alt.Tooltip("p:Q", format=".2f")])
txt = alt.Chart(hm).mark_text(fontSize=10).encode(x="scenario:N", y=alt.Y("cadaster_name:N", sort=pc.cadaster_name.tolist()), text=alt.Text("p:Q", format=".1f"))
st.altair_chart(C.wm(heat + txt, 560, 360), use_container_width=False)
st.caption("Each cell: share of random draws in which the cadaster is in the top-k under that scenario. A cadaster is recommended only if every cell is high.")

st.subheader("What each scenario does to the money and the target set")
mp = {"baseline": ("baseline", "baseline"), "S1_escalation": ("S1_escalation", "S1_escalation"), "S2_funding_shock": ("S2_funding_shock", "S2_funding_shock"),
      "S3_power_collapse": ("S3_power_collapse", None), "S4_staff_loss": ("S4_staff_loss", None), "S5_capacity_stall": ("S5_capacity_stall", "S5_capacity_stall"), "S6_worst_case_contamination": ("S6_worst_case_contamination", None)}
kt = theme_kpi.kpi_table(scored=RB["scored"])
k30 = kt[kt.year == 2030].set_index("scenario").local_control_share
esc = RB["escrow"].set_index("world")
esc_map = {"baseline": "baseline", "S2_funding_shock": "S2 funding -50%", "S5_capacity_stall": "S5 capacity stall (0 gain/yr)", "S1_escalation": "S1 escalation from 2028"}
bs = pol["by_scenario"]
best = pol["minimax_policy"]
rows = []
for sid, (rsid, ksid) in mp.items():
    t = rk["scenarios"].set_index("scenario").loc[sid if sid != "baseline" else "baseline"]
    pk = pc  # core hold: the lowest P(top-k) among core cadasters in this scenario
    corehold = float(rk["per_cadaster"][rk["per_cadaster"].core][f"p_top_{sid}"].min()) if core else float("nan")
    rows.append({"Scenario": sid.replace("_", " "), "Kendall τ vs baseline": round(float(t.kendall_tau_vs_baseline), 2), f"Top-{rk['top_k']} kept": int(t.top_k_retained),
                 "Core holds (min P(top-k))": None if pd.isna(corehold) else round(corehold, 2),
                 "Money released to towns ($)": round(float(esc.loc[esc_map[sid], "released_usd"]), 0) if sid in esc_map else None,
                 "Held in escrow ($)": round(float(esc.loc[esc_map[sid], "held_in_escrow_usd"]), 0) if sid in esc_map else None,
                 "Local control 2030": round(float(k30.get(ksid, float("nan"))), 2) if ksid else None,
                 f"Pathways ({best.replace('_', ' ')})": round(float(bs[(bs.scenario == sid) & (bs.policy == best)].mean_value.iloc[0]), 0)})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
st.caption("Money columns exist where the escrow model has the scenario (baseline, S1, S2, S5); S3, S4 and S6 act on access, capacity and exposure rather than on the escrow, so those cells are empty, not zero. Pathways = mean extra completed care pathways of the minimax policy.")

st.subheader("Graceful degradation of the escrow")
deg = RB["escrow"]
st.dataframe(C.pretty(deg.round(2), world="World", pool_usd="Pool $", released_usd="Released $", held_in_escrow_usd="Held $", conserved="Money conserved",
                      share_lebanese_managed_2030="Lebanese-managed 2030", towns_with_tranche_held="Towns with tranche held", need_floor_still_paid="Need floor paid", n_warnings="Warnings"),
             hide_index=True, width="stretch")
st.caption("The need floor is still paid and money is conserved in every world: under funding shock, capacity stall and escalation the capacity tranche is held (or the ladder falls back to an international fiduciary), rather than the mechanism collapsing.")

st.subheader("Which allocation policy: regret across scenarios")
st.dataframe(C.pretty(pol["summary"][["policy", "mean_value", "mean_regret", "max_regret", "minimax_rank"]].round(0), policy="Policy", mean_value="Mean pathways", mean_regret="Mean regret",
                      max_regret="Max regret", minimax_rank="Minimax rank"), hide_index=True, width="stretch")
st.caption("Allocations are fixed in advance on baseline data and judged in every world; prefer the smallest maximum regret, not the best average. Policies: top-down (by need), per capita, community-decided, existing allocation (follows current capacity). Escrow is evaluated above as a mechanism, not as a spending policy.")

st.caption("The regret chart (maximum regret by policy) is in the **Appendix charts** tab; the table above has the numbers.")

st.subheader("Break-evens: what has to be true")
from beqaa import breakeven  # noqa: E402
BE = breakeven.run(RB["scored"])
alloc = BE["allocation"]
alloc = alloc[alloc.priorities.str.startswith("community picks") | (alloc.parameter == "alignment")]
st.dataframe(C.pretty(alloc[["comparison", "reading"]], comparison="Comparison", reading="Break-even (everything else at the centre of its range)"), hide_index=True, width="stretch")
st.caption("Status quo = money follows current facility capacity. With community priorities as modelled (a placeholder) the community arm loses to both alternatives at every tested value; the rows above give the best case, where communities choose the most cost-effective option. "
           "Capture, local fit and committee cost have no published Lebanon value, so these thresholds are the result, not a forecast.")
ex = BE["exposure"]
st.dataframe(C.pretty(ex[["site_name", "value_mg_kg", "cr6_share_at_hq1"]].assign(cr6_share_at_hq1=lambda d: d.cr6_share_at_hq1.map("{:.2%}".format)), site_name="Soil site", value_mg_kg="Total Cr (mg/kg)", cr6_share_at_hq1="Cr(VI) share of total Cr at which the child hazard quotient reaches 1"), hide_index=True, width="stretch")
st.caption(f"Exposure break-even: the screening response flips from monitor to protective action if Cr(VI) is above {ex.cr6_share_at_hq1.min():.2%} to {ex.cr6_share_at_hq1.max():.2%} of total chromium, depending on the site (child, soil plus crop pathway). Nobody has measured the share in Beqaa. The only published ultramafic-soil data found (Greece, not Beqaa; abstract only) cap Cr(VI) at 0.53% of total Cr, which sits inside this window: a Cr(VI) speciation test is decisive, and it is the cheapest test that settles the response.")
st.dataframe(C.pretty(BE["escrow"][["threshold", "release_needs", "current_assumed", "reading"]], threshold="Release threshold", release_needs="Needs", current_assumed="Assumed now", reading="Reading"), hide_index=True, width="stretch")
with st.expander("Scenario definitions and sources"):
    st.dataframe(pd.DataFrame([{"scenario": v["label"], "what changes": ", ".join(f"{k}={val}" for k, val in v.items() if k not in ("label", "status")), "status": v["status"]} for v in RB["unc"]["scenarios"].values()]),
                 hide_index=True, width="stretch")
    st.slider("Draws per scenario (preview; the pipeline uses 1,000)", 100, 1000, 300, 100, key="p4_n")
