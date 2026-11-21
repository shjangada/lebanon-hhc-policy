"""Filter + rank registry entries against current priorities. Sources: data/registry/*.csv (never invented).

Registry statuses (funding_registry.csv `status`):
  verified              - checked on the funder's own page; usable
  to_verify             - found via a secondary source/aggregator; confirm before citing
  closed_recurring      - this round is closed but the call recurs (annual etc.): shown only as "expected next round"
  active_closed_to_new  - money is flowing but partners are already selected: evidence the channel works, not an opportunity
  closed                - closed, no known next round: hidden by default
Nothing here creates rows: every result is a registry row with its URL and verified_on date.
"""
from __future__ import annotations

import pandas as pd

from .io import ROOT

REG = ROOT / "data" / "registry"
TODAY = pd.Timestamp("2026-11-21")          # project 'now'; pass `today` to override

STATUSES = ["verified", "to_verify", "closed_recurring", "active_closed_to_new", "closed"]
AVAILABILITY = {
    "verified": "open / active",
    "to_verify": "open / active (verify)",
    "closed_recurring": "expected next round",
    "active_closed_to_new": "active, closed to new partners",
    "closed": "closed",
}
POOLABLE_CHANNELS = {"gov", "UN_pooled", "pooled_fund"}          # money that could sit in a ring-fenced pooled window
DIRECT_LOCAL_CHANNELS = {"local_ngo"}                            # grants straight to local/women-led orgs (complements the pool)
# Donor-involvement / community-decision fit. Lower donor involvement (core, flexible, institutional funding) ranks highest
# because it lets the community committee decide use. Ordering is a team judgement (assumption), not data.
FIT_SCORE = {"high": 3, "medium": 2, "low": 1, "to_verify": 0}
LOW_INVOLVEMENT_KEYWORDS = ("core", "flexible", "institutional", "general support", "trust-based", "unrestricted")


def load_funding() -> pd.DataFrame:
    f = pd.read_csv(REG / "funding_registry.csv")
    for c, default in (("community_decision_fit", "to_verify"), ("community_decision_note", ""), ("period_end", None)):
        if c not in f.columns:
            f[c] = default
    f["community_decision_fit"] = f.community_decision_fit.fillna("to_verify")
    return f


def load_orgs() -> pd.DataFrame:
    return pd.read_csv(REG / "org_registry.csv")


def load_datasets() -> pd.DataFrame:
    """Funding-flow data sources (D01-D11): where to pull real allocation/flow data from. Not grants."""
    return pd.read_csv(REG / "funding_datasets.csv")


def _low_involvement(r) -> bool:
    # sectors + the curated community_decision_note only (free-text notes give false hits, e.g. "institutional reform")
    txt = " ".join(str(x) for x in (r.sectors, r.community_decision_note) if pd.notna(x)).lower()
    return any(k in txt for k in LOW_INVOLVEMENT_KEYWORDS)


def annotate(f: pd.DataFrame, today: pd.Timestamp = TODAY, months: int = 6) -> pd.DataFrame:
    f = f.copy()
    cutoff = today - pd.DateOffset(months=months)
    ann = pd.to_datetime(f.announced_date.astype("string"), errors="coerce", format="mixed")
    end = pd.to_datetime(f.period_end, errors="coerce")
    ver = pd.to_datetime(f.verified_on, errors="coerce")
    rolling = f.period.astype(str).str.lower().str.contains("rolling")
    f["announced_recent"] = (ann >= cutoff).fillna(False)
    f["still_active"] = ((end >= today) | rolling).fillna(False)
    f["verified_stale"] = (ver < cutoff).fillna(True)
    f["recency_flag"] = "older than 6 months"
    f.loc[f.still_active | f.announced_recent, "recency_flag"] = "active or recent"
    f.loc[(end < today) & ~f.announced_recent, "recency_flag"] = "expired / older than 6 months"
    f["availability"] = f.status.map(AVAILABILITY).fillna("unknown status")
    openish = f.status.isin(["verified", "to_verify"])
    f.loc[openish & (f.recency_flag != "active or recent"), "availability"] = "outside 6-month window (" + f.status + ")"
    # a registry 'closed' status overrides dates
    f.loc[f.status.isin(["closed", "closed_recurring", "active_closed_to_new"]), "recency_flag"] = f.availability
    f["can_pool"] = f.channel.isin(POOLABLE_CHANNELS)
    elig = f.local_org_eligible.fillna("to_verify")

    def _fit(r, e):
        if r.channel in DIRECT_LOCAL_CHANNELS:
            return "no: direct grant to local orgs (complements the pool; community committee can apply)"
        if r.can_pool and e == "yes":
            return "yes"
        if r.can_pool and e in ("to_verify", "partial"):
            return "maybe: confirm local-org eligibility"
        return "no: " + ("government-only" if e == "no" else "cannot be pooled")
    f["fits_escrow"] = [_fit(r, e) for r, e in zip(f.itertuples(), elig)]
    f["low_donor_involvement"] = [_low_involvement(r) for r in f.itertuples()]
    f["involvement_score"] = f.community_decision_fit.map(FIT_SCORE).fillna(0) + f.low_donor_involvement.astype(int) * 2
    f["involvement_level"] = pd.cut(f.involvement_score, [-1, 0.5, 1.5, 2.5, 99],
                                    labels=["unknown (verify)", "high donor involvement", "medium", "low donor involvement (community decides)"]).astype(str)
    return f


