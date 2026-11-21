"""Tools the LLM assistant uses to loop through the registries. Pure functions over data/registry/*.csv.
Every row returned carries its id, URL and verified_on so the model can cite it. Nothing here invents data."""
from __future__ import annotations

import re

import pandas as pd

from . import funding_finder as ff
from .io import ROOT

STOP = set("the a an of for to in and or is are what which who how any can we do does with on from about funding fund grant grants".split())
FUND_COLS = ["fund_id", "name", "funder", "amount", "currency", "period", "period_end", "sectors", "geography", "channel", "local_org_eligible",
             "community_decision_fit", "involvement_level", "how_to_access", "url", "announced_date", "verified_on", "status", "availability",
             "recency_flag", "fits_escrow", "notes"]
ORG_COLS = ["org_id", "name", "type", "geography", "sectors", "works_with_unregistered_workers", "women_led", "community_decision_fit",
            "contact_route", "url", "status", "notes"]


def _tok(s) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", str(s).lower()) if t not in STOP and len(t) > 2}


def _clean(df: pd.DataFrame, cols) -> list[dict]:
    return [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in df[[c for c in cols if c in df.columns]].to_dict("records")]


def search_funding(query: str = "", channel: str | None = None, local_org_eligible: str | None = None, active_only: bool = False,
                   community_decision_fit: str | None = None, limit: int = 8, include_closed: bool = False) -> list[dict]:
    f = ff.annotate(ff.load_funding())
    if not include_closed:                       # 'closed' rows (no next round) are hidden; closed_recurring stays, labelled 'expected next round'
        f = f[f.status != "closed"]
    if channel:
        f = f[f.channel == channel]
    if local_org_eligible:
        f = f[f.local_org_eligible == local_org_eligible]
    if community_decision_fit:
        f = f[f.community_decision_fit == community_decision_fit]
    if active_only:
        f = f[f.recency_flag == "active or recent"]
    q = _tok(query)
    if q:
        f = f.assign(_s=[len(q & _tok(" ".join(map(str, (r.name, r.funder, r.sectors, r.geography, r.notes))))) for r in f.itertuples()])
        f = f[f._s > 0].sort_values("_s", ascending=False)
    return _clean(f.head(limit), FUND_COLS)


def search_orgs(query: str = "", community_decision_fit: str | None = None, limit: int = 8) -> list[dict]:
    o = ff.load_orgs()
    if community_decision_fit:
        o = o[o.community_decision_fit == community_decision_fit]
    q = _tok(query)
    if q:
        o = o.assign(_s=[len(q & _tok(" ".join(map(str, (r.name, r.type, r.geography, r.sectors, r.notes))))) for r in o.itertuples()])
        o = o[o._s > 0].sort_values("_s", ascending=False)
    return _clean(o.head(limit), ORG_COLS)


def get_entry(entry_id: str) -> dict | None:
    f = ff.annotate(ff.load_funding())
    hit = f[f.fund_id == entry_id]
    if len(hit):
        return _clean(hit, FUND_COLS)[0]
    o = ff.load_orgs()
    hit = o[o.org_id == entry_id]
    return _clean(hit, ORG_COLS)[0] if len(hit) else None


def list_sources(query: str = "") -> list[dict]:
    s = pd.read_csv(ROOT / "data" / "registry" / "sources.csv")
    q = _tok(query)
    if q:
        s = s[[bool(q & _tok(" ".join(map(str, r)))) for r in s.itertuples(index=False)]]
    return [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in s.to_dict("records")]


def valid_ids() -> set[str]:
    return set(ff.load_funding().fund_id) | set(ff.load_orgs().org_id) | set(pd.read_csv(ROOT / "data" / "registry" / "sources.csv").source_id)


def invalid_citations(text: str) -> list[str]:
    """Registry-style ids (F###, O###, S###) in `text` that are not in the registries: treated as a hard failure."""
    return sorted({m for m in re.findall(r"\b[FOS]\d{2,3}\b", text)} - valid_ids())


TOOLS = {"search_funding": search_funding, "search_orgs": search_orgs, "get_entry": get_entry, "list_sources": list_sources}

TOOL_SPECS = [
    {"name": "search_funding", "description": "Search the funding registry (grants, appeals, pooled funds). Returns rows with id, URL, verified_on, recency and escrow fit. "
     "Call several times with different queries/filters to loop through the database.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "keywords, e.g. 'maternal health', 'civil society'"},
         "channel": {"type": "string", "enum": ["gov", "UN_pooled", "pooled_fund", "local_ngo", "INGO", "NGO", "private", "other"]},
         "local_org_eligible": {"type": "string", "enum": ["yes", "no", "partial", "to_verify"]},
         "community_decision_fit": {"type": "string", "enum": ["high", "medium", "low", "to_verify"],
                                    "description": "how far the funder lets communities decide use (high = core/flexible/institutional funding)"},
         "active_only": {"type": "boolean"}, "include_closed": {"type": "boolean", "description": "include rows with status 'closed' (default false)"},
         "limit": {"type": "integer"}}}},
    {"name": "search_orgs", "description": "Search implementing organisations and precedents (local NGOs, municipalities, cooperatives, programmes).",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "community_decision_fit": {"type": "string", "enum": ["yes", "partial", "no", "to_verify"]},
                                                       "limit": {"type": "integer"}}}},
    {"name": "get_entry", "description": "Fetch one registry row by id (F### funding, O### organisation).",
     "input_schema": {"type": "object", "properties": {"entry_id": {"type": "string"}}, "required": ["entry_id"]}},
    {"name": "list_sources", "description": "Search the sources catalog (S### ids).",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}}},
]
