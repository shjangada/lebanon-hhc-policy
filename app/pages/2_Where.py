"""Page 2: Where should the money go? (destination layer: need, access, exposure, combined priority)"""
import pathlib
import sys

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import io, m1_access, m2_need_score as m2, narrative  # noqa: E402

STATE_COLOR = {"functional": [30, 150, 70, 235], "partial": [235, 150, 20, 235], "closed": [200, 30, 30, 235], "damaged": [110, 10, 10, 235], "unknown": [140, 140, 140, 235]}

c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
env_w = c1.slider("Environment weight in the combined priority", 0.0, 0.6, 0.25, 0.05, key="p2_env",
                  help="Share of the combined priority given to M4 exposure. The official severity index (JIAF) has no environmental indicator; 0.25 = equal weights.")
cr6 = None if c2.toggle("Precautionary: treat all Cr as Cr(VI)", False, key="p2_prec") else c2.slider("Assumed Cr(VI) share of total Cr", 0.0, 1.0, 0.1, 0.05, key="p2_cr6")
d0 = c3.selectbox("Catchment (min)", [15, 30, 60], 1, key="p2_d0")
unk = c4.radio("Facilities without a dated status count as", ["functional", "not functional"], key="p2_unk")

base = C.scored_cached(None, d0, cr6, C.VER)
comb = C.scored_cached(env_w, d0, cr6, C.VER)
panel = C.panel_cached(d0, 1.0 if unk == "functional" else 0.0, C.VER)
tg = m2.exposure_access_targets(comb)
top = comb.nsmallest(10, "rank")
topd = top.district.value_counts()
sent = narrative.page2(list(top.cadaster_name), topd.index[0], float(topd.iloc[0]) / len(top), len(tg))
C.header("Priority areas", sent, ["cadasters", "population", "facilities", "travel_time", "conflict_exposure", "vulnerability", "soil_sites", "official_severity"], purpose="Which cadasters need care most: need, access, exposure and the combined priority, before the war and now.")
if base.attrs.get("skipped_indicators"):
    st.info("Indicators with no data yet (skipped, not filled): " + ", ".join(base.attrs["skipped_indicators"]))

P = panel.merge(base[["cadaster_id", "need_score", "D_environment", "access_deficit", "women_15_49", "pregnant_est"]].rename(columns={"women_15_49": "women_15_49_s"}), on="cadaster_id")
P = P.merge(comb[["cadaster_id", "need_score"]].rename(columns={"need_score": "combined_priority"}), on="cadaster_id")
P["safe_birth_need"] = P.women_15_49 * P.access_deficit * (1 + P.D_environment)
METRICS = {"Combined priority (need + exposure weight)": ("combined_priority", False, "need"), "Need Score (equal domain weights)": ("need_score", False, "need"),
           "Environmental exposure (M4 tier score)": ("D_environment", False, "need"), "E2SFCA access (capacity per 1,000 women)": ("access", True, "access"),
           "Facilities in catchment per 10k people": ("facilities_per_10k", True, "access"), "Travel time to nearest PHC (min)": ("min_phc", False, "access"),
           "Travel time to nearest hospital (min)": ("min_hospital", False, "access"), "Beyond 30 min of a PHC": ("beyond_30_phc", False, "access"),
           "Safe-birth need: women 15-49 × access gap × exposure (women lens)": ("safe_birth_need", False, "women")}
opts = list(METRICS) if C.women_lens() else [m for m in METRICS if METRICS[m][2] != "women"]
default = opts[-1] if C.women_lens() else opts[0]
a, b = st.columns([3, 2])
metric = a.selectbox("Metric (map and ranked chart share it)", opts, index=opts.index(default), key=f"p2_metric_{C.women_lens()}")
period = b.radio("Period (access metrics)", ["Pre-war baseline (2023)", "Current (latest dated status)"], index=1, key="p2_period", horizontal=True)
k, higher_good, kind = METRICS[metric]
scn = "prewar" if period.startswith("Pre-war") else "current"
col = f"{k}_{scn}" if kind == "access" else k
if kind != "access":
    st.caption("Pre-war vs current applies to the access metrics; need, exposure and safe-birth metrics use current access.")
vals = P[col].astype(float)
rng = max(vals.max() - vals.min(), 1e-9)
P["_bad"] = ((1 - (vals - vals.min()) / rng) if higher_good else ((vals - vals.min()) / rng)).fillna(0)
P["_val"] = vals.round(3)
P["_r"], P["_g"], P["_rad"] = (255 * P._bad).astype(int), (190 * (1 - P._bad)).astype(int), P.population_total.pow(0.5) * 22

