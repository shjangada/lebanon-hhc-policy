import pytest

from beqaa import io, sensitivity as sv

need = pytest.mark.skipif(not (io.PROCESSED / "esu_by_district.csv").exists(), reason="run ingest")


@need
def test_tornado_defaults_reproduce_the_baseline_and_ranges_bracket_it(monkeypatch):
    monkeypatch.setenv("BEQAA_DATA", "auto")
    t = sv.tornado("cost_per_notified_case")
    assert (t.swing >= 0).all() and t.swing.is_monotonic_decreasing and t.baseline_output.nunique() == 1
    for r in t.itertuples():
        lo, hi = sorted((r.output_at_low, r.output_at_high))
        assert lo <= r.baseline_output * 1.001 or r.parameter == "relative risk (filtration, 95% CI)"        # RR default is the point estimate, between the CI ends
        assert lo <= r.baseline_output * 1.2 and hi >= r.baseline_output * 0.8
    top = t.iloc[0]
    assert top.parameter.startswith("transfer")                                                             # the biggest cost driver is the transfer assumption


@need
def test_sensitivity_summary_says_the_conclusion_does_not_flip(monkeypatch):
    monkeypatch.setenv("BEQAA_DATA", "auto")
    s = sv.summary()
    assert s["conclusion_flips"] is False and s["cost_range_over_all_one_way_runs"][0] > 20.03             # never as cheap as one visit
    assert 0 <= s["load_baseline"] <= s["load_max_over_all_one_way_runs"] <= 1
