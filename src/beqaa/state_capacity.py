"""State-capacity anchor for the governance / escrow logic.

Real, national anchors come from data/registry/state_capacity_sources.csv (SC01-SC12):
  SC01 WGI Government Effectiveness 2025 = 29.9/100 (status to_verify_primary) -> national admin-capacity anchor 0.299
  SC02 Government share of total health spending 2025 = 13.4% (verified)        -> fiscal anchor 0.134
  SC03 MoPH budget $486M (2018) -> $37M (2022) (secondary; context only)
  SC09 municipal councils elected May 2025 for 6 years -> elected municipal counterpart through 2030
District-level `governance_capacity` stays MOCK (no public district series; SC07 UN-Habitat 2026 rapid municipal assessment
is the best source to replace it). Here the mock district values keep only their RELATIVE spread: they are rescaled so the
district mean in the anchor year equals the national WGI anchor, and projections are capped at <=0.05/yr (FEASIBILITY §5).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from .io import ROOT, load_dataset

SC_PATH = ROOT / "data" / "registry" / "state_capacity_sources.csv"
ESCROW_PARAMS = ROOT / "data" / "params" / "escrow_params.yaml"


def load_sources() -> pd.DataFrame:
    return pd.read_csv(SC_PATH)


def load_params(path=None) -> dict:
    return yaml.safe_load(open(path or ESCROW_PARAMS))


def _val(sc: pd.DataFrame, sid: str) -> tuple[float, int, str]:
    r = sc.set_index("id").loc[sid]
    return float(r.value), int(r.year), str(r.status)


def national_baseline(sc: pd.DataFrame | None = None) -> dict:
    """National anchors (0-1 scale) with their source ids and status."""
    sc = sc if sc is not None else load_sources()
    ge, ge_y, ge_s = _val(sc, "SC01")
    fs, fs_y, fs_s = _val(sc, "SC02")
    out = {"admin_anchor": ge / 100, "admin_anchor_year": ge_y, "admin_anchor_source": "SC01", "admin_anchor_status": ge_s,
           "fiscal_anchor": fs / 100, "fiscal_anchor_year": fs_y, "fiscal_anchor_source": "SC02", "fiscal_anchor_status": fs_s}
    ids = set(sc.id)
    if "SC03" in ids:
        b22, _, s3 = _val(sc, "SC03")
        out.update(moph_budget_2022_usd=b22, moph_budget_2018_usd=486e6, moph_budget_ratio_2022_vs_2018=b22 / 486e6, moph_budget_status=s3)
    if "SC09" in ids:
        out.update(municipal_councils_elected=2025, municipal_term_end=2025 + 6, municipal_source="SC09")
    return out


def anchored_governance(gov: pd.DataFrame | None = None, anchor: float | None = None, anchor_year: int | None = None,
                        yoy_gain: float | None = None, max_yoy: float | None = None) -> pd.DataFrame:
    """District admin_capacity_index anchored to the national WGI value; projections recomputed with a capped yearly gain.
    Returns the governance table with `admin_capacity_index` replaced and provenance columns added."""
    p = load_params()["national_anchor"]
    if gov is None:
        gov, mock = load_dataset("governance_capacity")
    else:
        mock = bool(gov.get("is_mock", pd.Series([True])).astype(bool).any())
    nb = national_baseline()
    anchor = nb["admin_anchor"] if anchor is None else anchor
    max_yoy = p["max_yoy_gain"] if max_yoy is None else max_yoy
    yoy = min(p["default_yoy_gain"] if yoy_gain is None else yoy_gain, max_yoy)
    g = gov.copy()
    g["projected"] = g.projected.astype(bool)
    actual = g[~g.projected]
    ay = anchor_year or min(int(p["anchor_year_applied_to"]), int(actual.year.max()))
    mean_ay = actual[actual.year == ay].admin_capacity_index.mean()
    scale = anchor / mean_ay if mean_ay > 0 else 1.0
    g["admin_capacity_index_mock_raw"] = g.admin_capacity_index
    g.loc[~g.projected, "admin_capacity_index"] = (g.loc[~g.projected, "admin_capacity_index_mock_raw"] * scale).clip(0, 1)
    last = g[~g.projected].sort_values("year").groupby("district").tail(1).set_index("district")
    for i in g.index[g.projected]:
        d, y = g.at[i, "district"], g.at[i, "year"]
        g.at[i, "admin_capacity_index"] = float(np.clip(last.loc[d, "admin_capacity_index"] + yoy * (y - last.loc[d, "year"]), 0, 1))
    g["capacity_status"] = np.where(g.projected, f"projected: mock district spread x {nb['admin_anchor_source']} anchor, +{yoy:.2f}/yr (cap {max_yoy:.2f})",
                                    f"mock district spread rescaled to {nb['admin_anchor_source']} national anchor {anchor:.3f}")
    g["national_anchor"] = anchor
    g["anchor_scale"] = scale
    g["is_mock"] = mock
    return g


def capacity_panel() -> pd.DataFrame:
    """Small table for the dashboard: what is real (national) vs mock (district)."""
    nb = national_baseline()
    sc = load_sources().set_index("id")
    rows = [("National admin-capacity anchor", f"{nb['admin_anchor']:.3f}", "SC01 WGI Government Effectiveness " + str(nb["admin_anchor_year"]), nb["admin_anchor_status"], sc.loc["SC01", "url"]),
            ("Government share of health spending", f"{nb['fiscal_anchor']:.1%}", "SC02 K2P/UNICEF " + str(nb["fiscal_anchor_year"]), nb["fiscal_anchor_status"], sc.loc["SC02", "url"])]
    if "moph_budget_2022_usd" in nb:
        rows.append(("MoPH budget 2022 vs 2018", f"${nb['moph_budget_2022_usd'] / 1e6:.0f}M vs $486M", "SC03 (secondary, caveat)", nb["moph_budget_status"], sc.loc["SC03", "url"]))
    if "municipal_term_end" in nb:
        rows.append(("Elected municipal counterpart", f"councils elected May 2025, term to {nb['municipal_term_end']}", "SC09 UNDP", sc.loc["SC09", "status"], sc.loc["SC09", "url"]))
    rows.append(("District admin_capacity_index", "MOCK (relative spread only)", "replace with SC07 UN-Habitat 2026 rapid municipal assessment", "mock", sc.loc["SC07", "url"]))
    return pd.DataFrame(rows, columns=["indicator", "value", "source", "status", "url"])
