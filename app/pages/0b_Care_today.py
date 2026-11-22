"""Section: how care works today, and where pollution makes people sick (reported waterborne disease)."""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import io  # noqa: E402

PROC = io.PROCESSED
pay = pd.read_csv(PROC / "referral_payers.csv")
out = pd.read_csv(PROC / "outreach.csv")
wash = pd.read_csv(PROC / "wash.csv")
esu_d = pd.read_csv(PROC / "esu_by_district.csv")
esu_a = pd.read_csv(PROC / "esu_by_age_sex.csv")
pop = io.load_dataset("population").df.merge(io.load_dataset("cadasters").df[["cadaster_id", "district"]], on="cadaster_id").groupby("district").population_total.sum()

C.header("Care and disease today", "Care is available to everyone at primary level, but nothing connects an environmental finding to a clinic, referrals are not tracked, and no payer is found for unregistered Syrians in hospital since UNHCR's cut on 1 Dec 2025.",
         ["population", "facilities"], purpose="How a sick person reaches care, who pays at each step, what is missing, and which water-borne diseases are reported in the five districts.")

st.subheader("How it works today")
dot = '''digraph G { rankdir=LR; node [shape=box, style=rounded, fontsize=10]; edge [fontsize=8];
 sick [label="Sick or exposed"]; pharm [label="Pharmacy / self-care"]; phc [label="Primary-care centre or mobile unit\\n(MoPH network: open to all nationalities)"]; hosp [label="Hospital"];
 env [label="Soil / water finding", shape=note, color=red, fontcolor=red]; track [label="Referral completion:\\nnot tracked", color=red, fontcolor=red, style="rounded,dashed"];
 sick -> pharm; sick -> phc; pharm -> phc;
 phc -> hosp [label="Lebanese: MoPH covers 100% at government hospitals in the war period (80% routine)"];
 phc -> hosp [label="Registered Syrians: UNHCR hospital support ENDED 1 Dec 2025", color=red, fontcolor=red];
 phc -> hosp [label="Unregistered Syrians: no payer found", color=red, fontcolor=red, style=dashed];
 env -> phc [label="no trigger", color=red, fontcolor=red, style=dashed];
 hosp -> track [color=red, style=dashed]; }'''
st.graphviz_chart(dot)
st.caption("Fees at the primary level: LPSP-subsidised centres $2 (GP) or $3.5 (specialist); partner-supported centres charge registered Syrians LBP 150,000-900,000 per consultation; vaccines and acute medicines free. Red = missing or ended links. "
           "Source: processed/referral_payers.csv (MoPH, UNHCR, MSF, Annahar, LBC; payer for unregistered Syrians NOT FOUND in 2025-2026 sources).")
with st.expander("Payers by group and level of care (every row has a source URL in the file)"):
    st.dataframe(pay[["population_group", "level_of_care", "payer", "fee_or_coverage", "date"]], hide_index=True, width="stretch")

st.subheader("Outreach today")
o = out.copy()
o["frequency"] = o.frequency.fillna("not published").replace({"not reported": "not published"})
st.dataframe(C.pretty(o[["org", "district", "service", "units", "frequency"]], org="Organisation", district="Where", service="Service", units="Units", frequency="Visit frequency"), hide_index=True, width="stretch")
st.caption("No actor publishes how often mobile units or outreach teams visit a site (Amel revises its schedule weekly; MSF, UNICEF and MoPH report none). The pilot measures it.")

