"""Surveillance, care-flow and evidence packs (new data: data/raw/surveillance, data/raw/care_flow, data/raw/evidence) -> data/processed.

ESU (MoPH Epidemiological Surveillance Unit): reported (notified) cases, suspected and confirmed mixed, no denominator, under-reporting varies. The 'Bekaa' file is the OLD Beqaa
mohafaza (it includes the Hermel and Baalbeck cazas). 2026 runs to August only (as on 07/08/2026); Oct-Dec 2025 zeros are REPORTING LAG, not true zeros: both are flagged
(`reporting_lag`). WHO health-brief rows are PDF extractions; the disease label of the 'new suspected' line is inferred (flag kept in `note`). The WBD risk map has no district values
(2025 image) and equal 0.1 weights (2024 update): cadaster names are matched to COD-AB p-codes and unmatched names are logged, never guessed. Informal settlements are Dec 2016 (labelled).
Waiting times and referral completion were NOT FOUND: they stay pilot measures."""
from __future__ import annotations

import difflib
import re
import unicodedata

import pandas as pd

from .common import PROCESSED, RAW, log_unmatched, provenance

S, C, E = RAW / "surveillance", RAW / "care_flow", RAW / "evidence"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CAZA_TO_DISTRICT = {"Hermel": "Hermel", "Baalbeck": "Baalbek", "Zahleh": "Zahle", "West-Bekaa": "West Bekaa", "Rashaya": "Rachaya"}


def _n(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)))


def match_cadasters(names: pd.Series, districts: pd.Series, cad: pd.DataFrame) -> pd.Series:
    """COD-AB p-code by normalised name within the district, then a fuzzy match (>= 0.85) inside the district; else NaN (logged by the caller)."""
    out = []
    for nm, dist in zip(names, districts):
        pool = cad[cad.district == dist] if dist in set(cad.district) else cad
        key = {_n(r.cadaster_name): r.cadaster_id for r in pool.itertuples()}
        k = _n(nm)
        if k in key:
            out.append(key[k])
            continue
        m = difflib.get_close_matches(k, list(key), n=1, cutoff=0.85)
        out.append(key[m[0]] if m else None)
    return pd.Series(out, index=names.index)


def read_loose(path) -> pd.DataFrame:
    """Read a CSV whose text fields contain unquoted commas: rows with extra fields are folded into the LAST column (notes); short rows are padded. The raw file is untouched and the
    number of repaired rows is kept in the `repaired` column of the output."""
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    head, body = rows[0], rows[1:]
    out, fixed = [], []
    for r in body:
        fixed.append(len(r) != len(head))
        r = r[:len(head) - 1] + [",".join(r[len(head) - 1:])] if len(r) > len(head) else r + [""] * (len(head) - len(r))
        out.append(r)
    d = pd.DataFrame(out, columns=head)
    d["repaired"] = fixed
    return d.replace("", pd.NA)


def esu() -> dict:
    m = pd.read_csv(S / "esu_by_month.csv")
    m["is_total"] = m.month.eq("TOTAL")
    last = m[(m.year == 2026) & (m.mohafaza_file != "Lebanon") | (m.year == 2026) & (m.mohafaza_file == "Lebanon")]
    m["reporting_lag"] = ((m.year == 2026) & m.month.isin(["Aug"]) & ~m.is_total) | ((m.year == 2025) & m.month.isin(["Oct", "Nov", "Dec"]) & ~m.is_total) | \
                         ((m.year == 2026) & m.month.isin(["Sep", "Oct", "Nov", "Dec"]) & ~m.is_total)
    m["note"] = m.reporting_lag.map({True: "partial or lagged period (2026 runs to Aug; Oct-Dec 2025 zeros are reporting lag)", False: ""})
    d = pd.read_csv(S / "esu_by_district.csv")
    d["district_clean"] = d.district.map(CAZA_TO_DISTRICT)
    a = pd.read_csv(S / "esu_by_age_sex.csv")
    src = "MoPH ESU reported cases (notified, suspected+confirmed mixed; no denominator; under-reporting varies); 'Bekaa' = old Beqaa mohafaza"
    url = "https://www.moph.gov.lb/en/Pages/2/193/esudata"
    provenance(m, src, "2026-08-07", "partial", url, "ESU").to_csv(PROCESSED / "esu_by_month.csv", index=False)
    provenance(d, src, "2026-08-07", "partial", url, "ESU").to_csv(PROCESSED / "esu_by_district.csv", index=False)
    provenance(a, src, "2026-08-07", "partial", url, "ESU").to_csv(PROCESSED / "esu_by_age_sex.csv", index=False)
    return {"esu_month_rows": len(m), "esu_district_rows": len(d), "esu_age_sex_rows": len(a)}


