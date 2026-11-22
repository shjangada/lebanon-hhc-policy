"""Section: pilot design. Start-site scorer, outreach funnel and schedule, illness averted and cost, pilot metrics, stepped rollout, cost and reallocation.
Every input without a Beqaa measurement is a slider labelled as an assumption; sourced defaults are named in the captions."""
import pathlib
import sys

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import io, m6_illness_averted as m6, pilot_flow as pf, start_site as ss  # noqa: E402

PROC = io.PROCESSED
C.header("Pilot design", "Start where setup is cheapest and the need is plain, run a stepped rollout, and measure enough to justify scaling; everything that has no Beqaa measurement is a slider with its break-even.",
         ["cadasters", "population", "facilities"], purpose="Where to start, how often to visit and test, how many cases it could avert and at what cost, and what the pilot must measure.")

st.subheader("Where to start")
with st.expander("Weights and package assumptions (sliders)", expanded=False):
    cols = st.columns(7)
    w = {k: cols[i].slider(k, 0.0, 3.0, 1.0, 0.5, key=f"w_{k}") for i, k in enumerate(ss.CRITERIA)}
    p1, p2, p3 = st.columns(3)
    par = {"n_wells": p1.slider("Wells tested per site", 5, 60, 20, key="pil_wells"), "chw_months": p2.slider("CHW months per site", 1, 12, 6, key="pil_chw"),
           "filter_share": p3.slider("Share of settlement households given a filter", 0.0, 1.0, 1.0, 0.05, key="pil_filt")}
ranked = ss.score(w, par)
top = ranked.head(15)
st.dataframe(C.pretty(top[["start_rank", "cadaster_name", "district", "start_score", "soil", "host", "centre", "settlements", "outreach", "disease", "need", "startup_low_usd", "startup_central_usd", "startup_high_usd"]].round(2),
                      start_rank="Rank", cadaster_name="Cadaster", district="District", start_score="Start score", soil="Soil result", host="Funded host project", centre="Centre access", settlements="Settlements (2016)", outreach="Outreach operator",
                      disease="Water-borne disease", need="Need", startup_low_usd="Startup $ low", startup_central_usd="central", startup_high_usd="high"), hide_index=True, width="stretch")
zero = int(ranked.zero_data_site_central_usd.iloc[0])
st.caption(f"Criteria are 0-1 (soil within 15 km, a page-verified host project = 1, partly verified = 0.5, unverified = 0.25 (host projects are optional), E2SFCA access rank, 2016 settlement population: OLD, outreach operator named, reported hepatitis A + typhoid per 10,000 by district, need score). "
           f"Startup cost counts only missing pieces from sourced unit prices (no Lebanese Cr(VI) price exists: US $40-77); a site with no soil result and no host project would start at about ${zero:,} before kits. Centre capacity is assumed (ranking stable at 200-400 a week).")
cl = ss.clusters(ranked)
st.dataframe(C.pretty(cl.head(6).round(2), cluster_lead="Cluster", district="District", members="Cadasters", n="n", mean_start_score="Mean start score", startup_central_usd="Startup $ (central)", settlement_people_2016="Settlement people (2016)"), hide_index=True, width="stretch")
mp = alt.Chart(ranked).mark_circle(size=60).encode(longitude="lon:Q", latitude="lat:Q", color=alt.Color("start_score:Q", scale=alt.Scale(scheme="viridis"), title="Start score"), tooltip=["cadaster_name", "district", alt.Tooltip("start_score:Q", format=".2f"), "startup_central_usd"])
st.altair_chart(C.wm(mp.properties(), 520, 420), use_container_width=False)
st.caption("The pilot starts where the scorer ranks first. Bouday and Chmestar, the CNRS-L soil villages, are a second wave: they rank lower on centre access and settlement population, but have soil data and REACH HSM 2025 coverage (reported). Change the weights above to see how fragile any one site is.")

stab = ss.rank_stability(ss.criteria())
ps = stab["per_cadaster"].head(10).melt(["cadaster_name", "district"], ["top3_random", "top3_perturb"], "perturbation", "share")
ps["perturbation"] = ps.perturbation.map({"top3_random": "random weights (1,000 draws)", "top3_perturb": "weights +/-25% (1,000 draws)"})
st.altair_chart(C.wm(alt.Chart(ps).mark_bar().encode(y=alt.Y("cadaster_name:N", sort=None, title=None), x=alt.X("share:Q", title="share of draws in the top 3", scale=alt.Scale(domain=[0, 1])), color=alt.Color("perturbation:N", title=None),
                                                       yOffset="perturbation:N", tooltip=["cadaster_name", "district", "perturbation", alt.Tooltip("share:Q", format=".0%")]), 560, 340, scenario=True), use_container_width=False)
