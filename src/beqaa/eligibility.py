"""Funding & eligibility assistant (structured, retrieval-only; chat is an optional layer on top).

1. eligible_funds(profile): which registry rows a local organisation can apply to now (and which closed annual calls to expect next round), with the reason for each.
2. threshold_gaps(inputs): where an organisation stands on the escrow ladder and what it needs to move up a rung (transparent reporting, referral completion, posts filled, capacity).
3. uncovered_priority_cadasters(): high-need cadasters and whether a funded partner is known there. FTS and LHF data carry NO sub-national location (all flows are tagged LBN), so partner
   presence is reported as 'unknown (Health Sector 4W not public)': never guessed.
Everything shown comes from a registry row or an escrow parameter; nothing is invented. Eligibility is read from the registry's `local_org_eligible`, `status`, `channel` and notes (keyword
heuristic for women-only funds), so every `to_verify` stays a 'check' and not a 'yes'.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import escrow, funding_finder as ff

WOMEN_KEYS = ("women", "feminist", "girls", "gender")
ORG_TYPES = ["Local NGO / community group", "Women-led organisation", "Municipality / Union of Municipalities", "Farmer cooperative", "University / research centre"]


@dataclass
class Profile:
    org_type: str = ORG_TYPES[0]
    women_led: bool = False
    district: str = "Baalbek"
    registered_in_lebanon: bool = True


def registry_last_verified(f: pd.DataFrame | None = None) -> dict:
    f = f if f is not None else ff.load_funding()
    v = pd.to_datetime(f.verified_on, errors="coerce")
    n_tv = int((f.status == "to_verify").sum())
    return {"last_verified": None if v.dropna().empty else v.max().date().isoformat(), "oldest_verified": None if v.dropna().empty else v.min().date().isoformat(),
            "rows": len(f), "to_verify_rows": n_tv, "stale_rows": int(ff.annotate(f).verified_stale.sum())}


def _text(r) -> str:
    return " ".join(str(x) for x in (r.name, r.sectors, r.notes, r.how_to_access) if pd.notna(x)).lower()


def eligible_funds(profile: Profile, show_next_round: bool = True, f: pd.DataFrame | None = None) -> pd.DataFrame:
    f = ff.annotate(f if f is not None else ff.load_funding())
    keep = {"verified", "to_verify"} | ({"closed_recurring"} if show_next_round else set())
    rows = []
    muni = profile.org_type.startswith("Municipality")
    for r in f[f.status.isin(keep)].itertuples():
        txt = _text(r)
        women_only = any(k in (str(r.name).lower() + " " + str(r.sectors).lower()) for k in WOMEN_KEYS)
        elig = str(r.local_org_eligible) if pd.notna(r.local_org_eligible) else "to_verify"
        why, verdict = [], None
        if r.channel == "gov" and not muni:
            if elig != "yes":
                continue                                                       # government-to-government money: not open to a local NGO
        if elig == "no" and not muni:
            continue
        if women_only and not profile.women_led:
            continue                                                           # restricted to women-led organisations
        if women_only:
            why.append("open to women-led organisations")
        if elig == "yes":
            verdict, _ = "eligible", why.append("registry: local organisations eligible")
        elif elig == "partial":
            verdict = "conditional"
            why.append("registry: partly open to local organisations (check the condition in the notes)")
        else:
            verdict = "check eligibility"
            why.append("registry: local-organisation eligibility not yet verified")
        if r.channel in ff.POOLABLE_CHANNELS:
            why.append("money that could sit in the escrow window")
        when = "expected next round (this round closed)" if r.status == "closed_recurring" else str(r.availability)
        rows.append({"fund_id": r.fund_id, "name": r.name, "funder": r.funder, "eligibility": verdict, "why": "; ".join(why), "status": when, "involvement_level": r.involvement_level,
                     "how_to_access": r.how_to_access, "url": r.url, "verified_on": r.verified_on, "registry_status": r.status})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    order = {"eligible": 0, "conditional": 1, "check eligibility": 2}
    return out.assign(_o=out.eligibility.map(order), _n=out.status.str.startswith("expected")).sort_values(["_n", "_o"]).drop(columns=["_o", "_n"]).reset_index(drop=True)


def threshold_gaps(capacity_index: float, transparent_reporting: bool, referral_completion: float, posts_filled: float) -> dict:
    """Where the organisation sits on the ladder and the gap to the next rung. Thresholds come from data/params/escrow_params.yaml (assumptions unless noted there)."""
    rules = escrow.DEFAULT_RULES
    rung = escrow.level_for(capacity_index)
    i = escrow.LEVELS.index(rung)
    nxt = escrow.LEVELS[min(i + 1, len(escrow.LEVELS) - 1)]
    need_cap = float(escrow.LADDER.set_index("level").loc[nxt, "min_capacity"])
    checks = [{"requirement": "Capacity index (administrator rung)", "yours": round(capacity_index, 3), "required": need_cap if nxt != rung else None,
               "met": nxt == rung or capacity_index >= need_cap, "gap": None if nxt == rung else round(max(0.0, need_cap - capacity_index), 3), "what_it_unlocks": f"{nxt} rung"},
              {"requirement": "Capacity tranche: capacity index at least", "yours": round(capacity_index, 3), "required": rules["admin_capacity_min"], "met": capacity_index >= rules["admin_capacity_min"],
               "gap": round(max(0.0, rules["admin_capacity_min"] - capacity_index), 3), "what_it_unlocks": "capacity tranche released"},
              {"requirement": "Transparent reporting (published quarterly spend + third-party spot check)", "yours": transparent_reporting, "required": bool(rules["transparent_required"]),
               "met": transparent_reporting or not rules["transparent_required"], "gap": None, "what_it_unlocks": "capacity tranche released"},
              {"requirement": "Referral completion at least", "yours": round(referral_completion, 2), "required": rules["referral_min"], "met": referral_completion >= rules["referral_min"],
               "gap": round(max(0.0, rules["referral_min"] - referral_completion), 2), "what_it_unlocks": "capacity tranche released"},
              {"requirement": "Budgeted posts filled at least", "yours": round(posts_filled, 2), "required": rules["posts_filled_min"], "met": posts_filled >= rules["posts_filled_min"],
               "gap": round(max(0.0, rules["posts_filled_min"] - posts_filled), 2), "what_it_unlocks": "capacity tranche released"}]
    t = pd.DataFrame(checks)
    return {"current_rung": rung, "next_rung": nxt, "table": t, "all_tranche_thresholds_met": bool(t.iloc[1:].met.all()), "gaps": t[~t.met]}


def uncovered_priority_cadasters(scored: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """High-need cadasters with their access picture and the (unknown) partner presence. Funded-partner locations are not public (needs Health Sector 4W/5W)."""
    t = scored.nsmallest(top, "rank")[["cadaster_name", "district", "need_score", "access_deficit", "D_environment", "phc_30"]].copy()
    t["partner_presence"] = "unknown (Health Sector 4W not public; FTS/LHF are national only)"
    t["open_facilities_within_30_min"] = t.phc_30
    return t.drop(columns="phc_30")
