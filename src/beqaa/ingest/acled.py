"""2.4 ACLED events (myACLED OAuth). Credentials come ONLY from the environment / .env (ACLED_EMAIL, ACLED_PASSWORD); they are never printed, logged, cached to disk or committed.

Flow (https://acleddata.com/api-documentation/getting-started): POST /oauth/token (password grant, client_id=acled) -> access_token (24 h) + refresh_token; GET /api/acled/read
with a Bearer token, paged until an empty page. The raw file is saved under data/raw/conflict_events/acled/ (gitignored: ACLED's terms forbid redistributing raw data) and
processed counts (also gitignored) are written to data/processed/conflict_events.csv: events and fatalities in the last 30 / 90 / 365 days per admin-3 cadaster
(geo_precision 1-2 only; precision 3 is district-level) and an `access_degraded` flag whose rule is a parameter in data/params/conflict_access.yaml.
If the token call returns 401/403 the script stops (no retry loop) and tells the user to check the login / API access of the account.
Without credentials, `fallback_hdx()` summarises the public HDX admin-2 x month ACLED file (district level only) if it has been downloaded."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd
import yaml

from .common import PROCESSED, RAW, ROOT

TOKEN_URL = "https://acleddata.com/oauth/token"
READ_URL = "https://acleddata.com/api/acled/read"
FIELDS = "event_id_cnty|event_date|event_type|sub_event_type|actor1|admin1|admin2|admin3|location|latitude|longitude|geo_precision|fatalities|source_scale"
PARAMS = ROOT / "data" / "params" / "conflict_access.yaml"


class AcledAuthError(RuntimeError):
    pass


def _load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                k, v = k.strip().removeprefix("export ").strip(), v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":        # strip one matching pair of quotes only (a password may contain quote characters)
                    v = v[1:-1]
                os.environ[k] = v                                          # .env wins over a stale value left in the shell


def get_token() -> str:
    _load_env()
    email, pw = os.environ.get("ACLED_EMAIL"), os.environ.get("ACLED_PASSWORD")
    if not email or not pw:
        raise AcledAuthError("ACLED_EMAIL / ACLED_PASSWORD not set (copy .env.example to .env and fill them in)")
    body = urllib.parse.urlencode({"username": email, "password": pw, "grant_type": "password", "client_id": "acled"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=60) as r:
            return json.loads(r.read())["access_token"]                       # held in memory only
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AcledAuthError(f"ACLED token request refused (HTTP {e.code}). Check the login at acleddata.com and whether the account tier allows API access. Not retrying.") from None
        raise


def fetch(date_from: str, date_to: str, token: str) -> pd.DataFrame:
    frames, page = [], 1
    while True:
        q = urllib.parse.urlencode({"_format": "csv", "country": "Lebanon", "event_date": f"{date_from}|{date_to}", "event_date_where": "BETWEEN", "limit": 5000, "page": page, "fields": FIELDS}, safe="|")
        req = urllib.request.Request(f"{READ_URL}?{q}", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode("utf-8-sig")
        d = pd.read_csv(io.StringIO(txt)) if txt.strip() else pd.DataFrame()
        if d.empty:
            break
        frames.append(d)
        page += 1
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def process(ev: pd.DataFrame, cad: pd.DataFrame, today: dt.date | None = None) -> pd.DataFrame:
    """Join points to admin-3 polygons (geo_precision 1-2); count events and fatalities in the last 30 / 90 / 365 days; set access_degraded from the YAML rule."""
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree
    from .cadasters_population import _admin3
    today = today or dt.date.today()
    rule = yaml.safe_load(open(PARAMS)) if PARAMS.exists() else {"window_days": 30, "min_events": 1}
    feats = [f for f in _admin3() if f["properties"]["adm3_pcode"] in set(cad.cadaster_id)]
    geoms, ids = [shape(f["geometry"]) for f in feats], [f["properties"]["adm3_pcode"] for f in feats]
    tree = STRtree(geoms)
    ev = ev[ev.geo_precision.isin([1, 2])].copy()
    ev["event_date"] = pd.to_datetime(ev.event_date).dt.date
    rows = []
    for r in ev.itertuples():
        pt = Point(r.longitude, r.latitude)
        hit = [i for i in tree.query(pt) if geoms[i].contains(pt)]
        if hit:
            rows.append({"cadaster_id": ids[hit[0]], "age": (today - r.event_date).days, "fatalities": r.fatalities})
    e = pd.DataFrame(rows)
    out = cad[["cadaster_id"]].copy()
    for w in (30, 90, 365):
        s = e[e.age <= w] if len(e) else e
        g = s.groupby("cadaster_id").agg(events=("age", "size"), fatalities=("fatalities", "sum")) if len(e) else pd.DataFrame(columns=["events", "fatalities"])
        out = out.merge(g.rename(columns={"events": f"events_{w}d", "fatalities": f"fatalities_{w}d"}), left_on="cadaster_id", right_index=True, how="left")
    out = out.fillna(0)
    out["access_degraded"] = out[f"events_{int(rule['window_days'])}d"] >= rule["min_events"]
    out["is_mock"] = False
    out["source_id"], out["source"], out["source_date"], out["status"] = "ACLED", "ACLED (myACLED API), geo_precision 1-2 only", today.isoformat(), "verified"
    out["url"] = "https://acleddata.com"
    return out


def fallback_hdx() -> pd.DataFrame | None:
    """District-level monthly ACLED counts from the public HDX file, if downloaded. NOT admin-3; labelled as such."""
    import glob
    fs = glob.glob(str(RAW / "conflict_events" / "hdx" / "acled_lbn_political_violence_by_month-year_*.xlsx"))
    if not fs:
        return None
    d = pd.read_excel(fs[0], sheet_name="Data")
    d["date"] = pd.to_datetime(d["Year"].astype(str) + "-" + d["Month"].astype(str), format="%Y-%B", errors="coerce")
    last = d.date.max()
    rec = d[d.date > last - pd.DateOffset(months=3)].groupby(["Admin1", "Admin2", "Admin2 Pcode"], as_index=False).agg(events_3m=("Events", "sum"), fatalities_3m=("Fatalities", "sum"))
    rec["level"] = "admin2 (district), monthly: NOT admin 3"
    rec["is_mock"] = False
    return rec


def run() -> dict:
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})
    try:
        tok = get_token()
    except AcledAuthError as e:
        fb = fallback_hdx()
        if fb is not None:
            fb.to_csv(PROCESSED / "conflict_events_district_fallback.csv", index=False)
        return {"acled": f"SKIPPED: {e}", "fallback_hdx_district_rows": 0 if fb is None else len(fb)}
    to = dt.date.today().isoformat()
    raw = fetch("2025-01-01", to, tok)
    folder = RAW / "conflict_events" / "acled"
    folder.mkdir(parents=True, exist_ok=True)
    raw.to_csv(folder / f"acled_lbn_2025-01-01_{to}.csv", index=False)
    (folder / "_provenance.json").write_text(json.dumps({"source": "ACLED myACLED API", "url": READ_URL, "retrieved": to, "license": "ACLED Terms of Use and Attribution Policy (do not redistribute raw data)", "rows": len(raw)}, indent=2))
    out = process(raw, cad)
    out.to_csv(PROCESSED / "conflict_events.csv", index=False)
    return {"acled_events": len(raw), "cadasters_access_degraded": int(out.access_degraded.sum())}
