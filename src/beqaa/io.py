"""Dataset loader: real file from data/raw/ if present, else mock from data/mock/."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MOCK = ROOT / "data" / "mock"

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
    "governance_capacity": "governance_capacity.csv",
    "funding_flows": "funding_flows.csv",
}


@dataclass
class Loaded:
    df: pd.DataFrame
    is_mock: bool

    def __iter__(self):  # allows `df, is_mock = load_dataset(name)`
        return iter((self.df, self.is_mock))


def load_dataset(name: str, raw_dir: pathlib.Path | None = None, mock_dir: pathlib.Path | None = None) -> Loaded:
    if name not in DATASETS:
        raise KeyError(f"Unknown dataset '{name}'. Known: {sorted(DATASETS)}")
    raw_dir, mock_dir = raw_dir or RAW, mock_dir or MOCK
    raw = raw_dir / DATASETS[name]
    if raw.exists():
        df = pd.read_csv(raw)
        if "is_mock" not in df.columns:
            df["is_mock"] = False
        return Loaded(df, False)
    mock = mock_dir / DATASETS[name]
    if not mock.exists():
        raise FileNotFoundError(f"No real ({raw}) or mock ({mock}) file for '{name}'. Run `make mock`.")
    df = pd.read_csv(mock)
    df["is_mock"] = True
    return Loaded(df, True)


def data_status(raw_dir: pathlib.Path | None = None) -> pd.DataFrame:
    """Per-dataset status: real / partial / mock (partial = real file with any is_mock rows)."""
    raw_dir = raw_dir or RAW
    rows = []
    for name, fname in DATASETS.items():
        p = raw_dir / fname
        if not p.exists():
            rows.append((name, fname, "🔴 mock"))
            continue
        df = pd.read_csv(p)
        partial = ("is_mock" in df.columns and df["is_mock"].astype(bool).any()) or \
                  ("is_mock_location" in df.columns and df["is_mock_location"].astype(bool).any())
        rows.append((name, fname, "🟡 partial" if partial else "✅ real"))
    return pd.DataFrame(rows, columns=["dataset", "raw_file", "status"])


def overall_mode(raw_dir: pathlib.Path | None = None) -> str:
    s = data_status(raw_dir)["status"]
    if s.str.contains("🔴").all():
        return "MOCK"
    if s.str.contains("✅").all():
        return "REAL"
    return "PARTIAL"


def readme_status_table(raw_dir: pathlib.Path | None = None) -> str:
    t = data_status(raw_dir)
    lines = ["| Dataset | Raw file | Status |", "|---|---|---|"]
    lines += [f"| {r.dataset} | `data/raw/{r.raw_file}` | {r.status} |" for r in t.itertuples()]
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
