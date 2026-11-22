import numpy as np
import pytest

from beqaa import breakeven, m2_need_score as m2, robustness as rb


@pytest.fixture(scope="module")
def setup():
    unc = rb.load_uncertainty()
    scored = m2.compute(rb.scenario_raw(None, 30, 0.1, unc), spec=m2.load_spec())
    return scored, unc


def test_centre_ratios_match_the_engine_ordering(setup):
    """With every parameter at the centre of its range, the break-even report's ratios equal the allocation engine's values (same ordering as the regret ranking)."""
    scored, unc = setup
    be = breakeven.allocation_breakevens(scored, 100_000, unc)
    eng, base = breakeven._engine(scored, 100_000, unc)
    v = {p: eng.value(p, base) for p in rb.POLICIES}
    r = be[(be.comparison == "community vs status quo") & (be.parameter == "capture") & be.priorities.str.startswith("community priorities as modelled")].iloc[0]
    assert np.isclose(r.ratio_at_centre, v["community"] / v["existing_allocation"])
    r2 = be[(be.comparison == "community vs top-down by need") & (be.parameter == "local_fit") & be.priorities.str.startswith("community priorities as modelled")].iloc[0]
    assert np.isclose(r2.ratio_at_centre, v["community"] / v["top_down"])


def test_flip_points_are_real_flips(setup):
    scored, unc = setup
    be = breakeven.allocation_breakevens(scored, 100_000, unc)
    eng, base = breakeven._engine(scored, 100_000, unc)
    for r in be[be.flips_at.notna()].itertuples():
        a, b = ("community", "existing_allocation") if "status quo" in r.comparison else ("community", "top_down")
        bb = {**base, "alignment": 1.0 if r.priorities.startswith("community picks") else 0.0}
        eps = 1e-3
        lo, hi = ({**bb, r.parameter: r.flips_at - eps}, {**bb, r.parameter: r.flips_at + eps})
        ra, rb_ = eng.value(a, lo) / eng.value(b, lo), eng.value(a, hi) / eng.value(b, hi)
        assert (ra - 1) * (rb_ - 1) <= 0, r


def test_escrow_breakevens_follow_the_rules():
    t = breakeven.escrow_breakevens()
    assert set(t.threshold) == {"referral completion", "posts filled", "transparent reporting", "district admin capacity"}
    assert "40%" in t.loc[t.threshold == "referral completion", "release_needs"].iloc[0]


def test_assumptions_doc_quotes_the_breakevens():
    """docs/ASSUMPTIONS_PILOT.md quotes the break-even numbers: they must match the computed table (rounded)."""
    import pathlib

    import pandas as pd
    root = pathlib.Path(__file__).resolve().parents[1]
    doc = (root / "docs" / "ASSUMPTIONS_PILOT.md").read_text()
    f = root / "data" / "processed" / "breakeven.csv"
    if not f.exists():
        pytest.skip("run the pipeline first")
    b = pd.read_csv(f)
    b = b[(b.kind == "allocation") & b.priorities.str.startswith("community picks") & (b.comparison == "community vs status quo")].set_index("parameter")
    assert f"{b.loc['capture', 'flips_at'] * 100:.1f}%" in doc and f"{b.loc['local_fit', 'flips_at']:.2f}" in doc


def test_memo_docs_exist_and_never_claim_a_health_effect():
    import pathlib
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs"
    for f in ("EVIDENCE_TABLE.md", "STAKEHOLDERS.md", "NARRATIVE.md", "RIDER_SHORTLIST.md", "HEADLINE_AUDIT.md", "ASSUMPTIONS_PILOT.md"):
        assert (docs / f).exists(), f
    ev = (docs / "EVIDENCE_TABLE.md").read_text()
    rows = [l for l in ev.splitlines() if l.startswith("| ") and l[2].isdigit()]
    assert rows and not any(" | c | " in r and "Beqaa" in r.split(" | c | ")[1] for r in rows)       # no rung (c) for Beqaa
    assert "white phosphorus" in ev and "not white phosphorus" in ev.lower() or "Total P is not white phosphorus" in ev


def test_appendix_notebook_and_memo_figures_exist():
    import json
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    nb = json.loads((root / "notebooks" / "appendix.ipynb").read_text())
    assert nb["nbformat"] == 4 and any("make_figures" in "".join(c["source"]) for c in nb["cells"])
    figs = sorted(p.name for p in (root / "outputs" / "memo").glob("fig*.png"))
    assert len(figs) >= 6, figs
    exported = sorted(p.name for p in (root / "figures").glob("fig*.png"))
    assert len(exported) == 13 and exported == sorted(p.name for p in (root / "outputs" / "memo").glob("fig*.png"))      # figures/ is the 2x export; outputs/memo mirrors it