def who_and_risk(cad: pd.DataFrame) -> dict:
    w = read_loose(S / "who_health_briefs_wbd.csv")
    w["value"] = pd.to_numeric(w["value"], errors="coerce")
    provenance(w, "WHO Lebanon Health Briefs Apr 2025 to May 2026 (PDF text extraction; disease label of the 'new suspected' line inferred)", "2026-05", "partial", "https://www.emro.who.int/lebanon", "WHO-HB").to_csv(PROCESSED / "who_wbd.csv", index=False)
    r = read_loose(S / "wbd_risk_map.csv")
    r["cadaster_id"] = match_cadasters(r.name, r.district, cad)
    log_unmatched("wbd_risk", "cadaster", r[r.cadaster_id.isna() & r.geo_level.eq("cadaster") & r.in_beqaa_valley.eq("yes")].name, "WBD risk-map cadaster not matched to COD-AB; left unknown")
    provenance(r, "WaSH Sector water-borne-disease risk map (2024 update: top-20 cadasters, equal 0.1 weights; 2025 map has no district values)", "2025", "partial", "https://data.unhcr.org/ar/documents/download/109156", "WBD").to_csv(PROCESSED / "wbd_risk.csv", index=False)
    return {"who_rows": len(w), "wbd_rows": len(r), "wbd_beqaa_matched": int(r[r.in_beqaa_valley.eq("yes")].cadaster_id.notna().sum())}


def care_flow(cad: pd.DataFrame) -> dict:
    s = read_loose(C / "informal_settlements_by_cadaster_2016.csv")
    for c_ in ("n_sites_active_or_lt4", "n_active", "n_less_than_4_tents", "tents", "individuals", "mean_lat", "mean_lon", "n_sites_water_source_trucking"):
        s[c_] = pd.to_numeric(s[c_], errors="coerce")
    s["cadaster_id"] = match_cadasters(s.cadaster, s.district, cad)
    log_unmatched("informal_settlements", "cadaster", s[s.cadaster_id.isna()].cadaster, "IAMP 2016 cadaster not matched to COD-AB; settlements not assigned")
    provenance(s.assign(data_year=2016), "UNHCR/OCHA IAMP sweep 34, Dec 2016 (HDX): the latest public site-level list; OLD (2016)", "2016-12-29", "partial",
               "https://data.humdata.org/dataset/informal-settlements-refugees-living-in-informal-settlements", "IAMP").to_csv(PROCESSED / "informal_settlements.csv", index=False)
    out = {"settlements": len(s), "settlements_matched": int(s.cadaster_id.notna().sum())}
    for name, f, src, url in (("outreach", "outreach_services.csv", "MSF, Amel, MoPH/WHO, UNICEF outreach services (no published visit frequency)", ""),
                              ("referral_payers", "referral_payers.csv", "who pays for what by population group (UNHCR hospital support ended 1 Dec 2025; no payer found for unregistered Syrians)", ""),
                              ("wash", "wash_activities.csv", "WaSH Sector ITS activities and water-quality findings (72% of tested Baalbek-Hermel ITS samples faecally contaminated, Jul 2026)", ""),
                              ("capacity_waittime", "capacity_waittime.csv", "PHCC counts, volumes, access percentages; waiting times and referral completion NOT FOUND", "")):
        d = read_loose(C / f)
        provenance(d, src, "2026-11-21", "partial", url, "CARE").to_csv(PROCESSED / f"{name}.csv", index=False)
        out[name] = len(d)
    return out


def evidence_pack() -> dict:
    e = read_loose(E / "evidence.csv")
    p = pd.concat([read_loose(E / "prices.csv"), read_loose(E / "prices_extra.csv")], ignore_index=True)     # prices_extra: AUB lab prices read from the AUB price list
    provenance(e, "Evidence pack: 37 claims with rung, geography and verification flag", "2026-11-21", "to_verify", "see url per row", "EVD").to_csv(PROCESSED / "evidence_pack.csv", index=False)
    provenance(p, "Price pack: 20 rows; unverified prices stay sliders", "2026-11-21", "to_verify", "see url per row", "PRC").to_csv(PROCESSED / "prices_pack.csv", index=False)
    return {"evidence": len(e), "prices": len(p), "evidence_verified_flag": e.verified.value_counts().to_dict()}


def run() -> dict:
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})
    return {**esu(), **who_and_risk(cad), **care_flow(cad), **evidence_pack()}