sm = stab["summary"]
st.caption(f"Rank stability: with weights perturbed by 25% {sm['perturb']['baseline_first_site']} is first in {sm['perturb']['baseline_first_share_top1']:.0%} of draws, but with fully random weights no single cadaster is stable ({sm['random']['baseline_first_site']} first in {sm['random']['baseline_first_share_top1']:.0%}, top 3 in {sm['random']['baseline_first_share_top3']:.0%}). "
           f"Zahle district holds first place in {sm['district_of_first_site']['random'].get('Zahle', 0):.0%} of random draws and {sm['district_of_first_site']['perturb'].get('Zahle', 0):.0%} of perturbed ones: choose the district and a cluster, not one cadaster.")

st.subheader("Visits, tests and the referral funnel")
site = st.selectbox("Site", top.cadaster_name.tolist(), key="pil_site")
row = top[top.cadaster_name == site].iloc[0]
people = float(row.settlement_people_2016)
c = st.columns(4)
q = {"coverage": c[0].slider("Share of settlement people reached", 0.1, 1.0, 0.5, 0.05, key="pil_cov"), "screened_share": c[1].slider("Screened or tested", 0.1, 1.0, 0.5, 0.05, key="pil_scr"),
     "positive_rate": c[2].slider("Symptomatic / positive", 0.01, 0.5, 0.15, 0.01, key="pil_pos"), "chw_share": c[3].slider("Handled by CHWs (rest = red flags)", 0.3, 1.0, 0.8, 0.05, key="pil_chwsh")}
c2 = st.columns(3)
q["completion"] = c2[0].slider("Referral completed", 0.1, 1.0, 0.5, 0.05, key="pil_comp")
q["spare_share"] = c2[1].slider("Spare share of a centre's capacity", 0.01, 0.5, 0.2, 0.01, key="pil_spare")
q["illness_weeks"] = c2[2].slider("Illness duration (weeks)", 1.0, 6.0, 2.0, 0.5, key="pil_ill")
fn = pf.funnel(people, q)
fch = alt.Chart(fn).mark_bar(color="#2874a6").encode(y=alt.Y("stage:N", sort=None, title=None), x=alt.X("people:Q", title="people per year at this site"), tooltip=["stage", alt.Tooltip("people:Q", format=",.0f")])
st.altair_chart(C.wm(fch, 560, 240, scenario=True), use_container_width=False)
st.caption(f"{site}: {int(people):,} people in 2016 informal settlements (OLD); the shares are assumptions (no Beqaa data). Water positivity can default to 72% for settlement water samples (WaSH Sector, Jul 2026): the only sourced rate here.")
sch = pf.compare_schedules(people, 5, q)
st.dataframe(C.pretty(sch[["chw_interval_weeks", "water_interval_months", "visits_per_month", "chws_needed", "cost_per_month_usd", "red_flags_found_per_month", "cost_per_red_flag_usd", "expected_wait_days", "gdwq_floor_ok"]].round(1),
                      chw_interval_weeks="CHW visit every (weeks)", water_interval_months="Water test every (months)", visits_per_month="Visits / month", chws_needed="CHWs", cost_per_month_usd="Cost / month $",
                      red_flags_found_per_month="Red flags found / month", cost_per_red_flag_usd="$ per red flag", expected_wait_days="Expected wait (days, model)", gdwq_floor_ok="Meets WHO floor (12 samples/yr per supply)"), hide_index=True, width="stretch")
ok = sch[sch.gdwq_floor_ok].sort_values("cost_per_red_flag_usd").iloc[0]
st.caption(f"Cheapest schedule that meets the WHO sampling floor: a CHW visit every {int(ok.chw_interval_weeks)} week(s) with monthly water tests (${ok.cost_per_red_flag_usd:,.0f} per red flag found); quarterly water tests are cheaper but fall below the WHO GDWQ floor of 12 samples a year per supply. "
           "Expected wait is half the visit interval (a model approximation).")
