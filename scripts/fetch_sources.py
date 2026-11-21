"""Download the real datasets listed in data/registry/data_manifest.csv into data/raw/<local_dir>/.

    python scripts/fetch_sources.py            # fetch anything missing
    python scripts/fetch_sources.py --refresh  # re-download everything
    python scripts/fetch_sources.py --check    # report HDX 'last_modified' vs the copy on disk
    python scripts/fetch_sources.py --restore-pdfs  # re-download PDFs that are not stored in git (urls + sha256 from each _provenance.json)

Downloaded files are treated as UNTRUSTED DATA: this script only saves bytes (plus a provenance JSON); it never
opens, unzips or executes them. Inspect with `python -I`. Public sources only; no credentials.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "registry" / "data_manifest.csv"
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "beqaa-data-fetch/1.0"}


def get(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def hdx_package(pkg: str) -> dict:
    return json.loads(get(f"https://data.humdata.org/api/3/action/package_show?id={pkg}", 30))["result"]


def restore_pdfs() -> None:
    """PDFs are not committed (third-party licences vary). Every data/raw/*/_provenance.json lists file, url and sha256: re-fetch what is missing and verify the hash."""
    for prov in sorted(RAW.glob("**/_provenance.json")):
        d = json.loads(prov.read_text())
        entries = d if isinstance(d, list) else d.get("files", [d] if "file" in d else [])
        for e in entries:
            if not isinstance(e, dict):
                continue
            name, url = e.get("file"), e.get("url")
            if not name or not name.lower().endswith(".pdf"):
                continue
            dest = prov.parent / name
            if dest.exists():
                continue
            if not url:
                print(f"MANUAL  {dest.relative_to(RAW)}: no url recorded (supplied by the team); see docs/MANUAL_STEPS.md")
                continue
            try:
                blob = get(url)
            except Exception as ex:
                print(f"FAILED  {name}: {ex}")
                continue
            ok = not e.get("sha256") or hashlib.sha256(blob).hexdigest() == e["sha256"]
            dest.write_bytes(blob)
            print(f"{'ok     ' if ok else 'CHANGED'} {dest.relative_to(RAW)} ({len(blob):,} bytes){'' if ok else ' (sha256 differs from the recorded copy: re-check the transcription)'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore-pdfs", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.restore_pdfs:
        return restore_pdfs()
    for row in csv.DictReader(open(MANIFEST)):
        if row["status"] not in ("downloaded", "to_download"):
            continue
        out = RAW / row["local_dir"]
        prov_path = out / "_provenance.json"
        if a.check:
            if row["method"] == "hdx":
                lm = hdx_package(row["hdx_package"]).get("last_modified", "")[:10]
                have = json.loads(prov_path.read_text()).get("hdx_last_modified", "")[:10] if prov_path.exists() else "missing"
                print(f"{row['source_id']:4} {row['dataset']:16} hdx {lm}  local {have}  {'STALE' if lm != have else 'ok'}")
            continue
        if prov_path.exists() and not a.refresh:
            print(f"{row['source_id']:4} skip (exists) {row['local_dir']}")
            continue
        out.mkdir(parents=True, exist_ok=True)
        files, meta = [], {}
        if row["method"] == "hdx":
            pkg = hdx_package(row["hdx_package"])
            meta = {"hdx_last_modified": pkg.get("last_modified", ""), "hdx_page": f"https://data.humdata.org/dataset/{row['hdx_package']}"}
            want = set(row["files"].split(";"))
            for res in pkg["resources"]:
                name = urllib.parse.unquote(res["url"].split("/")[-1])
                if name in want or res["name"] in want:
                    files.append((name, res["url"]))
            missing = want - {n for n, _ in files}
            if missing:
                print(f"   WARNING {row['source_id']}: not found on HDX: {sorted(missing)}")
        else:
            files.append((urllib.parse.unquote(row["url"].split("?")[0].split("/")[-1]) or "download", row["url"]))
        recs = []
        for name, url in files:
            try:
                blob = get(url)
            except Exception as e:                                    # keep going; report
                print(f"   FAILED {row['source_id']} {name}: {e}")
                continue
            (out / name).write_bytes(blob)
            recs.append({"file": name, "url": url, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
            print(f"{row['source_id']:4} {name} ({len(blob):,} bytes)")
        if not recs:
            try:
                out.rmdir()
            except OSError:
                pass
        if recs:
            prov_path.write_text(json.dumps({"source_id": row["source_id"], "title": row["title"], "publisher": row["publisher"], "license": row["license"],
                                             "retrieved": dt.date.today().isoformat(), "files": recs, **meta}, indent=2))


if __name__ == "__main__":
    main()
