"""M4: Soil / food exposure screen. Answers Q2, Q4.

ADD_soil = C*IR*EF/BW ; C_crop = C*TF ; ADD_food = C_crop*intake/BW ; HQ = ADD/RfD.
Cr speciation (cr6_fraction in [0,1]) is the key uncertainty, so HQ is reported as a range.
Lead is compared with the EPA residential soil screening level (screening ratio, not an HQ).
Evidence rungs: a = environmental finding, b = plausible exposure pathway, c = demonstrated health effect.
Rung 'c' is never assigned here: it needs biomonitoring / clinical data that we do not have.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import yaml

from .io import ROOT, load_dataset

PARAMS_PATH = ROOT / "data" / "params" / "exposure_params.yaml"

ACTIONS = {
    0: ("a", "Background. No action; keep in monitoring registry."),
    1: ("a", "Elevated, no exposure shown. Protective advice (handwashing, wash produce); schedule confirmatory sampling."),
    2: ("b", "Plausible exposure pathway. Washing-water access for field workers; targeted blood-lead screening (Pb) / Cr(VI) "
             "speciation tests (Cr); clinical referral if symptomatic; consider land-use restriction if confirmed."),
    3: ("c", "Confirmed (health data). Clinical assessment, referral and follow-up; land-use restriction."),
}


def load_params(path: pathlib.Path | None = None) -> dict:
    return yaml.safe_load(open(path or PARAMS_PATH))


def _recv(p: dict, receptor: str):
    return (p["soil_ingestion_mg_per_day"][receptor], p["body_weight_kg"][receptor], p["exposure_frequency"]["days"] / p["exposure_frequency"]["per"],
            p["food_intake_kg_per_day"][receptor])


def add_soil(c_mg_kg, receptor: str, p: dict):
    ir, bw, ef, _ = _recv(p, receptor)
    return c_mg_kg * ir * 1e-6 * ef / bw          # mg/kg-day


def add_food(c_mg_kg, tf, receptor: str, p: dict):
    _, bw, _, intake = _recv(p, receptor)
    return c_mg_kg * tf * intake / bw


def cr_hq(c, receptor="child", cr6=0.0, tf=0.0, p=None, include_food=False):
    p = p or load_params()
    add = add_soil(c, receptor, p) + (add_food(c, tf, receptor, p) if include_food else 0.0)
    rfd3, rfd6 = p["rfd_mg_per_kg_day"]["Cr_III"]["value"], p["rfd_mg_per_kg_day"]["Cr_VI"]["value"]
    return add * (1 - cr6) / rfd3 + add * cr6 / rfd6


def _tf_for(metal: str, tfdf: pd.DataFrame) -> float:
    """Conservative: highest crop transfer factor for the metal (leafy-vegetable pathway)."""
    t = tfdf[tfdf.metal == metal].transfer_factor
    return float(t.max()) if len(t) else 0.0


def screen_sites(p: dict | None = None, receptor: str = "child", cr6_for_tier: float | None = None) -> pd.DataFrame:
    """One row per soil measurement with HQ range (soil+food), tier, evidence rung, action.
    `cr6_for_tier`: Cr(VI) share used to set the Cr tier. None (default) = precautionary worst case (all Cr(VI), = hq_high).
    This is the M4 -> M2 link: the tier feeds the Need Score environment domain (soil_hotspot_proximity) and, through it,
    the allocation / escrow priority. `speciation_decisive` = the HQ range straddles 1, so a Cr(VI) speciation test would
    change the tier (an implementation-research candidate, see research_gaps.py)."""
    p = p or load_params()
    soil, mock = load_dataset("soil_sites")
    tfdf, _ = load_dataset("crop_transfer")
    pbssl = p["lead_soil_screening_level_ppm"]["value"]
    rows = []
    for r in soil.itertuples():
        m, c = r.parameter, float(r.value_mg_kg)
        row = {"site_name": r.site_name, "cadaster_id": r.cadaster_id, "lat": getattr(r, "lat", np.nan), "lon": getattr(r, "lon", np.nan),
               "parameter": m, "value_mg_kg": c, "receptor": receptor, "hq_low": np.nan, "hq_high": np.nan, "screening_ratio": np.nan,
               "hq_at_assumed_cr6": np.nan, "speciation_decisive": False}
        if m == "Cr":
            tf = _tf_for("Cr", tfdf)
            row["hq_low"] = cr_hq(c, receptor, 0.0, tf, p, True)
            row["hq_high"] = cr_hq(c, receptor, 1.0, tf, p, True)
            row["hq_soil_only_low"] = cr_hq(c, receptor, 0.0, 0, p, False)
            row["hq_soil_only_high"] = cr_hq(c, receptor, 1.0, 0, p, False)
            row["hq_at_assumed_cr6"] = row["hq_high"] if cr6_for_tier is None else cr_hq(c, receptor, cr6_for_tier, tf, p, True)
            row["speciation_decisive"] = bool(row["hq_low"] < 1 <= row["hq_high"])
            hq_t = row["hq_at_assumed_cr6"]
            tier = 0 if hq_t < 0.1 else (1 if hq_t < 1 else 2)
        elif m == "Pb":
            row["screening_ratio"] = c / pbssl
            tier = 0 if row["screening_ratio"] < 0.5 else (1 if row["screening_ratio"] < 1 else 2)
        else:
            tier = 0          # e.g. total_P: nutrient / eutrophication marker, no toxicity benchmark applied
        row["tier"] = tier
        row["evidence_rung"], row["action"] = ACTIONS[tier]
        row["is_mock_location"] = bool(getattr(r, "is_mock_location", True))
        row["is_mock"] = bool(mock)
        row["note"] = "total_P: no toxicity benchmark; marker only" if m == "total_P" else ""
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def monte_carlo(c: float, receptor: str = "child", n: int = 5000, seed: int = 42, p: dict | None = None, metal: str = "Cr") -> dict:
    """Monte Carlo HQ over TF (lognormal), intake (uniform +-50%), soil ingestion (+-50%), cr6_fraction (uniform 0-1)."""
    p = p or load_params()
    rng = np.random.default_rng(seed)
    tfdf, _ = load_dataset("crop_transfer")
    tf0 = _tf_for(metal, tfdf)
    tf = tf0 * rng.lognormal(0, 0.6, n)
    ir_f, in_f = rng.uniform(0.5, 1.5, n), rng.uniform(0.5, 1.5, n)
    cr6 = rng.uniform(p["cr6_fraction"]["low"], p["cr6_fraction"]["high"], n)
    ir, bw, ef, intake = _recv(p, receptor)
    add = c * ir * ir_f * 1e-6 * ef / bw + c * tf * intake * in_f / bw
    rfd3, rfd6 = p["rfd_mg_per_kg_day"]["Cr_III"]["value"], p["rfd_mg_per_kg_day"]["Cr_VI"]["value"]
    hq = add * (1 - cr6) / rfd3 + add * cr6 / rfd6
    return {"hq": hq, "p5": float(np.percentile(hq, 5)), "p50": float(np.percentile(hq, 50)), "p95": float(np.percentile(hq, 95)),
            "p_exceed_1": float((hq >= 1).mean())}


def tornado(c: float = 230, receptor: str = "child", p: dict | None = None) -> pd.DataFrame:
    """One-at-a-time swing in HQ (soil+food) around the midpoint; ranks which evidence would most change the response
    (value-of-information ranking)."""
    p = p or load_params()
    tfdf, _ = load_dataset("crop_transfer")
    tf0 = _tf_for("Cr", tfdf)

    def hq(cr6=0.5, tfm=1.0, inm=1.0, irm=1.0):
        ir, bw, ef, intake = _recv(p, receptor)
        add = c * ir * irm * 1e-6 * ef / bw + c * tf0 * tfm * intake * inm / bw
        return add * (1 - cr6) / p["rfd_mg_per_kg_day"]["Cr_III"]["value"] + add * cr6 / p["rfd_mg_per_kg_day"]["Cr_VI"]["value"]

    base = hq()
    spec = {"Cr(VI) fraction (0 → 1)": (hq(cr6=0), hq(cr6=1), "Cr(VI) speciation tests"),
            "Crop transfer factor (×0.25 → ×4)": (hq(tfm=0.25), hq(tfm=4), "Local crop uptake sampling"),
            "Crop intake (×0.5 → ×1.5)": (hq(inm=0.5), hq(inm=1.5), "Diet survey of farming households"),
            "Soil ingestion (×0.5 → ×1.5)": (hq(irm=0.5), hq(irm=1.5), "Behavioural / hygiene survey")}
    df = pd.DataFrame([{"driver": k, "hq_low": a, "hq_high": b, "swing": abs(b - a), "evidence_that_would_change_response": e}
                       for k, (a, b, e) in spec.items()]).sort_values("swing", ascending=False)
    df["hq_base"] = base
    df["rank_voi"] = range(1, len(df) + 1)
    return df.reset_index(drop=True)


def cadaster_tiers(sites: pd.DataFrame | None = None) -> pd.DataFrame:
    s = sites if sites is not None else screen_sites()
    g = s.groupby("cadaster_id").agg(max_tier=("tier", "max")).reset_index()
    return g


def evidence_table(sites: pd.DataFrame | None = None) -> pd.DataFrame:
    s = sites if sites is not None else screen_sites()
    rows = []
    for r in s.itertuples():
        if r.parameter == "total_P":
            claim = f"{r.site_name}: total P {r.value_mg_kg:.0f} mg/kg measured in soil (marker only)"
        elif r.parameter == "Cr":
            claim = (f"{r.site_name}: Cr {r.value_mg_kg:.0f} mg/kg; child HQ {r.hq_low:.3f}–{r.hq_high:.2f} depending on Cr(VI) share"
                     f" (tier {r.tier})")
        else:
            claim = f"{r.site_name}: Pb {r.value_mg_kg:.0f} mg/kg = {r.screening_ratio:.2f}× EPA screening level (tier {r.tier})"
        rows.append({"claim": claim, "rung": r.evidence_rung,
                     "source": "CNRS-L/MoE Apr 2026 Ch. II (values); exposure params EPA defaults (status: verify)",
                     "is_mock_location": r.is_mock_location})
    return pd.DataFrame(rows)


def nitrate_by_cadaster() -> pd.DataFrame:
    w, _ = load_dataset("water_quality")
    return w.groupby("cadaster_id").nitrate_mg_l.mean().reset_index()