sites, cent, tt = pf.inputs_for(ranked, 8)
ppl = dict(zip(sites.cadaster_id, sites.settlement_people_2016))
rf = {cid: pf.funnel(n, q).set_index("stage").people["red flags referred"] for cid, n in ppl.items()}
rt = pf.route_red_flags(sites, cent, tt, rf, q).merge(ranked[["cadaster_id", "cadaster_name"]], on="cadaster_id").merge(cent[["facility_id", "name"]], on="facility_id", how="left")
st.dataframe(C.pretty(rt[["cadaster_name", "name", "minutes", "red_flags", "added_load_share", "over_limit"]].round(3), cadaster_name="Site", name="Receiving centre (most spare capacity within 30 min)", minutes="Minutes", red_flags="Red flags / yr",
                      added_load_share="Added load (share of yearly capacity)", over_limit="Over the 10% limit"), hide_index=True, width="stretch")
be = pf.break_even_chw_share(sites, cent, tt, ppl, q)
st.caption("Break-even: " + ("no centre exceeds the 10% load limit even if CHWs handle nothing, at these settings (try a smaller spare share)." if be == 0 else f"the minimum CHW-handled share that keeps every centre under the load limit is {be:.0%}."))

st.subheader("Illness averted and cost")
m_ = st.columns(4)
meas = m_[0].selectbox("Measure", list(m6.RR), index=0, key="m6_meas")
cov = m_[1].slider("Share of district population reached", 0.01, 0.5, 0.10, 0.01, key="m6_cov")
tr = m_[2].slider("Transfer of the diarrhoea effect to hepatitis A and typhoid (1 = same RR)", 0.0, 1.0, 1.0, 0.05, key="m6_tr")
vc = m_[3].slider("Primary-care visits per case", 0.5, 3.0, 1.0, 0.5, key="m6_vis")
pop = io.load_dataset("population").df.merge(io.load_dataset("cadasters").df[["cadaster_id", "district"]], on="cadaster_id").groupby("district").population_total.sum()
mm = pd.DataFrame([m6.simulate(d, pop[d] * cov, pop[d], meas if meas in ("filtration", "chlorination") else "filtration", tr, visits_per_case=vc) | {"effect_measure": meas} for d in pop.index])
rr = m6.RR[meas]
st.dataframe(C.pretty(mm[["district", "baseline_cases_per_year", "package_cost_usd", "cases_averted_p05", "cases_averted_median", "cases_averted_p95", "cost_per_case_averted_median", "visits_per_case_to_break_even"]].round(1),
                      district="District", baseline_cases_per_year="Reported cases / yr (2023-25)", package_cost_usd="Package cost $", cases_averted_p05="Averted p05", cases_averted_median="median", cases_averted_p95="p95",
                      cost_per_case_averted_median="$ per case averted", visits_per_case_to_break_even="Visits per case needed to break even"), hide_index=True, width="stretch")
st.caption(f"Relative risk {rr[0]:.2f} [{rr[1]:.2f}-{rr[2]:.2f}] for child diarrhoea in low- and middle-income countries (Wolf 2022): TRANSFERRED evidence, applied to reported hepatitis A + typhoid (notified cases; under-reporting not corrected). "
           "Package prices: 2026 UNICEF catalogue filter per household over an assumed 3-year life (the filtration measure; the chlorination package uses NaDCC tablets; handwashing and sewer connection use the filtration price: no package price is sourced for them), plus CHW months. "
           "The cost per case is for NOTIFIED cases, so it is an UPPER BOUND on the cost per illness averted: most diarrhoea is never notified, and the pilot measures the true figure. Cost and benefit both scale with coverage, so coverage cannot break even: each notified case would have to cost hundreds of primary-care visits; the package pays for itself only through diarrhoea and severity not counted here.")

st.subheader("Unit costs and what a household, a case and a notified case averted cost")
ucs = pd.read_csv(PROC / "unit_costs.csv")
st.dataframe(C.pretty(ucs, item="Item", unit="Unit", low="Low", central="Central", high="High", source="Source", year="Year", lebanon_price="Lebanese price (y/n)"), hide_index=True, width="stretch")
from beqaa import unit_costs as uc  # noqa: E402
cm = uc.cost_metrics(ranked, par)
k3 = st.columns(3)
k3[0].metric(f"Cost per household reached ({cm['top_site']})", f"${cm['cost_per_household_usd']['central']:,.0f}", help=f"low ${cm['cost_per_household_usd']['low']:,.0f}, high ${cm['cost_per_household_usd']['high']:,.0f}; {cm['households_reached']:,.0f} households (2016 settlement people, assumed reach); catalogue filter prices are ex-works")
k3[1].metric("Cost per notified case averted (median)", f"${cm['cost_per_notified_case_averted_usd']['median']:,.0f}", help=f"5th to 95th percentile ${cm['cost_per_notified_case_averted_usd']['p05']:,.0f} to ${cm['cost_per_notified_case_averted_usd']['p95']:,.0f}")
k3[2].metric("Primary-care service", "$20.03", help="K2P/UNICEF 2022; CHW contact about $7 derived from CHW pay and an assumed 10 visits a week; hospital delivery patient share $128-170 and caesarean $255-300 (UNHCR scheme, ended)")
st.caption(cm["note"] + ". Prices without a Lebanese source are marked n; a shipping and markup multiplier is a slider in the cost split below.")

