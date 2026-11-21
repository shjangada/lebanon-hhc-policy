"""One command rebuilds every output: python -m beqaa.pipeline  (M1 -> M4 -> M2 -> M5 -> allocation -> escrow).
Real-data-only rule: outputs/memo/ is written only when every dataset is real (overall mode REAL)."""
from __future__ import annotations

import shutil

import pandas as pd

from . import allocation, assumptions, escrow, io, m1_access, m2_need_score as m2, m4_exposure, m5_options, viz
from .io import ROOT

PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
MEMO = ROOT / "outputs" / "memo"


def run(verbose: bool = True) -> dict:
    for d in (PROC, FIG, MEMO):
        d.mkdir(parents=True, exist_ok=True)
    mode = io.overall_mode()
    is_mock = mode != "REAL"
    out = {}
    # M1
    acc = m1_access.access_by_cadaster(30, "women_15_49")
    acc.to_csv(PROC / "m1_access_by_cadaster.csv", index=False)
    m1_access.group_access(acc).to_csv(PROC / "m1_group_access.csv", index=False)
    m1_access.catchment_sensitivity().to_csv(PROC / "m1_catchment_sensitivity.csv", index=False)
    m1_access.mobile_unit_sites(3).to_csv(PROC / "m1_mobile_unit_sites.csv", index=False)
    # M4
    sites = m4_exposure.screen_sites()
    sites.to_csv(PROC / "m4_site_screen.csv", index=False)
    m4_exposure.tornado().to_csv(PROC / "m4_tornado.csv", index=False)
    ev = m4_exposure.evidence_table(sites)
    ev.to_csv(PROC / "m4_evidence.csv", index=False)
    # M2
    raw = m2.raw_indicators()
    scored = m2.compute(raw)
    scored.to_csv(PROC / "m2_need_score.csv", index=False)
    rob = m2.robustness(raw)
    rob.to_csv(PROC / "m2_robustness.csv", index=False)
    comp, hidden = m2.compare_official(scored)
    comp.to_csv(PROC / "m2_official_comparison.csv", index=False)
    hidden.to_csv(PROC / "m2_hidden_hotspots.csv", index=False)
    m2.group_need(scored).to_csv(PROC / "m2_group_need.csv", index=False)
    # M5 + allocation + escrow
    opt = m5_options.options_table(scored)
    opt.to_csv(PROC / "m5_options.csv", index=False)
    for name, b in m5_options.BUDGET_TIERS.items():
        m5_options.fundable_table(b).assign(budget_tier=name).to_csv(PROC / f"m5_fundable_{int(b)}.csv", index=False)
    summ, detail = allocation.simulate(scored, 100_000)
    summ.to_csv(PROC / "allocation_summary.csv", index=False)
    detail.to_csv(PROC / "allocation_detail.csv", index=False)
    esc, esc_sum, warn = escrow.run(scored)
    esc.to_csv(PROC / "escrow_schedule.csv", index=False)
    assum = assumptions.build()
    assum.to_csv(PROC / "assumptions.csv", index=False)
    # robustness statement
    stable = rob[rob.p_top_tier >= 0.9].cadaster_name.tolist()
    txt = (f"Data mode: {mode}.\nCadasters top-{m2.load_spec()['top_k']} in >=90% of random domain weightings: "
           f"{', '.join(stable) if stable else 'none'}.\n"
           f"Cadasters top-{m2.load_spec()['top_k']} in >=50%: {', '.join(rob[rob.p_top_tier >= 0.5].cadaster_name)}.\n")
    (PROC / "robustness.txt").write_text(txt)
    # figures (watermarked when mock)
    viz.priority_map(scored, is_mock, FIG / "fig1_priority_map.png")
    viz.access_lost(acc, is_mock, FIG / "fig2_access_lost.png")
    # memo outputs: REAL only
    if not is_mock:
        for f in ("fig1_priority_map.png", "fig2_access_lost.png"):
            shutil.copy(FIG / f, MEMO / f)
        opt.to_csv(MEMO / "tab_options.csv", index=False)
        ev.to_csv(MEMO / "tab_evidence.csv", index=False)
        assum.to_csv(MEMO / "tab_assumptions.csv", index=False)
        (MEMO / "robustness.txt").write_text(txt)
    if verbose:
        print(f"Pipeline done. Data mode: {mode}. Processed -> {PROC}")
        print("Top 5 by Need Score:", ", ".join(scored.sort_values("rank").head(5).cadaster_name))
        print(txt)
        print("memo outputs written" if not is_mock else "mock data: outputs/memo/ intentionally left empty")
    return {"mode": mode}


if __name__ == "__main__":
    run()
