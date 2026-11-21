"""Grounded 'ask the registry' assistant. Retrieval only (no LLM call): answers exclusively from
funding_registry.csv, org_registry.csv and sources.csv. Every hit cites its row id + URL + verified_on.
If nothing matches it says so; it never invents a grant. (An LLM layer can be added later on top of the retrieved rows.)"""
from __future__ import annotations

import re

import pandas as pd

from . import funding_finder as ff

NO_MATCH = "No verified entry; add one to the registry."
STOP = set("the a an of for to in and or is are what which who how any can we do does with on from about funding fund grant grants".split())


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 2}


def answer(query: str, today: pd.Timestamp = ff.TODAY) -> dict:
    q = _tokens(query)
    f = ff.annotate(ff.load_funding(), today)
    o = ff.load_orgs()
    hits = []
    for r in f.itertuples():
        text = " ".join(str(x) for x in (r.name, r.funder, r.sectors, r.geography, r.channel, r.notes))
        ov = q & _tokens(text)
        if ov:
            hits.append({"kind": "funding", "id": r.fund_id, "name": r.name, "url": r.url, "verified_on": r.verified_on,
                         "stale": bool(r.verified_stale), "recency": r.recency_flag, "fits_escrow": r.fits_escrow,
                         "amount": f"{r.amount:,.0f} {r.currency}" if pd.notna(r.amount) else "see source document",
                         "matched": sorted(ov)})
    for r in o.itertuples():
        text = " ".join(str(x) for x in (r.name, r.type, r.geography, r.sectors, r.notes))
        ov = q & _tokens(text)
        if ov:
            hits.append({"kind": "org", "id": r.org_id, "name": r.name, "url": r.url if isinstance(r.url, str) else "",
                         "verified_on": "", "stale": True, "recency": f"status: {r.status}", "matched": sorted(ov)})
    hits.sort(key=lambda h: -len(h["matched"]))
    if not hits:
        return {"answer": NO_MATCH, "citations": []}
    lines = []
    for h in hits[:6]:
        flag = " ⚠ verification older than 6 months or not verified" if h["stale"] else ""
        lines.append(f"- **{h['name']}** [{h['id']}] ({h['recency']}){flag}. Source: {h['url'] or 'no URL on record'}; "
                     f"verified_on: {h['verified_on'] or 'n/a'}")
    return {"answer": "\n".join(lines), "citations": [h["id"] for h in hits[:6]]}