st.subheader("Pilot metrics: evidence for scaling")
kp = pd.read_csv(PROC / "kpis.csv")
st.dataframe(C.pretty(kp.drop(columns=["baseline_source"]), level="Level", baseline="Baseline", target="Target", frequency="Frequency", owner="Owner", splits="Reported split by", escrow_trigger="Escrow trigger"), hide_index=True, width="stretch")
st.caption("A KPI whose baseline says 'none' is set in pilot months 1-3. Targets that are not published values are labelled ASSUMPTION. Three KPIs are the escrow release triggers (referral completion >= 0.40, posts filled >= 0.60, capacity >= 0.30); every KPI is reported split by sex, nationality, registration status and settlement vs village.")

st.subheader("Stepped rollout")
order = top.head(8).cadaster_name.tolist()
grid = pd.DataFrame([{"site": s, "month": m, "state": "pilot" if m >= 2 * i else "comparison"} for i, s in enumerate(order) for m in range(0, 13)])
sr = alt.Chart(grid).mark_rect().encode(x=alt.X("month:O", title="month"), y=alt.Y("site:N", sort=order, title=None), color=alt.Color("state:N", scale=alt.Scale(domain=["pilot", "comparison"], range=["#2874a6", "#d5d8dc"]), title=None))
st.altair_chart(C.wm(sr, 520, 260, scenario=True), use_container_width=False)
st.caption("Illustrative stepped-wedge: one site starts every two months in score order; sites not yet started are the comparison. Randomised or matched ordering and the ESU comparison cazas are to be fixed with the implementer.")

st.subheader("Cost and reallocation")
rf_cost = st.slider("Referral fund per red flag with no payer ($, illustrative)", 0, 400, 150, 10, key="pil_refund",
                    help="no payer is found for unregistered Syrians; the patient share of a normal delivery under the ended UNHCR scheme was $128-170")
mult = st.slider("Shipping and markup multiplier on imported tests and filters (assumption: no Lebanese price or freight rate found)", 1.0, 3.0, 1.0, 0.1, key="pil_mult")
pr = ss._prices()
pr = {k: tuple(x * mult if k in ("cr6", "filter") else x for x in v) for k, v in pr.items()}
n_red = float(fn.set_index("stage").people["red flags referred"])
package = pd.DataFrame([
    {"item": "Water tests (nitrate + chromium, wells)", "type": "new money (a host project can pay it: optional saving)", "usd": par["n_wells"] * (pr["nitrate"][1] + pr["cr_water"][1])},
    {"item": "Soil baseline (if no soil result near)", "type": "new money", "usd": 0.0 if bool(row.soil_sampled_nearby) else 10 * pr["soil"][1]},
    {"item": "Cr(VI) speciation (if a chromium finding is near; US price proxy $40-77, no Lebanese price: assumption A-cost-3)", "type": "new money", "usd": 10 * pr["cr6"][1] if row.soil_hq_high_nearby > 0 else 0.0},
    {"item": "Filters for settlement households (UNICEF catalogue, ex-works)", "type": "new money", "usd": people / 5 * par["filter_share"] * pr["filter"][1]},
    {"item": "CHW months", "type": "redirected where an existing outreach team covers the site, else new", "usd": par["chw_months"] * pr["chw"][1]},
    {"item": "Referral fund for red flags with no payer", "type": "new money", "usd": n_red * rf_cost},
    {"item": "Primary-care visits at $20.03 for handled cases", "type": "redirected (existing subsidised package)", "usd": float(fn.set_index("stage").people["handled by CHWs"]) * 20.03}])
st.dataframe(package.round(0), hide_index=True, width="stretch")
new = package[package.type.str.startswith("new")].usd.sum()
st.caption(f"New money at {site}: about ${new:,.0f} (${new / max(people * q['coverage'], 1):,.1f} per person reached) against the host-project budgets in the rider cards; the rest is redirected. Prices: UNICEF catalogue 2026, AUB 2025, K2P/UNICEF 2022; the Cr(VI) and referral-fund lines are the unverified ones.")
