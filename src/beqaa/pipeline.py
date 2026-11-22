"""One command rebuilds every output: python -m beqaa.pipeline  (M1 -> M4 -> M2 -> M5 -> allocation -> escrow).
Real-data-only rule: outputs/memo/ is written only when every dataset is real (overall mode REAL)."""
from __future__ import annotations


import pandas as pd

from . import (allocation, assumptions, escrow, robustness, funding_finder, io, m1_access, m2_need_score as m2, m4_exposure, m5_options,
               research_gaps, state_capacity, viz)
from .io import ROOT

PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
MEMO = ROOT / "outputs" / "memo"


def run(verbose: bool = True) -> dict:
    for d in (PROC, FIG, MEMO):
        d.mkdir(parents=True, exist_ok=True)
    problems = io.validate_consistency()
    if problems:
        raise SystemExit("Inconsistent datasets (set BEQAA_DATA=mock, or finish the converters):\n  " + "\n  ".join(problems))
    mode = io.overall_mode()
    is_mock = io.any_mock()                      # a dataset that is entirely mock; partly real datasets (real values plus labelled proxies) are not mock
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
    m2.method_sensitivity(raw).to_csv(PROC / "m2_method_sensitivity.csv", index=False)
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
    allocation.by_district(detail).to_csv(PROC / "allocation_by_district.csv", index=False)
    esc, esc_sum, warn = escrow.run(scored)
    from . import theme_kpi
    theme_kpi.kpi_table(scored=scored).to_csv(PROC / "theme_kpi.csv", index=False)                  # year x scenario: the theme KPI projection and who holds the money
    rb = robustness.run_all()                                           # N draws per scenario (data/params/uncertainty.yaml), fixed seed
    rb["rank"]["per_cadaster"].to_csv(PROC / "robust_rank_per_cadaster.csv", index=False)
    rb["rank"]["scenarios"].to_csv(PROC / "robust_rank_scenarios.csv", index=False)
    (PROC / "robust_core_set.txt").write_text(f"Core set (top-{rb['rank']['top_k']} in >= {rb['rank']['threshold']:.0%} of {rb['rank']['n_draws']} draws per scenario and in every scenario): "
                                              + (", ".join(rb["rank"]["core"]) if rb["rank"]["core"] else "EMPTY") + "\n" + (rb["rank"]["warning"] or "") + "\n")
    rb["regret"]["summary"].to_csv(PROC / "robust_regret_summary.csv", index=False)
    rb["regret"]["by_scenario"].to_csv(PROC / "robust_regret_by_scenario.csv", index=False)
    rb["breakpoints"].to_csv(PROC / "robust_breakpoints.csv", index=False)
    from . import breakeven, riders
    riders.run()
    from . import unit_costs
    unit_costs.run()
    be = breakeven.run(rb["scored"])
    pd.concat([be["allocation"].assign(kind="allocation"), be["escrow"].assign(kind="escrow release"), be["exposure"].assign(kind="exposure")], ignore_index=True).to_csv(PROC / "breakeven.csv", index=False)
    rb["escrow"].to_csv(PROC / "robust_escrow_degradation.csv", index=False)
    esc.to_csv(PROC / "escrow_schedule.csv", index=False)
    esc_sum.to_csv(PROC / "escrow_summary.csv", index=False)
    escrow.flow_links(esc).to_csv(PROC / "escrow_flow_links.csv", index=False)
    escrow.role_table(esc).to_csv(PROC / "escrow_roles.csv", index=False)
    escrow.by_district(esc).to_csv(PROC / "escrow_by_district.csv", index=False)
    state_capacity.anchored_governance().to_csv(PROC / "governance_capacity_anchored.csv", index=False)
    state_capacity.capacity_panel().to_csv(PROC / "state_capacity_panel.csv", index=False)
    # M2 x evidence: implementation-research candidates linked to registry rows
    gaps = research_gaps.cadaster_gaps(scored, rob)
    gaps.to_csv(PROC / "research_gaps_cadaster.csv", index=False)
    research_gaps.district_gaps(gaps).to_csv(PROC / "research_gaps_district.csv", index=False)
    research_gaps.research_candidates(gaps).to_csv(PROC / "research_candidates.csv", index=False)
    research_gaps.intervention_gaps(m4_exposure.tornado()).to_csv(PROC / "research_gaps_interventions.csv", index=False)
    fr = funding_finder.annotate(funding_finder.load_funding())
    funding_finder.rank_involvement(fr).to_csv(PROC / "funding_ranked.csv", index=False)
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
        # memo figures are written by scripts/make_figures.py (13 figures, figures/ and outputs/memo/); the pipeline writes the tables
        opt.to_csv(MEMO / "tab_options.csv", index=False)
        ev.to_csv(MEMO / "tab_evidence.csv", index=False)
        assum.to_csv(MEMO / "tab_assumptions.csv", index=False)
        (MEMO / "robustness.txt").write_text(txt)
    if verbose:
        print(f"Pipeline done. Data mode: {mode}. Processed -> {PROC}")
        print("Top 5 by Need Score:", ", ".join(scored.sort_values("rank").head(5).cadaster_name))
        print(txt)
        print("memo tables written to outputs/memo (figures: scripts/make_figures.py)" if not is_mock else "a dataset is entirely mock: outputs/memo/ intentionally left empty")
    return {"mode": mode}


if __name__ == "__main__":
    run()
