"""Page 4: Does the money keep reaching people when things go wrong?"""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import narrative, robustness, theme_kpi  # noqa: E402


@st.cache_data
def run(n, ver):
    return robustness.run_all(n=n)


n = st.session_state.get("p4_n", 300)
RB = run(n, C.VER)
rk, pol = RB["rank"], RB["regret"]
core = rk["core"]
C.header("Does the money keep reaching people when things go wrong?", narrative.page4(len(core), rk["top_k"], rk["threshold"], pol["minimax_policy"]),
         ["cadasters", "population", "facilities", "travel_time", "conflict_exposure", "governance_capacity", "interventions"])
st.caption("Scenarios: S1 renewed escalation, S2 funding −30/−50/−70%, S3 power collapse, S4 staff loss, S5 capacity stall, S6 worst-case Cr(VI). Parameter ranges and their sources: data/params/uncertainty.yaml. "
           "Scenario effects, costs and community priorities are assumptions or mock; the method is what carries over to real data.")

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

st.subheader("Breakpoints: where does the recommendation flip?")
st.dataframe(C.pretty(RB["breakpoints"][["priorities", "assumption", "reading"]], priorities="Community priorities", assumption="Assumption", reading="Reading"), hide_index=True, width="stretch")
with st.expander("Scenario definitions and sources"):
    st.dataframe(pd.DataFrame([{"scenario": v["label"], "what changes": ", ".join(f"{k}={val}" for k, val in v.items() if k not in ("label", "status")), "status": v["status"]} for v in RB["unc"]["scenarios"].values()]),
                 hide_index=True, width="stretch")
    st.slider("Draws per scenario (preview; the pipeline uses 1,000)", 100, 1000, 300, 100, key="p4_n")
