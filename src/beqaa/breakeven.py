"""Break-even outputs: the value at which the preferred allocation option stops being preferred, with everything else at the centre of its range.

Options compared (policy names in robustness.POLICIES):
  status quo  = `existing_allocation`  money follows current facility capacity (what happens without a rule)
  top-down    = `top_down`             by need score x pregnancies
  community   = `community`            community committees choose among interventions (the proposal; local fit, capture and committee cost are assumptions)
For each comparison and each uncertain parameter (capture rate, committee admin cost, local-fit multiplier, alignment of community priorities with the most cost-effective
option) it solves for the flip point. Escrow release break-evens come straight from the pre-agreed rules in escrow_params.yaml (referral completion, posts filled, capacity).
Inputs that have no published value (referral completion, capture, local fit, committee cost) are scenario parameters, so these thresholds ARE the finding ("works if X > Y").
`reading` is the sentence for the memo; `flips_at` is None when no flip exists inside the tested range."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import escrow, m2_need_score as m2, m4_exposure, robustness as rb

PAIRS = [("community", "existing_allocation", "community vs status quo"), ("community", "top_down", "community vs top-down by need")]
PARAMS = {"capture": (0.0, 0.9, "capture rate", "<", "share of community money diverted"),
          "admin_cost": (0.0, 0.9, "committee admin cost", "<", "share of money spent running committees"),
          "local_fit": (0.8, 3.0, "local-fit multiplier", ">", "gain from spending matching local priorities"),
          "alignment": (0.0, 1.0, "alignment of community priorities with the most cost-effective option", ">", "share of priorities on the best option")}


def _engine(scored, budget, unc):
    eng = rb._Engine(scored, unc["top_k"], budget, unc)
    base = rb._draw(None, unc, np.random.default_rng(0), center=True, iv=eng.iv)
    base["alignment"] = 0.0
    return eng, base


def _solve(f, lo, hi):
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if f(lo) * f(m) <= 0 else (m, hi)
    return (lo + hi) / 2


def allocation_breakevens(scored: pd.DataFrame, budget: float = 100_000, unc: dict | None = None) -> pd.DataFrame:
    unc = unc or rb.load_uncertainty()
    eng, base = _engine(scored, budget, unc)
    rows = []
    for a, b, label in PAIRS:
        for name, (lo, hi, text, sign, expl) in PARAMS.items():
            for align in ((0.0, 1.0) if name != "alignment" else (0.0,)):
                bb = {**base, "alignment": align}

                def f(x, name=name, bb=bb, a=a, b=b):
                    d = {**bb, name: x}
                    return eng.value(a, d) / eng.value(b, d) - 1.0
                x = _solve(f, lo, hi)
                at_c = f(bb[name]) + 1.0
                rows.append({"comparison": label, "parameter": name, "priorities": "community picks the most cost-effective option" if align == 1.0 else "community priorities as modelled (placeholder)",
                             "flips_at": x, "central_value": bb[name], "ratio_at_centre": at_c,
                             "reading": (f"{a.replace('_', ' ')} beats {b.replace('_', ' ')} only while {text} {sign} {x:.2f}" if x is not None
                                         else f"no flip for {text} inside [{lo}, {hi}]: {a.replace('_', ' ')} {'wins' if at_c > 1 else 'loses'} throughout"),
                             "status": "scenario parameter (no published value)"})
    return pd.DataFrame(rows)


def escrow_breakevens(rules: dict | None = None, yoy_gain: float | None = None) -> pd.DataFrame:
    """What each town must show before the capacity tranche is released (the pre-agreed rules), and how many years capacity growth needs to cross the capacity bar."""
    r = {**escrow.DEFAULT_RULES, **(rules or {})}
    from . import state_capacity
    p = state_capacity.load_params()["national_anchor"]
    anchor = state_capacity.national_baseline()["admin_anchor"]
    gain = min(p["default_yoy_gain"] if yoy_gain is None else yoy_gain, p["max_yoy_gain"])
    rows = [{"threshold": "referral completion", "release_needs": f">= {r['referral_min']:.0%}", "current_assumed": f"{escrow.SCEN_REFERRAL:.0%} (scenario, not data)",
             "reading": f"the capacity tranche is released only if measured referral completion is at least {r['referral_min']:.0%}; no public measurement exists, so the pilot measures it"},
            {"threshold": "posts filled", "release_needs": f">= {r['posts_filled_min']:.0%}", "current_assumed": f"{escrow.SCEN_POSTS:.0%} (scenario, not data)",
             "reading": f"needs at least {r['posts_filled_min']:.0%} of budgeted PHC posts filled"},
            {"threshold": "transparent reporting", "release_needs": "published quarterly spend + spot check" if r["transparent_required"] else "not required", "current_assumed": "scenario rule from 2027",
             "reading": "a pre-agreed process rule the consortium commits to; it is the one threshold the pilot controls"}]
    need = r["admin_capacity_min"]
    yrs = 0 if anchor >= need else int(np.ceil((need - anchor) / gain)) if gain > 0 else None
    rows.append({"threshold": "district admin capacity", "release_needs": f">= {need:.2f}", "current_assumed": f"{anchor:.3f} (WGI GE 2025, national)",
                 "reading": (f"capacity {anchor:.3f} vs required {need:.2f}: " + ("already above" if yrs == 0 else f"crossed after {yrs} year(s) at +{gain:.2f}/yr" if yrs else "never crossed at zero growth"))})
    return pd.DataFrame(rows)


GREEK_ULTRAMAFIC_BOUND = 11.5 / 2176      # Botsou et al. 2022: total Cr(VI) 0.49-11.5 mg/kg vs total Cr 2,176-21,929 mg/kg => at most 0.53% for any pairing of the ranges (not Beqaa; abstract only)


def exposure_breakevens() -> pd.DataFrame:
    """Cr(VI) share of total chromium at which the child hazard quotient (soil + crop pathway) reaches 1, per sampled site. HQ is linear in the share between hq_low (all Cr(III)) and hq_high
    (all Cr(VI)): share* = (1 - hq_low) / (hq_high - hq_low). Below it the screening result is 'monitor', above it 'protective action'. Nobody has measured the share in Beqaa; the only published
    ultramafic-soil data found (Greece, not Beqaa) bound it at <= 0.53% of total Cr, which sits inside the window, so the speciation test is decisive."""
    s = m4_exposure.screen_sites()
    c = s[(s.parameter == "Cr") & s.hq_low.notna()].copy()
    c["cr6_share_at_hq1"] = (1 - c.hq_low) / (c.hq_high - c.hq_low)
    c["decisive_if_like_greek_ultramafic"] = c.cr6_share_at_hq1 < GREEK_ULTRAMAFIC_BOUND
    c["reading"] = c.apply(lambda r: f"{r.site_name} ({r.value_mg_kg:.0f} mg/kg total Cr): hazard quotient reaches 1 if Cr(VI) is above {r.cr6_share_at_hq1:.2%} of total Cr", axis=1)
    return c[["site_name", "value_mg_kg", "hq_low", "hq_high", "cr6_share_at_hq1", "decisive_if_like_greek_ultramafic", "reading"]].reset_index(drop=True)


def run(scored: pd.DataFrame | None = None, budget: float = 100_000) -> dict:
    scored = scored if scored is not None else m2.compute(rb.scenario_raw(None, 30, 0.1, rb.load_uncertainty()), spec=m2.load_spec())
    return {"allocation": allocation_breakevens(scored, budget), "escrow": escrow_breakevens(), "exposure": exposure_breakevens()}
