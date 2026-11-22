"""Page 1: Where does the money go now, and who controls it?"""
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
from beqaa import io, narrative, state_capacity, theme_kpi  # noqa: E402

PROC = io.PROCESSED
SC = pd.read_csv(io.ROOT / "data" / "registry" / "state_capacity_sources.csv")
GOV_SHARE = float(SC.loc[SC.id == "SC02", "value"].iloc[0]) / (100.0 if float(SC.loc[SC.id == "SC02", "value"].iloc[0]) > 1 else 1.0)
GLOBAL_DIRECT, PLEDGE = 0.043, 0.25
ALNAP = "https://alnap.org/help-library/resources/sohs-2026/chapter-4-power-imbalances-and-improving-accountability/4-overview/"

lhf = theme_kpi.observed_series()
req = pd.read_csv(PROC / "funding_requirements.csv") if (PROC / "funding_requirements.csv").exists() else None
flows = pd.read_csv(PROC / "funding_flows.csv") if (PROC / "funding_flows.csv").exists() else None
flash = None
if req is not None:
    r = req[(req.plan == "Lebanon Flash Appeal 2026") & (req.cluster == "All clusters (plan total)")]
    flash = float(r.percent_funded.iloc[0]) / 100.0 if len(r) else None
last_year = int(lhf.year.max()) if lhf is not None else None
last_share = float(lhf.loc[lhf.year == last_year, "national_ngo_share"].iloc[0]) if lhf is not None else None
sent = narrative.page1(last_share, last_year, flash, GOV_SHARE, GLOBAL_DIRECT)
C.header("Funding today", sent, ["funding_flows"], purpose="How much recovery money reaches Lebanese organisations today, who receives it, and the target the theme is built around.")

c = st.columns(4)
c[0].metric("Direct to local actors, globally (2025)", f"{GLOBAL_DIRECT:.1%}", f"target {PLEDGE:.0%}", delta_color="off",
            help=f"Grand Bargain 2016 pledged 25% 'as directly as possible' to local actors; 4.3% went directly in 2025. Source: ALNAP SOHS 2026 ch.4 ({ALNAP}). Secondary source: verify against the primary tables.")
c[1].metric(f"LHF to national NGOs ({last_year})" if last_year else "LHF to national NGOs", f"{last_share:.0%}" if last_share is not None else "data pending",
            help="Lebanon Humanitarian Fund: share of project budgets to National NGOs. CBPF project summary via HDX (real). Nationwide, one pooled fund, not all aid; 2026 is a partial year." if last_share is not None else "Run `make ingest` (CBPF project summary). No value is shown without data.")
c[2].metric("Flash Appeal 2026 funded", f"{flash:.0%}" if flash is not None else "data pending",
            help="OCHA FTS: Lebanon Flash Appeal 2026, funding as a share of requirements (Health cluster: see the chart below)." if flash is not None else "Run `make ingest` (FTS requirements).")
c[3].metric("State share of health spending", f"{GOV_SHARE:.1%}", help="SC02: K2P/UNICEF primary-healthcare financing memo (Oct 2025), verified in state_capacity_sources.csv.")
if flash is not None:
    h = req[(req.plan == "Lebanon Flash Appeal 2026") & (req.cluster == "Health")]
    if len(h):
        st.caption(f"Health cluster 2026: ${float(h.funding_usd.iloc[0]) / 1e6:,.1f}M of ${float(h.requirements_usd.iloc[0]) / 1e6:,.1f}M funded ({float(h.percent_funded.iloc[0]):.0f}%). Source: OCHA FTS.")

st.subheader("Who receives the money: Lebanon funding by recipient type")
if flows is None:
    st.info("Data pending: run `make ingest` to load OCHA FTS funding flows. Nothing is shown without data.")