picked = None
try:
    bar, mp_ = st.session_state.get("p2_bar"), st.session_state.get("p2_map")
    if bar and bar["selection"]["pick"]:
        picked = bar["selection"]["pick"][0].get("cadaster_name")
    elif mp_ and mp_["selection"]["objects"]:
        for objs in mp_["selection"]["objects"].values():
            if objs and objs[0].get("cadaster_name"):
                picked = objs[0]["cadaster_name"]
                break
except Exception:
    picked = None

layers = [pdk.Layer("ScatterplotLayer", P, id="cad", get_position=["lon", "lat"], get_radius="_rad", get_fill_color=["_r", "_g", 40, 170], pickable=True, stroked=True, get_line_color=[255, 255, 255, 120], line_width_min_pixels=1)]
if picked:
    layers.append(pdk.Layer("ScatterplotLayer", P[P.cadaster_name == picked], get_position=["lon", "lat"], get_radius="_rad", filled=False, stroked=True, get_line_color=[0, 0, 0, 255], line_width_min_pixels=4))
fac = io.load_dataset("facilities").df.copy()
fac["state"] = m1_access.facility_state(fac)
fac["_c"] = fac.state.map(STATE_COLOR)
fac["_rad"] = np.where(fac["type"] == "mobile", 1800, 1100)
fac["_label"] = fac.name.astype(str) + " | " + fac.state.map(m1_access.STATE_LABELS) + " | " + fac.get("status_date", pd.Series("", index=fac.index)).fillna("").astype(str).replace("", "no date")
layers.append(pdk.Layer("ScatterplotLayer", fac, id="fac", get_position=["lon", "lat"], get_radius="_rad", get_fill_color="_c", pickable=True, stroked=True, get_line_color=[0, 0, 0, 255], line_width_min_pixels=1))
if st.session_state.get("p2_soil", True):
    from beqaa import m4_exposure
    s_ = m4_exposure.screen_sites(cr6_for_tier=cr6).dropna(subset=["lat"]).assign(_c=lambda d: d.tier.map({0: [120, 120, 120, 220], 1: [240, 190, 0, 230], 2: [130, 0, 160, 240]}))
    layers.append(pdk.Layer("ScatterplotLayer", s_, get_position=["lon", "lat"], get_radius=2300, get_fill_color="_c", stroked=True, get_line_color=[255, 255, 255, 255]))
if C.IS_MOCK:
    layers.append(pdk.Layer("TextLayer", pd.DataFrame({"lat": [P.lat.mean()], "lon": [P.lon.mean()], "t": ["MOCK DATA"]}), get_position=["lon", "lat"], get_text="t", get_size=60, get_color=[220, 0, 0, 120]))
ml, mr = st.columns([3, 2])
with ml:
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=P.lat.mean(), longitude=P.lon.mean(), zoom=8.2), tooltip={"text": "{cadaster_name}\n{_val}\n{_label}"}),
                    on_select="rerun", selection_mode="single-object", key="p2_map")
    st.markdown("<span style='font-size:0.85rem'>Cadaster colour: green = better, red = worse. Facilities: <span style='color:#1e9646'>●</span> functional · <span style='color:#eb9614'>●</span> partial · "
                "<span style='color:#c81e1e'>●</span> closed · <span style='color:#6e0a0a'>●</span> damaged · <span style='color:#8c8c8c'>●</span> unknown (no dated source). Soil: purple = tier 2 (plausible pathway).</span>", unsafe_allow_html=True)
    st.checkbox("Overlay soil results (M4 exposure tier)", True, key="p2_soil")
with mr:
    topn = P.sort_values("_bad", ascending=False).head(15)
    ch = alt.Chart(topn).encode(y=alt.Y("cadaster_name:N", sort="-x", title=None), x=alt.X("_val:Q", title=metric.split(" (")[0].split(":")[0]),
                                color=alt.condition(alt.datum.cadaster_name == (picked or ""), alt.value("#111"), alt.value("#c0392b")), tooltip=["cadaster_name", "district", "_val"])
    st.altair_chart(C.wm(ch.mark_bar().add_params(alt.selection_point(name="pick", fields=["cadaster_name"])), 420, 420), on_select="rerun", key="p2_bar")
    st.caption("The fifteen cadasters with the worst value for the chosen metric. Click a bar or a map dot to highlight it in both.")

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
    st.caption("Ten cadasters that lost the most access since the pre-war baseline. Facilities come from OSM (about 15% of MoPH-network PHCs), so levels are understated; the ranking of losses is what to read.")
