"""Dataset loader: real file from data/raw/ if present, else mock from data/mock/."""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MOCK = ROOT / "data" / "mock"
PROCESSED = ROOT / "data" / "processed"   # real datasets written by `python -m beqaa.ingest`; preferred over data/mock unless BEQAA_DATA=mock
MOCK_REAL_IDS = MOCK / "real_ids"          # mock scenario inputs keyed to the REAL cadaster/facility ids (used when real cadasters are loaded)
DERIVED = PROCESSED                        # legacy alias

# dataset name -> raw file name (see CLAUDE.md section 4)
DATASETS = {
    "cadasters": "cadasters.csv",
    "population": "population.csv",
    "facilities": "facilities.csv",
    "travel_time": "travel_time.csv",
    "vulnerability": "vulnerability.csv",
    "official_severity": "official_severity.csv",
    "soil_sites": "soil_sites.csv",
    "water_quality": "water_quality.csv",
    "crop_transfer": "crop_transfer.csv",
    "interventions": "interventions.csv",
    "cascade_baseline": "cascade_baseline.csv",
    "staffing_referrals": "staffing_referrals.csv",
    "conflict_exposure": "conflict_exposure.csv",
    "funding_flows": "funding_flows.csv",
    "funding_requirements": "funding_requirements.csv",
    "governance_capacity": "governance_capacity.csv",
}


@dataclass
class Loaded:
    df: pd.DataFrame
    is_mock: bool

    def __iter__(self):  # allows `df, is_mock = load_dataset(name)`
        return iter((self.df, self.is_mock))


ID_COLS = {"cadaster_id": str, "facility_id": str}
# datasets whose real source is partial or modelled: they never get the plain "real" badge
KEYED_MOCK = {"staffing_referrals", "water_quality", "soil_sites"}        # id-keyed mock inputs regenerated against real ids (data/mock/real_ids)


def _mode() -> str:
    """BEQAA_DATA=mock forces mock files; anything else (default) prefers data/processed and falls back to mock per dataset. 'derived' is a legacy alias."""
    return "mock" if os.environ.get("BEQAA_DATA", "").lower() == "mock" else "auto"


def _read(path: pathlib.Path) -> pd.DataFrame:
    head = pd.read_csv(path, nrows=0).columns
    return pd.read_csv(path, dtype={c: t for c, t in ID_COLS.items() if c in head})


def load_dataset(name: str, raw_dir: pathlib.Path | None = None, mock_dir: pathlib.Path | None = None) -> Loaded:
    """Order: data/raw/<file> (real, hand-placed) -> data/processed/<file> (real, from the ingest scripts) -> data/mock/<file>.
    Explicit raw_dir / mock_dir arguments isolate the call (used by tests) and skip data/processed."""
    if name not in DATASETS:
        raise KeyError(f"Unknown dataset '{name}'. Known: {sorted(DATASETS)}")
    isolated = raw_dir is not None or mock_dir is not None
    raw_dir, mock_dir = raw_dir or RAW, mock_dir or MOCK
    raw = raw_dir / DATASETS[name]
    if raw.exists():
        df = _read(raw)
        if "is_mock" not in df.columns:
            df["is_mock"] = False
        return Loaded(df, False)
    if not isolated and _mode() == "auto":
        proc = PROCESSED / DATASETS[name]
        if proc.exists():
            df = _read(proc)
            if "is_mock" not in df.columns:
                df["is_mock"] = False
            return Loaded(df, bool(df["is_mock"].any()))
        real_ids = MOCK_REAL_IDS / DATASETS[name]
        if name in KEYED_MOCK and real_ids.exists() and (PROCESSED / DATASETS["cadasters"]).exists():
            df = _read(real_ids)
            df["is_mock"] = True
            return Loaded(df, True)
    mock = mock_dir / DATASETS[name]
    if not mock.exists():
        raise FileNotFoundError(f"No real ({raw}) or mock ({mock}) file for '{name}'. Run `make mock`.")
    df = _read(mock)
    df["is_mock"] = True
    return Loaded(df, True)


REAL_ONLY = {"funding_flows", "funding_requirements"}          # no mock counterpart: absent processed file = missing, never invented
BADGES = {"real": "✅ real", "partly real": "🟡 partly real", "mock": "🔴 mock", "missing": "⚪ missing"}


