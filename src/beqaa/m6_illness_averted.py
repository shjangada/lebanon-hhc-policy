"""M6: reported illness averted and cost-effectiveness of the prevention package (water treatment) for settlement households.

Baseline  reported hepatitis A + typhoid cases by caza, mean 2023-2025 (MoPH ESU; notified cases, under-reporting NOT corrected; 2026 is a partial year, late-2025 zeros are lag).
          National acute watery diarrhoea (WHO briefs) is context only.
Effects   Wolf et al. 2022 relative risks for DIARRHOEA in children in low- and middle-income countries (TRANSFERRED evidence): point-of-use filtration 0.50 [0.41-0.60], chlorination 0.66 [0.56-0.77],
          handwashing with soap 0.70 [0.64-0.76], sewer connection 0.53 [0.30-0.93]. Hepatitis A and typhoid share the faecal-oral route but the same RR is an ASSUMPTION: a transfer slider scales the
          effect (1.0 = same RR as diarrhoea; 0 = no effect), default 1.0, range 0-1.
Coverage  share of the district population reached (slider); cases are assumed proportional to population (no settlement-specific incidence exists).
Outputs   (Monte Carlo over the RR confidence interval and the transfer slider) reported cases averted per year, primary-care visits avoided at $20.03 per service (K2P/UNICEF 2022), cost per case
          averted, and the break-even visits per case at which avoided visit costs cover the package (cost and benefit both scale with coverage).
Package   2026 UNICEF catalogue prices: ceramic filter per household (one-off) and NaDCC tablets per household-month, plus sourced CHW months; the 2002 cost per person (filtration $3.03, chlorination $0.66)
          is shown as the LOW bound and is NOT inflated here (it would be higher)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import riders, start_site
from .io import PROCESSED, load_dataset

RR = {"filtration": (0.50, 0.41, 0.60), "chlorination": (0.66, 0.56, 0.77), "handwashing": (0.70, 0.64, 0.76), "sewer connection": (0.53, 0.30, 0.93)}
VISIT_COST = 20.03          # USD per primary-care service (K2P/UNICEF 2022; cost_ranges 2a)
HH_SIZE = 5


def baseline_cases(esu: pd.DataFrame | None = None) -> pd.Series:
    d = esu if esu is not None else pd.read_csv(PROCESSED / "esu_by_district.csv")
    d = d[(d.mohafaza_file == "Bekaa") & (d.geo_level == "caza") & d.year.between(2023, 2025) & d.disease.str.contains("Hepatitis A|Typhoid", case=False, regex=True)]
    return d.groupby(["district_clean", "year"]).cases.sum().groupby("district_clean").mean()


def package_cost_per_person_year(measure: str = "filtration", prices: pd.DataFrame | None = None) -> tuple[float, float, float]:
    """(low, central, high) USD per person-year. Filtration: catalogue filter per household over 3 years (assumed lifetime) plus no running cost; chlorination: NaDCC tablets per household-month."""
    pk = prices if prices is not None else pd.read_csv(PROCESSED / "prices_pack.csv")
    if measure == "chlorination":
        c = float(pk[pk["item"].str.startswith("NaDCC 33 mg")].central.iloc[0])
        return (0.66, c * 12 / HH_SIZE, c * 12 / HH_SIZE * 1.0)               # low = 2002 cost per person (not inflated)
    f = pk[pk["item"].str.startswith("Household ceramic water filter")].iloc[0]
    life = 3.0                                                                 # years: ASSUMPTION (filter lifetime)
    return (3.03, float(f.central) / HH_SIZE / life, float(f.high) / HH_SIZE / life * 1.0)


def simulate(district: str, people_reached: float, district_pop: float, measure: str = "filtration", transfer: float = 1.0, n: int = 5000, seed: int = 42,
             visits_per_case: float = 1.0, chw_months: float = 6.0, esu: pd.DataFrame | None = None) -> dict:
    rng = np.random.default_rng(seed)
    base = float(baseline_cases(esu).get(district, np.nan))
    rr, lo, hi = RR[measure]
    sd = (np.log(hi) - np.log(lo)) / (2 * 1.96)
    rr_s = np.exp(rng.normal(np.log(rr), sd, n))
    effect = (1 - rr_s) * transfer                                           # share of cases averted among those covered
    cov = people_reached / district_pop
    averted = base * cov * effect
    chw = riders.unit_prices().set_index("unit").loc["chw_month", "usd_central"] * chw_months
    low, cen, high = package_cost_per_person_year(measure)
    cost = people_reached * cen + chw
    cost_lo, cost_hi = people_reached * low + chw, people_reached * high + chw
    visits_saved = averted * visits_per_case * VISIT_COST
    q = lambda a, p: float(np.percentile(a, p))
    cpa = np.where(averted > 0, cost / np.maximum(averted, 1e-9), np.nan)
    return {"district": district, "measure": measure, "baseline_cases_per_year": base, "coverage_of_district": cov, "package_cost_usd": cost, "package_cost_range_usd": (cost_lo, cost_hi),
            "cases_averted_p05": q(averted, 5), "cases_averted_median": q(averted, 50), "cases_averted_p95": q(averted, 95),
            "visits_cost_avoided_median_usd": q(visits_saved, 50), "cost_per_case_averted_median": float(np.nanmedian(cpa)),
            "cost_per_case_averted_p05": float(np.nanpercentile(cpa, 5)), "cost_per_case_averted_p95": float(np.nanpercentile(cpa, 95)),
            "visits_per_case_to_break_even": float(np.nanmedian(cpa)) / VISIT_COST,   # cost and benefit both scale with coverage, so coverage cannot break even: visits per case can
            "note": "reported (notified) cases; under-reporting not corrected; RR transferred from child diarrhoea in LMICs (Wolf 2022)"}


def table(coverages=(0.05, 0.10, 0.25), measure: str = "filtration", transfer: float = 1.0) -> pd.DataFrame:
    pop = load_dataset("population").df.merge(load_dataset("cadasters").df[["cadaster_id", "district"]], on="cadaster_id").groupby("district").population_total.sum()
    rows = [simulate(d, pop[d] * c, pop[d], measure, transfer) | {"coverage": c} for d in pop.index for c in coverages]
    return pd.DataFrame(rows)
