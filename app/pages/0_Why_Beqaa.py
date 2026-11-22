"""Section 0: Why Beqaa. Agriculture, military action, age and sex, health access: each number sourced and dated; old sources are labelled old."""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import io, theme_kpi  # noqa: E402

PROC = io.PROCESSED
cad = io.load_dataset("cadasters").df
pop = io.load_dataset("population").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
conf = io.load_dataset("conflict_exposure").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
fac = io.load_dataset("facilities").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
agesex = pd.read_csv(PROC / "agesex_by_district.csv") if (PROC / "agesex_by_district.csv").exists() else None
dmg = pd.read_csv(PROC / "damage_published.csv") if (PROC / "damage_published.csv").exists() else None
facts = pd.read_csv(io.ROOT / "data" / "registry" / "why_beqaa_facts.csv")
bq = theme_kpi.beqaa_proxy_series()

byd = pop.groupby("district").population_total.sum()
inc = conf.groupby("district").conflict_incidents.sum()
phc = fac[fac.type == "PHC"].groupby("district").size().reindex(byd.index).fillna(0)
hosp = fac[fac.type == "hospital_hub"].groupby("district").size().reindex(byd.index).fillna(0)
ngo = float(bq.national_ngo_share.mean()) if bq is not None and len(bq) else float("nan")
sent = (f"Five districts, {int(byd.sum()):,} people (LRP 2026) in {len(cad)} cadasters: Lebanon's farming heartland, with {int(inc.sum()):,} conflict incidents recorded between October 2023 and July 2025, "
        f"{int(phc.sum())} primary-care centres and {int(hosp.sum())} hospitals, and about {ngo:.0%} of the Beqaa-titled LHF health money (2024-26 average) going to national NGOs.")
C.header("Why Beqaa", sent, ["cadasters", "population", "conflict_exposure", "facilities"],
         purpose="The Beqaa Valley here means the five districts Zahle, West Bekaa, Rachaya, Baalbek and Hermel (a physical region, not the Bekaa governorate alone).")

k = st.columns(4)
k[0].metric("People (LRP 2026)", f"{int(byd.sum()):,}", help="LRP 2026 population package by cadaster (host, displaced and registered Syrians)")
k[1].metric("Conflict incidents", f"{int(inc.sum()):,}", help="LRP 2026 package, Oct 2023 to 29 Jul 2025; the 2026 war is not in this series (ACLED access is limited to events older than 12 months)")
k[2].metric("Primary-care centres per 10,000", f"{phc.sum() / byd.sum() * 1e4:.1f}", help="MoPH list (65 centres); only 4 facilities have a dated 2026 status")
k[3].metric("Beqaa-titled LHF health money to national NGOs", f"{ngo:.0%}", help="Proxy: LHF health projects whose title names Bekaa or Baalbek-Hermel, 2024-26, full budgets")

st.subheader("Who lives here: age and sex")
if agesex is None:
    st.info("Data pending: run `make ingest` (WorldPop age and sex).")
else:
    sel = st.selectbox("District", ["All five districts"] + sorted(agesex.district.unique()), key="why_district")
    a = agesex if sel.startswith("All") else agesex[agesex.district == sel]
    a = a.groupby(["sex", "age_band"], as_index=False).population.sum()
    a["label"] = a.age_band.map(lambda b: "90+" if b == 90 else f"{b}-{b + 4}" if b >= 5 else ("0" if b == 0 else "1-4"))
    a["signed"] = a.population.where(a.sex == "female", -a.population)
    order = a.drop_duplicates("age_band").sort_values("age_band").label.tolist()
    pyr = alt.Chart(a).mark_bar().encode(y=alt.Y("label:N", sort=order[::-1], title="age band"), x=alt.X("signed:Q", title="men ← people → women", axis=alt.Axis(format="s")),
                                         color=alt.Color("sex:N", scale=alt.Scale(domain=["female", "male"], range=["#b03a6e", "#2874a6"]), title=None),
                                         tooltip=["sex", "label", alt.Tooltip("population:Q", format=",.0f")])
    st.altair_chart(C.wm(pyr, 520, 380), use_container_width=False)
    t = a.population.sum()
    w = a[(a.sex == "female") & a.age_band.between(15, 45)].population.sum()
    st.caption(f"WorldPop 2025, modelled 1 km grid (not a census, and not scaled to the LRP 2026 totals): women 15-49 are {w / t:.0%}, children under 5 are {a[a.age_band < 5].population.sum() / t:.0%} "
               f"and people 60+ are {a[a.age_band >= 60].population.sum() / t:.0%} of {int(t):,}: demand for maternal and child care, and for chronic care.")

st.subheader("Military action: incidents per district")
d = pd.DataFrame({"incidents": inc, "per_1000": inc / byd * 1000}).reset_index()
ch = alt.Chart(d).mark_bar(color="#c0392b").encode(y=alt.Y("district:N", sort="-x", title=None), x=alt.X("per_1000:Q", title="incidents per 1,000 people"),
                                                   tooltip=["district", alt.Tooltip("incidents:Q", format=",.0f"), alt.Tooltip("per_1000:Q", format=".2f")])
st.altair_chart(C.wm(ch, 400, 220), use_container_width=False)
st.caption("LRP 2026 conflict-incident counts per cadaster, Oct 2023 to 29 Jul 2025. It stops before the 2026 war, so it understates the current picture.")

st.subheader("Damage figures (published; checked against the PDFs only where marked)")
if dmg is not None:
    show = dmg[dmg.admin_level.isin(["governorate", "district"]) & dmg.metric.isin(["destroyed_buildings_total_partial", "damage_all_sectors", "housing_units_destroyed_or_damaged", "agriculture_damage"])]
    st.dataframe(C.pretty(show[["geography", "metric", "value", "unit", "period", "figure_source", "status"]], geography="Area", metric="Measure", value="Value", unit="Unit", period="Period", figure_source="Source", status="Status"),
                 hide_index=True, width="stretch")
    st.caption("Sources: UN-Habitat BDDQA (Jan 2025), World Bank RDNA (Mar 2025), CNRS-L via Annahar (2026 housing units). Rows were extracted automatically and are `to_verify_pdf`; "
               "no 2026 building-level damage dataset exists for the Beqaa. The Nabi Sheet casualty figure is not used until the article is read (the headline in its URL differs from the handoff figure).")

st.subheader("Farming and food: reported figures")
st.dataframe(C.pretty(facts[["topic", "claim", "value", "unit", "year", "source", "status"]], topic="Topic", claim="Claim", value="Value", unit="Unit", year="Year", source="Source", status="Status"), hide_index=True, width="stretch")
st.caption("Older figures are labelled with their year. 'reported_not_reread' means the number comes from the cited source as reported to the team and has not been re-read here; check before quoting. "
           "Soil results (5 villages, rung a) and crop transfer factors are on the next sections.")