def dataset_badge(name: str, raw_dir: pathlib.Path | None = None, processed_dir: pathlib.Path | None = None) -> str:
    """real = verified processed file, nothing assumed or missing; partly real = processed file with assumed/modelled fields, NaN columns or
    status partial/assumption; mock = synthetic."""
    raw_dir = raw_dir or RAW
    fname = DATASETS[name]
    if (raw_dir / fname).exists():
        df = pd.read_csv(raw_dir / fname)
        mocky = ("is_mock" in df.columns and df["is_mock"].astype(bool).any()) or ("is_mock_location" in df.columns and df["is_mock_location"].astype(bool).any())
        return "partly real" if mocky else "real"
    pdir = processed_dir if processed_dir is not None else (PROCESSED if (raw_dir == RAW and _mode() == "auto") else None)
    if pdir is not None and (pdir / fname).exists():
        df = pd.read_csv(pdir / fname)
        if "is_mock" in df.columns and df["is_mock"].astype(bool).all():
            return "mock"
        mixed = "is_mock" in df.columns and df["is_mock"].astype(bool).any()        # some rows real (e.g. intervention costs derived from sourced prices), some still mock
        st = set(df["status"].dropna().astype(str)) if "status" in df.columns else set()
        data_cols = [c for c in df.columns if c not in ("is_mock", "source_id", "source", "source_date", "url", "status", "level", "areas", "analysis_date", "assumed_fields")]
        has_nan_col = bool(df[data_cols].isna().all().any()) if data_cols else False
        if mixed or st & {"partial", "assumption", "missing"} or "assumed_fields" in df.columns or has_nan_col:
            return "partly real"
        return "real"
    return "missing" if name in REAL_ONLY else "mock"


def data_status(raw_dir: pathlib.Path | None = None, processed_dir: pathlib.Path | None = None) -> pd.DataFrame:
    """Per-dataset badge (real / partly real / mock) and where it is loaded from."""
    rows = []
    for name, fname in DATASETS.items():
        b = dataset_badge(name, raw_dir, processed_dir)
        rows.append((name, fname, BADGES[b]))
    return pd.DataFrame(rows, columns=["dataset", "raw_file", "status"])


def overall_mode(raw_dir: pathlib.Path | None = None, processed_dir: pathlib.Path | None = None) -> str:
    st_ = data_status(raw_dir, processed_dir)
    s = st_[~st_.dataset.isin(REAL_ONLY)]["status"]
    if s.str.contains("🔴").all():
        return "MOCK"
    if s.str.contains("✅").all():
        return "REAL"
    return "PARTIAL"


def readme_status_table(raw_dir: pathlib.Path | None = None) -> str:
    t = data_status(raw_dir)
    lines = ["| Dataset | Raw file | Status |", "|---|---|---|"]
    lines += [f"| {r.dataset} | `{r.raw_file}` | {r.status} |" for r in t.itertuples()]
    return "\n".join(lines)


# ---- Reference series (national context; not part of the mock/real switch) ----
WDI_DIR = RAW / "worldbank_population"


def load_wdi_population(country_code: str = "LBN") -> pd.DataFrame | None:
    """World Bank WDI total population (year, population) for one country, or None if the file is absent."""
    f = WDI_DIR / "wdi_population_total_by_country.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f, skiprows=4, encoding="utf-8-sig")
    row = df[df["Country Code"] == country_code]
    if row.empty:
        return None
    s = row.drop(columns=["Country Name", "Country Code", "Indicator Name", "Indicator Code"], errors="ignore")
    s = s.loc[:, [c for c in s.columns if str(c).isdigit()]].iloc[0].dropna()
    out = pd.DataFrame({"year": s.index.astype(int), "population": s.values.astype(float)})
    out["source"] = "World Bank WDI SP.POP.TOTL"
    out["status"] = "verified"
    out["is_mock"] = False
    return out


def reference_status() -> pd.DataFrame:
    ok = (WDI_DIR / "wdi_population_total_by_country.csv").exists()
    return pd.DataFrame([("wdi_population (Lebanon national series)", "data/raw/worldbank_population/", "✅ real" if ok else "🔴 missing")],
                        columns=["dataset", "raw_file", "status"])


CADASTER_KEYED = ["population", "vulnerability", "conflict_exposure", "travel_time", "facilities"]


def validate_consistency() -> list[str]:
    """Datasets keyed by cadaster_id must all use the same cadaster set. Mixing real cadasters with mock files (or the reverse) breaks joins.
    Returns a list of problems (empty = consistent)."""
    ids = set(load_dataset("cadasters").df.cadaster_id)
    problems = []
    for name in CADASTER_KEYED:
        if name not in DATASETS:
            continue
        try:
            df = load_dataset(name).df
        except FileNotFoundError:
            continue
        have = set(df.cadaster_id.dropna())
        if name in ("population", "vulnerability", "conflict_exposure") and have != ids:
            problems.append(f"{name}: {len(have ^ ids)} cadaster ids differ from cadasters ({len(have)} vs {len(ids)}). Mixed real/mock?")
        elif name in ("travel_time", "facilities") and not have <= ids:
            problems.append(f"{name}: {len(have - ids)} cadaster ids not in cadasters. Mixed real/mock?")
    return problems
