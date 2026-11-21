"""Filter + rank registry entries against current priorities. Sources: data/registry/*.csv (never invented)."""
from __future__ import annotations

import pandas as pd

from .io import ROOT

REG = ROOT / "data" / "registry"
TODAY = pd.Timestamp("2026-11-21")          # project 'now'; pass `today` to override


def load_funding() -> pd.DataFrame:
    return pd.read_csv(REG / "funding_registry.csv")


def load_orgs() -> pd.DataFrame:
    return pd.read_csv(REG / "org_registry.csv")


def annotate(f: pd.DataFrame, today: pd.Timestamp = TODAY, months: int = 6) -> pd.DataFrame:
    f = f.copy()
    cutoff = today - pd.DateOffset(months=months)
    ann = pd.to_datetime(f.announced_date, errors="coerce", format="mixed")
    end = pd.to_datetime(f.period_end, errors="coerce")
    ver = pd.to_datetime(f.verified_on, errors="coerce")
    f["announced_recent"] = ann >= cutoff
    f["still_active"] = end >= today
    f["verified_stale"] = ver < cutoff
    f["recency_flag"] = "older than 6 months"
    f.loc[f.still_active | f.announced_recent, "recency_flag"] = "active or recent"
    f.loc[(end < today) & ~f.announced_recent, "recency_flag"] = "expired / older than 6 months"
    f["can_pool"] = f.channel.isin(["gov", "UN_pooled"])
    f["fits_escrow"] = f.apply(lambda r: "yes" if r.can_pool and r.local_org_eligible == "yes" else
                               ("maybe: confirm local-org eligibility" if r.can_pool and r.local_org_eligible == "to_verify" else
                                "no: " + ("government-only" if r.local_org_eligible == "no" else "cannot be pooled")), axis=1)
    return f


def rank(f: pd.DataFrame, sectors: list[str], geography: str | None = None) -> pd.DataFrame:
    f = f.copy()
    sec = f.sectors.fillna("").str.lower()
    f["sector_match"] = sec.apply(lambda s: sum(k.lower() in s for k in sectors))
    geo = f.geography.fillna("").str.lower()
    f["geo_match"] = geo.apply(lambda g: int(geography is None or geography.lower() in g or "lebanon" in g))
    f["score"] = (2 * f.sector_match + f.geo_match + 2 * f.still_active.astype(int) + f.announced_recent.astype(int)
                  + (f.local_org_eligible == "yes").astype(int) + f.can_pool.astype(int))
    return f.sort_values("score", ascending=False)


def filter_funding(f: pd.DataFrame, channels=None, local_only=False, active_only=True, min_amount=0) -> pd.DataFrame:
    g = f
    if channels:
        g = g[g.channel.isin(channels)]
    if local_only:
        g = g[g.local_org_eligible.isin(["yes", "to_verify"])]
    if active_only:
        g = g[g.recency_flag == "active or recent"]
    if min_amount:
        g = g[g.amount.fillna(0) >= min_amount]
    return g