else:
    clu = st.radio("Cluster", ["Health", "All clusters"], horizontal=True, key="p1_cluster")
    d = flows if clu == "All clusters" else flows[flows.cluster == "Health"]
    d = d.groupby(["year", "recipient_type"], as_index=False).usd.sum()
    d = d[d.year <= 2026]
    ch = alt.Chart(d).mark_bar().encode(x=alt.X("year:O", title=None), y=alt.Y("usd:Q", stack="normalize", title="share of funding"), color=alt.Color("recipient_type:N", title="Recipient"),
                                        tooltip=["year", "recipient_type", alt.Tooltip("usd:Q", format=",.0f")])
    st.altair_chart(C.wm(ch, 760, 300), use_container_width=False)
    st.caption("Source: OCHA FTS incoming funding (real). FTS does not split national from international NGOs: the national-NGO share comes from the Lebanon Humanitarian Fund (below). "
               "Government is a lower bound on money held by Lebanese state actors. 2027 flows are pledges.")

lhf_alloc = pd.read_csv(PROC / "lhf_allocations.csv") if (PROC / "lhf_allocations.csv").exists() else None
left, right = st.columns(2)
with left:
    st.subheader("Lebanon Humanitarian Fund: who implements")
    if lhf_alloc is None:
        st.info("Data pending: run `make ingest` (CBPF project summary).")
    else:
        la = lhf_alloc.copy()
        ch2 = alt.Chart(la).mark_bar().encode(x=alt.X("year:O", title=None), y=alt.Y("budget_usd:Q", stack="normalize", title="share of project budgets"),
                                              color=alt.Color("partner_type:N", title="Partner type"), tooltip=["year", "partner_type", alt.Tooltip("budget_usd:Q", format=",.0f"), alt.Tooltip("projects:Q")])
        st.altair_chart(C.wm(ch2, 400, 280), use_container_width=False)
        st.caption("Source: OCHA CBPF project summary, Lebanon fund (real). National NGOs' share has risen from 17-24% in 2019-2022 to 38-47% in 2023-2026, still below the 70% aspiration for pooled funds.")
with right:
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

st.subheader("Theme KPI: share of Beqaa health money controlled by Lebanese actors")
scn = st.selectbox("Scenario for the projection", list(theme_kpi.SCENARIOS), format_func=lambda k: theme_kpi.SCENARIO_LABELS[k], key="p1_scn")
base = theme_kpi.local_control_share(last_year or 2025, scn)
k = st.columns(3)
k[0].metric("Baseline (observed)", f"{base['value']:.0%}" if base["value"] is not None else "missing", help=f"{base['scope']}. Source: {base['source']}. Status: {base['status']}. {base['caveat']}")
p30 = theme_kpi.local_control_share(2030, scn, scored=C.scored_cached(None, 30, 0.1, C.VER))
k[1].metric("2030 local control (escrow window)", f"{p30['value']:.0%}" if p30["value"] is not None else "missing",
            help=f"{p30['scope']}. Status: {p30['status']} (capacity starts at the national anchor in every district: no district series exists). Source: {p30['source']}.")
k[2].metric("2030 held by Lebanese organisations", f"{p30.get('lebanese_held_share', 0):.0%}", help="Share of released money administered by any Lebanese organisation (national NGO or above). Starts near 100% in the model because national NGOs qualify from day one.")
tab = theme_kpi.kpi_table(scenarios=[scn], scored=C.scored_cached(None, 30, 0.1, C.VER))
obs = lhf.rename(columns={"national_ngo_share": "value"}).assign(series="Observed: LHF share to national NGOs (real)", kind="observed")[["year", "value", "series", "kind"]] if lhf is not None else pd.DataFrame(columns=["year", "value", "series", "kind"])
proj = tab.rename(columns={"local_control_share": "value"}).assign(series="Projection: local control of the escrow window (assumption: national-anchor capacity, scenario thresholds)", kind="projection")[["year", "value", "series", "kind"]]
bq = theme_kpi.beqaa_proxy_series()
bqp = bq.rename(columns={"national_ngo_share": "value"}).assign(series="Proxy: Beqaa-titled LHF health projects, share to national NGOs", kind="observed")[["year", "value", "series", "kind"]] if bq is not None else pd.DataFrame(columns=["year", "value", "series", "kind"])
allp = pd.concat([obs, bqp, proj], ignore_index=True)
line = alt.Chart(allp).mark_line(point=True).encode(x=alt.X("year:O", title=None), y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1]), title="share"), color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom")),
                                                      strokeDash=alt.StrokeDash("kind:N", legend=None, scale=alt.Scale(domain=["observed", "projection"], range=[[1, 0], [5, 4]])))
