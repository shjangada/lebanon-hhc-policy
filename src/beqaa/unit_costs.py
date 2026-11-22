"""Unit costs, cost per household / per case / per notified case averted, and the pilot KPI table mapped to the escrow triggers.

unit_costs.csv  item, unit, low, central, high, source, year, lebanon_price (y/n). Built only from rows that have a number in processed/prices_pack.csv, processed/cost_ranges.csv and riders.py:
                the AUB lab prices and CHW pay and the $20.03 primary-care service are Lebanese (y); catalogue filters, chlorine, Cr(VI) and PPE are not (n).
kpis.csv        level, KPI, baseline, baseline_source (or "set in pilot months 1-3"), target, frequency, owner, splits, escrow_trigger. Targets that are not published values are labelled ASSUMPTION;
                the three escrow triggers (referral completion >= 0.40, posts filled >= 0.60, capacity >= 0.30) come from escrow_params.yaml. Every KPI is reported split by sex, nationality
                (Lebanese / displaced Syrian), registration status (registered / unregistered) and settlement vs village, so the equity safeguard is measured and not assumed."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import escrow, m6_illness_averted as m6, riders, start_site
from .io import PROCESSED

SPLITS = "sex; nationality (Lebanese / displaced Syrian); registration status (registered / unregistered); settlement vs village"


def unit_costs() -> pd.DataFrame:
    pk = pd.read_csv(PROCESSED / "prices_pack.csv")
    cr = pd.read_csv(PROCESSED / "cost_ranges.csv").set_index("item_id")
    rows = []

    def add(item, unit, low, central, high, source, year, leb):
        rows.append({"item": item, "unit": unit, "low": low, "central": central, "high": high, "source": source, "year": year, "lebanon_price": "y" if leb else "n"})
    u = riders.unit_prices().set_index("unit")
    add("Water nitrate lab test", "per sample", u.loc["nitrate_water", "usd_low"], u.loc["nitrate_water", "usd_central"], u.loc["nitrate_water", "usd_high"], "AUB CEE testing price list (cost_ranges 6a)", 2025, True)
    add("Water total chromium lab test", "per sample", u.loc["cr_water", "usd_low"], u.loc["cr_water", "usd_central"], u.loc["cr_water", "usd_high"], "AUB CEE price list (6b)", 2025, True)
    add("Soil total chromium (digestion + metal)", "per sample", u.loc["soil_total_cr", "usd_low"], u.loc["soil_total_cr", "usd_central"], u.loc["soil_total_cr", "usd_high"], "derived from AUB prices (6c; secondary)", 2025, True)
    for it, lab in (("E. coli lab test", "E. coli lab test, water"), ("Total coliforms lab test", "Total coliforms lab test, water"), ("Free chlorine lab test", "Free available chlorine lab test, water")):
        r = pk[pk["item"].str.startswith(lab.split(",")[0].replace("lab test", "lab test"))]
        if len(r):
            r = r.iloc[0]
            add(it, "per sample", np.nan, float(r.central), np.nan, "AUB CEE testing price list (prices_extra)", 2025, True)
    add("Community health worker pay", "per month", u.loc["chw_month", "usd_low"], u.loc["chw_month", "usd_central"], u.loc["chw_month", "usd_high"], "job postings (cost_ranges 4b/4a/4c; secondary)", 2026, True)
    add("Primary-care service (full provider cost)", "per service", u.loc["phc_service", "usd_low"], u.loc["phc_service", "usd_central"], u.loc["phc_service", "usd_high"], "K2P/UNICEF 2022 (cost_ranges 2a)", 2022, True)
    f = pk[pk["item"].str.startswith("Household ceramic water filter")].iloc[0]
    add("Household ceramic water filter", "per household", float(f.low), float(f.central), float(f.high), "UNICEF supply catalogue (ex-works; excludes freight and distribution)", 2026, False)
    n = pk[pk["item"].str.startswith("NaDCC 33 mg")].iloc[0]
    add("NaDCC chlorine tablets (household supply)", "per household per month", np.nan, float(n.central), np.nan, "UNICEF supply catalogue", 2026, False)
    add("Cr(VI) analysis (US lab fee schedules)", "per sample", 40.0, 76.0, 80.25, "US only: $40 soil (2024 list), $74.90 water (Westchester Co. NY, 2025), $77 soil (c. 2008, secondary), $80.25 solid (2025): NO Lebanese price", 2025, False)
    for lab, nm in (("Pesticide PPE - locally adapted", "Pesticide PPE kit, locally adapted set"), ("Pesticide PPE kit - commercial", "Pesticide PPE kit, commercial"), ("Pesticide PPE kit - farm applicator", "Pesticide PPE kit, 14-day applicator kit")):
        r = pk[pk["item"].str.startswith(lab)].iloc[0]
        add(nm, "per kit", np.nan, float(r.central), np.nan, "retail / Nepal study (prices_pack): NO Lebanese or regional NGO price", str(r.year), False)
    fac = pd.read_csv(PROCESSED / "facilities.csv", dtype={"cadaster_id": str})
    cdd = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})[["cadaster_id", "district"]]
    npc = fac[fac.type == "PHC"].merge(cdd, on="cadaster_id").groupby("district").size()
    add("E-referral / DHIS2 software and rollout, first year per district (PROXY, not used in the ranking)", "per district", float(npc.min() * 1245), float(npc.median() * 1245), float(npc.max() * 1245),
        "Sierra Leone eIDSR rollout $1,021 + running $224 per facility (PMC8820104, 2017) x PHCs per district; surveillance system, excludes coordination and tracking staff", 2017, False)
    add("Hospital delivery, patient share (UNHCR scheme, ENDED 1 Dec 2025)", "per delivery", float(cr.loc["3c", "usd_low"]), float(cr.loc["3c", "usd_central"]), float(cr.loc["3c", "usd_high"]), "cost_ranges 3c", 2025, True)
    add("Caesarean, patient share (UNHCR scheme, ENDED)", "per delivery", float(cr.loc["3d", "usd_low"]), float(cr.loc["3d", "usd_central"]), float(cr.loc["3d", "usd_high"]), "cost_ranges 3d", 2025, True)
    return pd.DataFrame(rows)


def cost_metrics(ranked: pd.DataFrame | None = None, params: dict | None = None, coverage: float = 0.5) -> dict:
    """Cost per household reached, cost per case by care level, and cost per NOTIFIED case averted for the top-ranked site (assumption-based counts; sourced unit prices)."""
    r = ranked if ranked is not None else start_site.score()
    top = r.iloc[0]
    p = {**start_site.DEFAULT_PARAMS, **(params or {})}
    pr = start_site._prices()
    people = float(top.settlement_people_2016) * coverage
    hh = max(people / p["hh_size"], 1)
    pkg = {tag: p["n_wells"] * (pr["nitrate"][i] + pr["cr_water"][i]) + p["chw_months"] * pr["chw"][i] + hh * pr["filter"][i] + (0 if top.soil_sampled_nearby else p["n_soil"] * pr["soil"][i])
           for tag, i in (("low", 0), ("central", 1), ("high", 2))}
    chw_visit = pr["chw"][1] / (10 * 52 / 12)                      # CHW month / visits a CHW makes a month (10 a week: assumption)
    from .io import load_dataset
    dp = load_dataset("population").df.merge(load_dataset("cadasters").df[["cadaster_id", "district"]], on="cadaster_id").groupby("district").population_total.sum()
    sim = m6.simulate(top.district, people, float(dp[top.district]), "filtration", 1.0)
    return {"top_site": top.cadaster_name, "district": top.district, "households_reached": hh, "package_cost_usd": pkg,
            "cost_per_household_usd": {k: v / hh for k, v in pkg.items()},
            "cost_per_case_by_care_level": {"CHW contact (derived: CHW month / assumed 10 visits a week)": chw_visit, "primary-care service (K2P/UNICEF 2022)": 20.03,
                                            "hospital delivery, patient share (UNHCR scheme, ended)": "128-170", "caesarean, patient share (UNHCR scheme, ended)": "255-300"},
            "cost_per_notified_case_averted_usd": {"p05": sim["cost_per_case_averted_p05"], "median": sim["cost_per_case_averted_median"], "p95": sim["cost_per_case_averted_p95"]},
            "note": "UPPER BOUND on cost per illness averted: notified cases are a small share of waterborne illness; the pilot measures the true figure"}


def kpis() -> pd.DataFrame:
    esu = start_site.disease_rate()
    rule = escrow.DEFAULT_RULES
    cap = float(__import__("beqaa.state_capacity", fromlist=["x"]).national_baseline()["admin_anchor"])
    dis = "; ".join(f"{d} {v:.1f}" for d, v in esu.round(1).items())
    R = [("Outcome", "Cadasters reporting health services inaccessible (cost is the main barrier)", "17 of 53 sampled Bekaa and Baalbek-Hermel cadasters, Dec 2024; reduced income 10/17, medicine cost 9/17 (REACH HSM; purposive sample, key informants)", "falling in pilot cadasters against months 1-3 (no numeric target is published)", "annual", "REACH / consortium", ""),
         ("Output", "People reached and screened per site per month", "set in pilot months 1-3 (outreach coverage partial; no visit frequency published)", "ASSUMPTION: at least half of settlement people reached (slider)", "monthly", "consortium lead (PHCC operator)", ""),
         ("Output", "Water samples per supply per year (nitrate, chromium, microbial)", "set in pilot months 1-3", "at least 12 per supply per year (WHO GDWQ Table 4.4, supplies serving fewer than 5,000 people)", "monthly", "consortium lead + AUB lab", ""),
         ("Output", "Share of tested settlement water sources faecally contaminated", "72% of tested samples, Baalbek-Hermel settlements, Jul 2026 (WaSH Sector / UNICEF SitRep No. 5)", "falling against months 1-3 (no numeric target is published)", "quarterly", "WASH partners + consortium", ""),
         ("Output", "Red flags referred", "set in pilot months 1-3", "all red flags routed to the centre with spare capacity", "monthly", "CHWs + centre", ""),
         ("Outcome", "Referral completion (referrals completed / sent)", "none published: set in pilot months 1-3", f">= {rule['referral_min']:.2f} (escrow release threshold)", "monthly, third-party spot check", "centre + independent monitor", f"escrow trigger: referral completion >= {rule['referral_min']:.2f}"),
         ("Outcome", "Days from red flag to care", "none published: set in pilot months 1-3", "set after months 1-3", "monthly", "centre register", ""),
         ("Outcome", "Resolved or recovered at 2-4 weeks", "none published: set in pilot months 1-3", "set after months 1-3", "monthly", "CHW follow-up call", ""),
         ("Outcome", "Reported hepatitis A + typhoid per 10,000, pilot vs comparison cazas", f"ESU 2023-2025 mean by district: {dis} (reported cases; under-reported)", "pilot caza falling relative to comparison", "quarterly", "MoPH ESU + consortium", ""),
         ("Outcome", "Pesticide symptoms and injuries treated", "none for Beqaa (reference only: 69 of 126 women farmworkers reported health problems, Bekaa and Koura sample, self-reported)", "set after months 1-3", "quarterly", "CHWs + centres", ""),
         ("Outcome", "Antenatal care 4+ visits among women workers", "registered displaced Syrians: 0.691 (HAUS 2024, national); VASyR: 66% nationally in 2025 (the preliminary slides say 54%) and 46% in Bekaa in 2024; no host-Lebanese baseline found", "ASSUMPTION: above the HAUS reference for every group", "quarterly", "centre registers", ""),
         ("System", "Posts filled (CHW and nurse posts budgeted vs filled)", "none published: set in pilot months 1-3", f">= {rule['posts_filled_min']:.2f} (escrow release threshold)", "quarterly", "consortium lead", f"escrow trigger: posts filled >= {rule['posts_filled_min']:.2f}"),
         ("System", "District administrative capacity index", f"{cap:.3f} (WGI government effectiveness 2025, national anchor)", f">= {rule['admin_capacity_min']:.2f} (capacity threshold); growth capped at 0.05 a year", "annual", "municipal union + MoPH", f"escrow trigger: capacity >= {rule['admin_capacity_min']:.2f}"),
         ("System", "Transparent reporting (published quarterly spend + third-party spot check)", "none: scenario rule from 2027", "published every quarter", "quarterly", "consortium lead", "escrow trigger: transparent reporting"),
         ("System", "Centre added load from the rider", "M1 with assumed centre capacity (300 a week)", "at most 10% of a centre's yearly capacity", "monthly", "MoPH PHC department", ""),
         ("System", "Share of pilot money held by Lebanese organisations", "LHF national NGO share 38-47% (2023-26); Beqaa-titled health proxy 0-5% (2024-26)", "rises with the escrow ladder (INGO -> national NGO -> municipal union -> MoPH)", "quarterly", "LHF secretariat", "ladder rung = capacity and reporting thresholds"),
         ("Equity", "Share of services used by unregistered workers and by women", "unobservable from public data (no group baseline)", "ASSUMPTION: no group below the settlement average", "quarterly", "consortium (anonymous community-ID tally)", "")]
    d = pd.DataFrame(R, columns=["level", "KPI", "baseline", "target", "frequency", "owner", "escrow_trigger"])
    d["baseline_source"] = d.baseline.map(lambda b: "set in pilot months 1-3" if b.startswith(("set in pilot", "none")) else "see baseline text")
    d["splits"] = SPLITS
    return d[["level", "KPI", "baseline", "baseline_source", "target", "frequency", "owner", "splits", "escrow_trigger"]]


def run() -> dict:
    u = unit_costs()
    u.to_csv(PROCESSED / "unit_costs.csv", index=False)
    k = kpis()
    k.to_csv(PROCESSED / "kpis.csv", index=False)
    return {"unit_costs": len(u), "kpis": len(k), "metrics": cost_metrics()}