with g2:
    sc = P.assign(target=(P.D_environment >= 0.33) & (P.access_deficit >= 0.5))
    pts = alt.Chart(sc).mark_circle(opacity=0.7).encode(x=alt.X("access_deficit:Q", title="access deficit (share of pre-war access lost)", scale=alt.Scale(domain=[0, 1])),
                                                       y=alt.Y("D_environment:Q", title="environmental exposure (M4 tier score)", scale=alt.Scale(domain=[0, 1])), size=alt.Size("population_total:Q", legend=None, scale=alt.Scale(range=[20, 400])),
                                                       color=alt.Color("district:N", title="District"), stroke=alt.condition("datum.target", alt.value("black"), alt.value(None)), tooltip=["cadaster_name", "district", alt.Tooltip("access_deficit:Q", format=".2f"), alt.Tooltip("D_environment:Q", format=".2f")])
    rules = alt.Chart(pd.DataFrame({"x": [0.5], "y": [0.33]}))
    quad = rules.mark_rule(strokeDash=[4, 4], color="#555").encode(x="x:Q") + rules.mark_rule(strokeDash=[4, 4], color="#555").encode(y="y:Q")
    st.altair_chart(C.wm(pts + quad, 400, 340), use_container_width=False)
    st.caption("Top-right quadrant (outlined) = high exposure and low access: the core target list below. Exposure only exists where soil was sampled, so empty space is 'not measured', not 'safe'.")
d1, d2 = st.columns(2)
with d1:
    box = alt.Chart(comb).mark_boxplot(extent="min-max").encode(x=alt.X("district:N", title=None), y=alt.Y("need_score:Q", title="combined priority"), color=alt.Color("district:N", legend=None))
    st.altair_chart(C.wm(box, 400, 280), use_container_width=False)
    st.caption("Combined priority by district: the spread inside each district is what district-level official severity cannot show.")
with d2:
    from beqaa import m4_exposure
    tor = m4_exposure.tornado()
    tb = alt.Chart(tor).mark_bar(color="#8e44ad").encode(y=alt.Y("driver:N", sort="-x", title=None), x=alt.X("swing:Q", title="swing in hazard quotient"), tooltip=["driver", "evidence_that_would_change_response"])
    st.altair_chart(C.wm(tb, 400, 280), use_container_width=False)
    st.caption("What would change the exposure response: " + tor.iloc[0].evidence_that_would_change_response + " (largest swing). Cr(VI) speciation is the cheapest test that settles the key uncertainty.")

st.subheader("Core target list: high exposure and low access")
st.dataframe(C.pretty(tg[["cadaster_name", "district", "D_environment", "access_deficit", "need_score"]].round(2), cadaster_name="Cadaster", district="District", D_environment="Exposure (M4 tier score)",
                      access_deficit="Access deficit", need_score="Need score"), hide_index=True, width="stretch")
st.caption("Exposure >= 0.33 and access deficit >= 50% (assumptions). Exposure tiers are screening-level (rung a/b), never demonstrated harm. "
           "The environment domain only sees the villages with a published soil result; a cadaster nobody sampled scores 0 exposure, which is not evidence of safety.")

sev = m2.compare_official(comb)
with st.expander("Comparison with the official district severity (JIAF / health / FSA)"):
    st.dataframe(sev[0].round(2), hide_index=True, width="stretch")
    st.caption("Our district ranking vs the official severity classes (LRP Addendum, hand-transcribed). Disagreements show where cadaster-level need and exposure differ from the district class. FSA composite is printed for Severity-4 districts only.")
vo = m1_access.validate_vs_official(panel)
with st.expander(f"Validation: access ranking vs official health severity (Spearman ρ = {vo['rho']:.2f})"):
    st.dataframe(vo["table"].round(2), hide_index=True, width="stretch")
with st.expander("Layer dates and sources (every layer is date-stamped)"):
    st.dataframe(m1_access.layer_dates(), hide_index=True, width="stretch")
d_sum = m1_access.district_summary(panel)
with st.expander("Before the war vs now, by district"):
    st.dataframe(d_sum.round(2), hide_index=True, width="stretch")
    st.caption("Thresholds (30 min to a PHC, 60 min to a hospital) are assumptions. Facilities come from OSM (about 15% of the MoPH-network PHCs), so access is understated.")
if C.women_lens():
    st.caption("Women lens: safe-birth need = women 15-49 × access deficit × (1 + exposure). Women are the delivery channel and the outcome (safe pregnancy and birth), not the most needy group overall: women and girls are about 53% of remaining IDPs, roughly proportional.")