st.altair_chart(C.wm(line, 760, 300), use_container_width=False)
st.caption("Proxy line: LHF health projects whose title names Bekaa or Baalbek-Hermel, full budgets, so projects that do not name it are missed (no governorate-level funding data is public). The series have different scopes and are not one continuous line: observed = one real pooled fund, nationwide; projection = the proposed escrow window, weighted by the rung that holds the money (INGO 0, national NGO 1/3, union of municipalities 2/3, MoPH 1). Page 3 shows the mechanism.")

st.subheader("Projects already funded in the Beqaa")
prj = pd.read_csv(PROC / "projects.csv") if (PROC / "projects.csv").exists() else None
if prj is None:
    st.info("Data pending: run `make ingest` (projects inventory).")
else:
    st.warning(f"None of the {len(prj)} inventoried projects tests soil contamination or screens people for exposure: the money is already in the fields (water, irrigation, cooperatives, farmland), "
               "and nothing connects it to health. Desk search of 2026-11-21; pages were read through a summarising tool and only 3 of the shortlisted pages could be opened, so this is a finding to confirm, not a proven absence.", icon="ℹ️")
    sectors = prj.sector.str.split(";").explode().str.strip().value_counts().rename_axis("sector").reset_index(name="projects")
    chs = alt.Chart(sectors).mark_bar(color="#2e86c1").encode(y=alt.Y("sector:N", sort="-x", title=None), x=alt.X("projects:Q", title="projects (a project can have several sectors)"), tooltip=["sector", "projects"])
    st.altair_chart(C.wm(chs, 520, 220), use_container_width=False)
    show = prj[prj.recency_ok.eq("yes") | prj.attachability_score.ge(2)].sort_values(["attachability_score", "recency_ok"], ascending=False)
    st.dataframe(C.pretty(show[["project_id", "name", "funder", "implementer_type", "location_precision", "amount", "currency", "recency_ok", "attachability_score", "verified"]], project_id="ID", name="Project",
                          funder="Funder", implementer_type="Implementer type", location_precision="Location precision", amount="Amount", currency="Cur.", recency_ok="Recent (6 mo)", attachability_score="Attachability 0-3",
                          verified="Page verified"), hide_index=True, width="stretch")
    st.caption("Source: data/raw/projects (inventory) with per-project verification in data/registry/projects_verification.csv. `verified` is `no` unless a person or agent opened the source page; discrepancies are recorded there.")

st.subheader("Why a mechanism: pledges without one fail")
st.markdown(
    f"- **Grand Bargain 2016:** 25% of humanitarian funding pledged 'as directly as possible' to local actors; **4.3%** went directly in 2025 ([ALNAP SOHS 2026 ch.4]({ALNAP})).\n"
    "- **UN Emergency Relief Coordinator, June 2025:** aspiration of 70% of pooled funding to local actors, especially women-led organizations ([ALNAP SOHS 2026 ch.4.1](https://alnap.org/help-library/resources/sohs-2026/chapter-4-power-imbalances-and-improving-accountability/4-1-funding-pathways-and-the-politics-behind-the-numbers/)).\n"
    "- **ODI/HPG, May 2026:** CBPF share to local and national actors 2016-2025 ([report](https://media.odi.org/documents/HST-LHL_localistion_report_final.pdf)).\n"
    "- **Lebanon Recovery Fund** ran no projects in 2025 ([UNDP MPTF annual report](https://mptf.undp.org/sites/default/files/documents/2026-05/2025_consolidated_annual_narrative_report_lebanon_recovery_fund.pdf)).")