def rank(f: pd.DataFrame, sectors: list[str], geography: str | None = None) -> pd.DataFrame:
    """Priority match: sector fit, geography, open now, local eligibility, poolability, plus community-decision fit."""
    f = f.copy()
    sec = (f.sectors.fillna("") + " " + f.notes.fillna("")).str.lower()
    f["sector_match"] = sec.apply(lambda s: sum(k.lower() in s for k in sectors))
    geo = f.geography.fillna("").str.lower()
    f["geo_match"] = geo.apply(lambda g: int(geography is None or geography.lower() in g or "lebanon" in g))
    inv = f["involvement_score"] if "involvement_score" in f else 0
    f["score"] = (2 * f.sector_match + f.geo_match + 2 * f.still_active.astype(int) + f.announced_recent.astype(int)
                  + (f.local_org_eligible == "yes").astype(int) + f.can_pool.astype(int) + 0.5 * inv)
    return f.sort_values("score", ascending=False)


def rank_involvement(f: pd.DataFrame, sectors: list[str] | None = None) -> pd.DataFrame:
    """Community-decision ranking: core / flexible / institutional funding (lowest donor involvement) first,
    then community_decision_fit, then sector match. Ties broken by priority score."""
    g = rank(f, sectors or ["health"]) if "score" not in f else f.copy()
    return g.sort_values(["involvement_score", "sector_match", "score"], ascending=False)


def filter_funding(f: pd.DataFrame, channels=None, local_only=False, active_only=True, min_amount=0,
                   show_next_round: bool = False, show_closed: bool = False, show_closed_to_new: bool = False) -> pd.DataFrame:
    """Default: open/active rows only. `show_next_round` adds closed_recurring rows (labelled 'expected next round');
    `show_closed_to_new` adds channels that are running but not taking partners; `show_closed` adds closed rows."""
    g = f
    keep = {"verified", "to_verify"} | ({"closed_recurring"} if show_next_round else set()) | \
           ({"active_closed_to_new"} if show_closed_to_new else set()) | ({"closed"} if show_closed else set())
    g = g[g.status.isin(keep)]
    if channels:
        g = g[g.channel.isin(channels)]
    if local_only:
        g = g[g.local_org_eligible.isin(["yes", "to_verify", "partial"])]
    if active_only:
        g = g[(g.recency_flag == "active or recent") | (g.status != "verified") & (g.status != "to_verify")]
    if min_amount:
        g = g[g.amount.fillna(0) >= min_amount]
    return g


def match_sectors(f: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """Registry rows whose sectors/notes mention any keyword (used to link research gaps to fundable rows)."""
    txt = (f.sectors.fillna("") + " " + f.notes.fillna("") + " " + f.name.fillna("")).str.lower()
    hit = txt.apply(lambda s: [k for k in keywords if k.lower() in s])
    out = f.assign(matched_keywords=hit.apply("; ".join))
    return out[hit.apply(len) > 0]