st.subheader("What can be redirected (no new numbers)")
st.dataframe(pd.DataFrame([
    {"existing resource": "Mobile-unit routes", "what it is today": "Amel: 14 mobile units reaching 65 sites; MSF mobile teams across the Beqaa", "redirect": "add the rider's testing and referral stop to existing routes"},
    {"existing resource": "WASH partner visits", "what it is today": "112,629 people in tented settlements reached nationally, Jan-Sep 2026 (WaSH Sector)", "redirect": "add nitrate, chromium and chlorine tests to existing water-quality visits"},
    {"existing resource": "Outreach volunteers", "what it is today": "UNHCR outreach programme: no 2025-2026 source found", "redirect": "none until found"},
    {"existing resource": "Host-project safety lines", "what it is today": "funded water, irrigation and cooperative projects (see Funding today)", "redirect": "pay the rider from the project's own safeguard or OHS line where allowed"},
    {"existing resource": "Subsidised primary-care package", "what it is today": "LPSP: $2 / $3.5 per visit; network open to all", "redirect": "treat and refer through the existing package"}]), hide_index=True, width="stretch")

st.subheader("Pollution makes people sick: reported water-borne disease")
dis = st.selectbox("Disease", ["Hepatitis A", "Typhoid fever", "Brucellosis"], key="care_disease")
d = esu_d[(esu_d.mohafaza_file == "Bekaa") & (esu_d.geo_level == "caza") & esu_d.disease.str.contains(dis.split()[0], case=False)].copy()
d = d.groupby(["year", "district_clean"], as_index=False).cases.sum()
d["per_10k"] = d.apply(lambda r: r.cases / pop[r.district_clean] * 1e4, axis=1)
d["partial_year"] = d.year == 2026
ch = alt.Chart(d).mark_line(point=True).encode(x=alt.X("year:O", title=None), y=alt.Y("per_10k:Q", title="reported cases per 10,000 (LRP 2026 population)"),
                                               color=alt.Color("district_clean:N", title="Caza"), strokeDash=alt.StrokeDash("partial_year:N", legend=None, scale=alt.Scale(domain=[False, True], range=[[1, 0], [4, 4]])),
                                               tooltip=["year", "district_clean", alt.Tooltip("per_10k:Q", format=".1f"), "cases"])
st.altair_chart(C.wm(ch, 700, 300), use_container_width=False)
st.caption("MoPH ESU notified cases (suspected and confirmed mixed, under-reported); the ESU Bekaa file is the old Beqaa mohafaza. The 2026 point (dashed) is January to August only and late-2025 months are reporting lag, so the drop in 2025 and 2026 is partly not real. "
           "Hepatitis A, Bekaa file: 2023 690, 2024 779, 2025 270, 2026 to August 67.")
a = esu_a[(esu_a.mohafaza_file == "Bekaa") & esu_a.disease.str.contains("Hepatitis A", case=False) & esu_a.year.between(2023, 2025)]
ag = a[a.group_type == "age"].groupby("group", as_index=False).cases.sum()
sx = a[a.group_type == "sex"].groupby("group", as_index=False).cases.sum()
l, r = st.columns(2)
with l:
    st.altair_chart(C.wm(alt.Chart(ag).mark_bar(color="#2874a6").encode(x=alt.X("group:N", sort=None, title="age group"), y=alt.Y("cases:Q", title="reported cases 2023-2025"), tooltip=["group", "cases"]), 380, 220), use_container_width=False)
with r:
    st.dataframe(C.pretty(sx.assign(share=(sx.cases / sx.cases.sum()).round(2)), group="Sex", cases="Reported cases 2023-2025", share="Share"), hide_index=True, width="stretch")
    st.caption("The burden is not concentrated in women, and children carry much of it: the rider protects all workers and households, with women as a delivery channel and priority group.")
k = st.columns(3)
wv = wash[wash.metric.astype(str).str.contains("faecal|fecal", case=False, na=False)]
k[0].metric("Faecally contaminated settlement water samples (Baalbek-Hermel, Jul 2026)", "72%", help="WaSH Sector / UNICEF SitRep No. 5 (processed/wash.csv)")
k[1].metric("Water per person per day in settlements", "15-20 L", help="against a 35 L standard (2024)")
k[2].metric("Wastewater discharged untreated (national)", "about 70%", help="CDR / MoEW strategic environmental assessment (reported)")
