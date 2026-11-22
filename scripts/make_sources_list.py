"""Writes docs/DATA_SOURCES.md: every downloaded source with publisher, licence and access date (from data/registry/data_manifest.csv and the _provenance.json files under data/raw)."""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def retrieved(local_dir: str) -> str:
    p = ROOT / "data" / "raw" / local_dir / "_provenance.json"
    if p.exists():
        d = json.loads(p.read_text())
        for k in ("retrieved", "obtained", "accessed"):
            if isinstance(d, dict) and d.get(k):
                return str(d[k])[:10]
        items = d.get("files") if isinstance(d, dict) else d if isinstance(d, list) else []
        for it in items or []:
            if isinstance(it, dict) and it.get("retrieved"):
                return str(it["retrieved"])[:10]
    return "2026-11-21"


def render() -> str:
    rows = list(csv.DictReader(open(ROOT / "data" / "registry" / "data_manifest.csv")))
    t = ["# Data sources with access dates", "", "From `data/registry/data_manifest.csv` and each `data/raw/*/_provenance.json` (retrieved date; the manifest rows were retrieved 2026-11-21 unless the file says otherwise). Third-party PDFs are not stored in git: `python scripts/fetch_sources.py --restore-pdfs`.", "",
         "| ID | Dataset | Source | Publisher | Licence | Retrieved | Feeds |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        t.append(f"| {r['source_id']} | {r['dataset']} | {r['title']} | {r['publisher']} | {r['license']} | {retrieved(r['local_dir'])} | {r['feeds']} |")
    t += ["", "Added after the manifest (each has a `_provenance.json` or a README in `data/raw/`): MoPH facility list and PHC network (2026-11-21), costs pack, Beqaa funding and partners, WorldPop age/sex, damage figures, projects inventory, surveillance (MoPH ESU to 7 Aug 2026, WHO briefs, WBD risk map), care-flow pack, evidence and price packs, AUB lab prices.",
          "ACLED is not used (the account returned HTTP 403 on OAuth and its tier gives only events older than 12 months); ACLED data are never committed."]
    return "\n".join(t) + "\n"


if __name__ == "__main__":
    (ROOT / "docs" / "DATA_SOURCES.md").write_text(render())
    print("wrote docs/DATA_SOURCES.md")
