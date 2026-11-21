"""Generate MOCK datasets for the Beqaa dashboard. Every file is clearly labelled MOCK.
Replace each file with real data as it arrives (see CLAUDE.md, section 4)."""
import math
import pathlib

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "mock"
OUT.mkdir(parents=True, exist_ok=True)

MOCK_SRC = {"source": "MOCK (synthetic)", "source_date": "2026-11-21", "url": "", "status": "mock"}


def save(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Write a mock CSV with is_mock=True and provenance columns (principle 1)."""
    df = df.copy()
    df["is_mock"] = True
    for k, v in MOCK_SRC.items():
        if k not in df.columns:
            df[k] = v
    df.to_csv(OUT / name, index=False)
    return df


# Real district names (Beqaa + Baalbek-Hermel governorates); cadasters are synthetic.
districts = {"Baalbek": (34.00, 36.20), "Hermel": (34.39, 36.38), "Zahle": (33.85, 35.90),
             "West Bekaa": (33.62, 35.75), "Rachaya": (33.50, 35.84)}
rows = []
for d, (lat, lon) in districts.items():
    for i in range(8):
        rows.append({"cadaster_id": f"MOCK-{d[:3].upper()}-{i+1:02d}", "cadaster_name": f"{d} mock town {i+1}",
                     "district": d, "governorate": "Baalbek-Hermel" if d in ("Baalbek", "Hermel") else "Bekaa",
                     "lat": round(lat + rng.normal(0, 0.06), 5), "lon": round(lon + rng.normal(0, 0.06), 5)})
cad = save(pd.DataFrame(rows), "cadasters.csv")

pop = cad[["cadaster_id"]].copy()
pop["population_total"] = rng.integers(2_000, 40_000, len(cad))
pop["women_15_49"] = (pop.population_total * rng.uniform(0.22, 0.27, len(cad))).astype(int)
pop["pregnant_est"] = (pop.women_15_49 * 0.041).astype(int)          # ~16,000/390,000 (UNFPA ratio)
pop["displaced"] = (pop.population_total * rng.uniform(0, 0.15, len(cad))).astype(int)
pop["displaced_syrians_registered"] = (pop.population_total * rng.uniform(0.05, 0.35, len(cad))).astype(int)
pop["unregistered_workers_est"] = (pop.population_total * rng.uniform(0.01, 0.10, len(cad))).astype(int)
save(pop, "population.csv")

fac = []
for k in range(22):
    c = cad.sample(1, random_state=k).iloc[0]
    fac.append({"facility_id": f"MOCK-PHC-{k+1:02d}", "name": f"Mock PHC {k+1}", "type": "PHC",
                "cadaster_id": c.cadaster_id, "lat": c.lat + rng.normal(0, 0.01), "lon": c.lon + rng.normal(0, 0.01),
                "capacity_weekly": int(rng.integers(150, 900)),
                "status_2026": rng.choice(["open", "open", "open", "closed", "damaged"]),
                "offers_anc": bool(rng.random() > 0.3), "in_mophnetwork": bool(rng.random() > 0.4),
                "power_source": rng.choice(["grid_only", "generator", "generator", "solar"])})
for k, (lat, lon, n) in enumerate([(34.006, 36.21, "Mock Baalbek hub"), (33.847, 35.902, "Mock Zahle hub"),
                                   (34.39, 36.38, "Mock Hermel hub")]):
    fac.append({"facility_id": f"MOCK-HUB-{k+1}", "name": n, "type": "hospital_hub", "cadaster_id": None,
                "lat": lat, "lon": lon, "capacity_weekly": 2000, "status_2026": "open",
                "offers_anc": True, "in_mophnetwork": True})
fac = pd.DataFrame(fac)
# Dated functionality status (MOCK). Separate rng: adding these columns must not shift the draws of the datasets below.
_r = np.random.default_rng(11)
fac["hours_per_week"] = np.nan
is_phc = fac.type == "PHC"
fac.loc[is_phc & (fac.status_2026 == "open") & (_r.random(len(fac)) < 0.2), "status_2026"] = "partial"          # partially functional
fac["status_date"] = [(pd.Timestamp("2026-11-01") - pd.Timedelta(days=int(d))).strftime("%Y-%m-%d") for d in _r.integers(0, 60, len(fac))]
fac.loc[is_phc & (_r.random(len(fac)) < 0.15), "status_date"] = ""                                                # no dated source -> unknown (shown grey)
fac["status_source"] = np.where(fac.status_date == "", "", "MOCK Health Sector functionality update")
# Mobile medical units: part-time facilities, effective capacity = capacity x hours_per_week / 40
mob = []
for k, (idx, hrs) in enumerate([(3, 24), (27, 16)]):
    c = cad.iloc[idx]
    mob.append({"facility_id": f"MOCK-MMU-{k+1}", "name": f"Mock mobile maternal unit {k+1}", "type": "mobile", "cadaster_id": c.cadaster_id,
                "lat": c.lat, "lon": c.lon, "capacity_weekly": 300, "status_2026": "open", "offers_anc": True, "in_mophnetwork": False,
                "power_source": "generator", "hours_per_week": hrs, "status_date": "2026-11-01", "status_source": "MOCK Health Sector 4W (mobile unit routes)"})
fac = pd.concat([fac, pd.DataFrame(mob)], ignore_index=True)
fac = save(fac, "facilities.csv")


def hav(a, b, c, d):
    R = 6371
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


tt = [{"cadaster_id": r.cadaster_id, "facility_id": f.facility_id,
       "minutes": round(hav(r.lat, r.lon, f.lat, f.lon) * 1.3 / 40 * 60, 1)}   # 1.3 detour factor, 40 km/h
      for r in cad.itertuples() for f in fac.itertuples()]
save(pd.DataFrame(tt), "travel_time.csv")

vul = cad[["cadaster_id", "district"]].copy()
ipc = {"Baalbek": 0.30, "Hermel": 0.32, "Zahle": 0.18, "West Bekaa": 0.15, "Rachaya": 0.14}   # MOCK shares
vul["ipc3plus_share"] = vul.district.map(ipc) + rng.normal(0, 0.02, len(vul)).round(3)
vul["female_headed_hh_share"] = rng.uniform(0.15, 0.30, len(vul)).round(3)
vul["unable_to_access_care_share"] = rng.uniform(0.10, 0.45, len(vul)).round(3)
vul["no_insurance_share"] = rng.uniform(0.3, 0.8, len(vul)).round(3)
vul["level"] = "district_value_applied_to_cadaster"
save(vul.drop(columns="district"), "vulnerability.csv")

# Official district severity (MOCK scores, 1-5 scale like JIAF 2.0 severity classes).
sev = pd.DataFrame({"district": list(districts),
                    "jiaf_severity": [4, 4, 3, 3, 3], "health_severity": [4, 4, 3, 2, 3],
                    "fsa_composite_severity": [4, 5, 3, 3, 2]})
sev["source_date"] = "2026-11-21"
save(sev, "official_severity.csv")

# Soil: metal values are the REAL values reported by CNRS-L (Apr 2026) Ch. II; locations are MOCK.
soil = pd.DataFrame([
    ("Rayak", "total_P", 1858), ("Rayak", "total_P", 970), ("Rayak", "Cr", 220), ("Chemstar", "Cr", 230),
    ("Chemstar", "total_P", 628), ("Bouday", "Pb", 230), ("Bouday", "Cr", 140), ("Ksarnaba", "Cr", 170)],
    columns=["site_name", "parameter", "value_mg_kg"])
soil["cadaster_id"] = rng.choice(cad.cadaster_id, len(soil))
soil["lat"] = soil.cadaster_id.map(cad.set_index("cadaster_id").lat)
soil["lon"] = soil.cadaster_id.map(cad.set_index("cadaster_id").lon)
soil["source"] = "CNRS-L/MoE Apr 2026, Ch. II (values); location MOCK"
soil["evidence_rung"] = "a"
soil["is_mock_location"] = True
save(soil, "soil_sites.csv")

wells = cad[["cadaster_id"]].sample(15, random_state=1).copy()
wells.insert(0, "site_id", [f"MOCK-WELL-{i+1:02d}" for i in range(len(wells))])
wells["nitrate_mg_l"] = rng.uniform(10, 260, len(wells)).round(0)
wells["date"] = "2026-01-01"
save(wells, "water_quality.csv")

# Crop transfer factors (soil -> edible crop), MOCK placeholders; real source: Abi Saab et al. 2022.
tf = pd.DataFrame([("Cr", "lettuce", 0.02), ("Cr", "potato", 0.005), ("Pb", "lettuce", 0.03),
                   ("Pb", "potato", 0.004), ("Cr", "wheat", 0.01), ("Pb", "wheat", 0.01)],
                  columns=["metal", "crop", "transfer_factor"])
save(tf, "crop_transfer.csv")

# Conflict exposure per cadaster (MOCK counts; real source: LRP 2026 package sheet "Conflict Incidents_adm3_Summary", incidents since Oct 2023).
ce = cad[["cadaster_id"]].copy()
dist_scale = {"Baalbek": 18, "Hermel": 14, "Zahle": 6, "West Bekaa": 8, "Rachaya": 4}
ce["conflict_incidents"] = [int(rng.poisson(dist_scale[d])) for d in cad.district]
save(ce, "conflict_exposure.csv")

# Interventions. Cost/people are PER UNIT (see label). `steps` = cascade steps shifted (semicolon list);
# lift_* = absolute uplift in step probability for people reached (MOCK ranges). `divisible` = can be bought in fractions.
iv = pd.DataFrame([
    ("mobile_maternal_unit", "Mobile maternal unit (per unit-year)", 90_000, 160_000, "reach", 1200, 2500, "any_anc;anc4", 0.05, 0.15, False,
     "Unregistered workers may avoid fixed stops", "Medium: NGO-run", "Low", "May bypass fixed PHCs", "Needs safe routes; suspend if conflict"),
    ("hub_spoke_ereferral", "Hub-spoke + e-referral (per district-year)", 120_000, 250_000, "continuity", 3000, 6000, "referral_complete", 0.15, 0.35, False,
     "Needs ID/registration for tracked referral", "Medium: data held by hub", "Medium", "Strengthens PHCs if MoPH-owned", "Data protection for unregistered patients"),
    ("transport_vouchers", "Transport vouchers for ANC/delivery (per 100 women)", 4_000, 9_000, "reach", 100, 100, "anc4;facility_delivery", 0.08, 0.20, True,
     "Voucher eligibility checks can exclude undocumented women", "High: voucher resale", "Low", "Low", "Cash-like; check price inflation"),
    ("soil_water_screening", "Soil + water screening per facility catchment", 3_000, 12_000, "environment", 0, 0, "", 0.0, 0.0, True,
     "Results tied to landowners may not reach workers", "Low", "Low", "Needs local lab (e.g. AUB)", "Publication of results may affect land prices"),
    ("cr_speciation_tests", "Cr(VI) speciation, 10 samples", 500, 1_500, "environment", 0, 0, "", 0.0, 0.0, True,
     "None direct", "Low", "Low", "Needs lab partner", "Settles the key uncertainty (cr6 fraction)"),
    ("washing_water_truck", "Daily washing water truck for field workers (per month)", 1_500, 4_000, "environment", 200, 400, "", 0.0, 0.0, True,
     "Reaches workers at field edge, not only landowners", "Low", "Medium: recurring cost", "Could displace municipal water service", "Low"),
    ("sunflower_biochar_plot", "Sunflower + biochar trial plot", 100, 1_000, "environment", 0, 0, "", 0.0, 0.0, True,
     "Landowner consent needed; workers not involved", "Low", "Low", "Low", "Trial only: not a health intervention yet"),
    ("chw_women_orgs", "Community health workers via women's orgs (per 10 CHW-year)", 25_000, 60_000, "reach", 1500, 3000, "anc4;postnatal", 0.05, 0.15, False,
     "Organisation membership may exclude outsiders", "Medium: org capture", "Low: builds local capacity", "Could compete with PHC outreach", "Trusted local actors; women-led"),
], columns=["intervention_id", "label", "cost_low_usd", "cost_high_usd", "acts_on", "people_low", "people_high", "steps", "lift_low",
            "lift_high", "divisible", "risk_exclusion", "risk_capture", "risk_dependency", "risk_displacement", "risk_conflict"])
# Feasibility filter F1-F8 (docs/FEASIBILITY.md). Qualitative team judgments (status: assumption), not data.
FEAS = {  # id: (needs_new_public_money, pausable, grid_power_dependent, needs_new_doctors, existing_institution, requires_id, funding_window, indicator_source)
    "mobile_maternal_unit": (False, True, False, False, "MoPH PHC hub + existing partner (UNFPA/MSF precedent)", False, "LHF; UNFPA appeal", "visits scheduled/held; ANC4 via hub register"),
    "hub_spoke_ereferral": (False, True, False, False, "MoPH PHC network + DHIS2", True, "LHF/LFF Beqaa window", "referrals completed/sent (pilot-collected, offline-first phone log)"),
    "transport_vouchers": (False, True, False, False, "Women's organisation / NGO distribution", True, "LHF; EU civil-society window", "vouchers used; ANC4 and facility delivery"),
    "soil_water_screening": (False, True, False, False, "AUB lab / MoE", False, "UNDP/WB GATE grants (check eligibility)", "samples reported; days from finding to action"),
    "cr_speciation_tests": (False, True, False, False, "AUB lab", False, "small grant (<= $1.5k)", "Cr(VI) fraction measured"),
    "washing_water_truck": (False, True, False, False, "Municipality / WASH sector", False, "WASH sector (LHF)", "litres/day delivered; workers served"),
    "sunflower_biochar_plot": (False, True, False, False, "AUB + farmer cooperative", False, "UNDP/WB GATE (check eligibility)", "soil metal change in plot (research pilot only)"),
    "chw_women_orgs": (False, True, False, False, "Women's organisations + PHC network", False, "EU civil-society window; LHF", "CHW visits; ANC4 and postnatal follow-up"),
}
for j, col in enumerate(["needs_new_public_money", "pausable", "grid_power_dependent", "needs_new_doctors", "existing_institution", "requires_id",
                         "funding_window", "indicator_source"]):
    iv[col] = iv.intervention_id.map(lambda i: FEAS[i][j])
iv["note"] = "ALL COSTS/LIFTS MOCK: replace with UNFPA/WHO appeal lines, K2P/UNICEF, quotes"
save(iv, "interventions.csv")

# Care cascade baseline by group (MOCK probabilities; referral completion is an assumption even when real).
groups = ["host_lebanese", "displaced_lebanese", "registered_displaced_syrians",
          "unregistered_workers_est", "women_15_49"]
base = {"p_any_anc": [0.90, 0.80, 0.70, 0.45, 0.82], "p_anc4": [0.75, 0.60, 0.45, 0.25, 0.62],
        "p_facility_delivery": [0.97, 0.92, 0.85, 0.60, 0.90], "p_postnatal": [0.60, 0.45, 0.35, 0.15, 0.48],
        "p_referral_complete": [0.70, 0.55, 0.45, 0.25, 0.58]}
save(pd.DataFrame({"group": groups, **base}), "cascade_baseline.csv")


# ---- Whiteboard additions (v2) ----
# Staffing / retention per facility (MOCK): feeds providership stress + retention indicators.
ph = fac[fac.type == "PHC"][["facility_id"]].copy()
ph["posts_budgeted"] = rng.integers(4, 14, len(ph))
ph["posts_filled"] = (ph.posts_budgeted * rng.uniform(0.4, 1.0, len(ph))).astype(int)
ph["has_family_physician"] = rng.random(len(ph)) > 0.85          # paper cites 86.3% absent nationally
ph["staff_left_last_12m"] = rng.integers(0, 4, len(ph))
ph["referral_sent_month"] = rng.integers(10, 80, len(ph))
ph["referral_completed_month"] = (ph.referral_sent_month * rng.uniform(0.2, 0.7, len(ph))).astype(int)
save(ph, "staffing_referrals.csv")

# Governance capacity per district per year (MOCK; no public source: a scenario input the pilot would measure).
# Projection is deliberately modest: gains capped at 0.05/yr (docs/FEASIBILITY.md), not the old jump to MoPH-level capacity.
yrs = list(range(2019, 2031)); gc = []
for d in districts:
    base = rng.uniform(0.3, 0.45)
    prev = None
    for y in yrs:
        if y <= 2026:
            dip = 0.2 if y in (2020, 2021, 2024, 2026) else 0
            val = base - dip + 0.02 * (y - 2019) + rng.normal(0, 0.02)
        else:
            val = prev + min(0.03, 0.05)
        val = round(min(1, max(0, val)), 3); prev = val
        gc.append({"district": d, "year": y, "projected": y > 2026, "admin_capacity_index": val,
                   "share_funds_managed_locally": round(min(1, max(0, 0.15 + 0.03 * max(0, y - 2026) + rng.normal(0, 0.02))), 3),
                   "transparent_reporting": bool(rng.random() > 0.5)})
save(pd.DataFrame(gc), "governance_capacity.csv")

print("MOCK data written to", OUT)
