"""Beqaa health funding proxy and partner presence (new_data pack, data/raw/beqaa_funding).

beqaa_funding_proxy.csv           LHF (CBPF) health-titled projects whose TITLE names a Bekaa / Baalbek-Hermel place, by recipient type and year, plus national denominators.
                                  CAVEATS (from the pack): full project budgets (multi-governorate projects not apportioned); geography from title keywords only, so projects in
                                  Beqaa that do not name it are MISSED; 'health' includes multi-sector titles and one WASH project. A PROXY, not a measured Beqaa share.
beqaa_lhf_national_ngo_share_by_year.csv   national-NGO share of Beqaa-titled LHF health money vs the same share nationally, by year.
beqaa_health_partners.csv         49 organisations (39 operate the MoPH-network PHCCs of 16/04/2026, all Lebanese; plus INGOs/NNGOs/UN). women_led is UNKNOWN for all.
org_registry.csv                  partners are appended (status to_verify, women_led to_verify) unless the name is already there.
No 4W by governorate exists publicly: a measured Beqaa share cannot be computed, so every use is labelled 'proxy'."""
from __future__ import annotations

import re

import pandas as pd

from .common import PROCESSED, RAW, ROOT, provenance

SRC = RAW / "beqaa_funding"
URL = "https://data.humdata.org/dataset/cbpf-allocations-and-contributions"
TYPE_MAP = {"NNGO (Lebanese association)": "local NGO", "NNGO": "local NGO", "INGO": "international NGO", "Local government (municipality)": "municipality",
            "Lebanese religious institution": "Lebanese religious institution", "National Red Cross society": "local NGO"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z؀-ۿ]", "", str(s).lower())


def share_table(f: pd.DataFrame) -> pd.DataFrame:
    f = f[f.recipient_type.isin(["International NGO", "National NGO"])]
    f = f.assign(scope=f.governorate.str.startswith("Bekaa").map({True: "beqaa_titled_proxy", False: "national"}))
    p = f.pivot_table(index=["year", "scope"], columns="recipient_type", values="amount_usd", aggfunc="sum", fill_value=0.0).reset_index()
    p["total_usd"] = p["International NGO"] + p["National NGO"]
    p["national_ngo_share"] = p["National NGO"] / p["total_usd"]
    return p.rename(columns={"International NGO": "ingo_usd", "National NGO": "nngo_usd"})


def append_registry(partners: pd.DataFrame) -> int:
    path = ROOT / "data" / "registry" / "org_registry.csv"
    reg = pd.read_csv(path, dtype=str).fillna("")
    have = {_norm(n) for n in reg.name}
    n0 = int(reg.org_id.str[1:].astype(int).max()) if len(reg) else 0
    rows = []
    for r in partners.itertuples():
        if r.org_type.startswith(("Government (MoPH", "Government (MoSA")) or r.org_type == "UN":
            continue                                   # state actors and UN agencies are not funding-eligible partners; they are in the escrow ladder, not this registry
        if _norm(r.org_name) in have or any(_norm(r.org_name).startswith(h) or h.startswith(_norm(r.org_name)) for h in have if len(h) > 6):
            continue
        n0 += 1
        have.add(_norm(r.org_name))
        rows.append({"org_id": f"O{n0:03d}", "name": r.org_name, "type": TYPE_MAP.get(r.org_type, r.org_type),
                     "geography": f"{r.governorates} ({r.districts})", "sectors": "primary health care", "works_with_unregistered_workers": "to_verify",
                     "women_led": "to_verify", "contact_route": "", "url": r.source_url, "status": "to_verify",
                     "notes": f"{r.activities} (partners file, retrieved 2026-11-21; women_led and everything else unverified)", "community_decision_fit": "to_verify"})
    if rows:
        pd.concat([reg, pd.DataFrame(rows)], ignore_index=True).to_csv(path, index=False)
    return len(rows)


def run() -> dict:
    f = pd.read_csv(SRC / "beqaa_funding_by_recipient_type.csv")
    provenance(f, "LHF/CBPF health-titled projects naming Bekaa/Baalbek-Hermel (title keyword proxy), full budgets; plus national denominators", "2026-11-21", "partial", URL, "BQF").to_csv(PROCESSED / "beqaa_funding_proxy.csv", index=False)
    s = share_table(f)
    provenance(s, "National-NGO share of LHF health project budgets: Beqaa-titled projects (PROXY) vs national", "2026-11-21", "partial", URL, "BQF").to_csv(PROCESSED / "beqaa_lhf_national_ngo_share_by_year.csv", index=False)
    p = pd.read_csv(SRC / "beqaa_health_partners.csv")
    provenance(p, "MoPH PHCC list 16/04/2026 (operators) + LHF project titles + Health Sector contacts; women_led unknown", "2026-11-21", "partial", "https://www.moph.gov.lb/userfiles/files/HealthCareSystem/PHC/phcc-16-4-2026.pdf", "BQP").to_csv(PROCESSED / "beqaa_health_partners.csv", index=False)
    added = append_registry(p)
    b = s[s.scope == "beqaa_titled_proxy"].set_index("year").national_ngo_share
    return {"beqaa_proxy_share_by_year": {int(k): round(float(v), 3) for k, v in b.items()}, "partners": len(p), "added_to_org_registry": added}
