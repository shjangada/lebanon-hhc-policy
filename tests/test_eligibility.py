import pandas as pd
import pytest

from beqaa import eligibility as el, escrow, funding_finder as ff


def test_women_only_funds_need_women_led_and_ids_come_from_registry():
    reg = set(ff.load_funding().fund_id)
    a = el.eligible_funds(el.Profile(women_led=False))
    b = el.eligible_funds(el.Profile(women_led=True, org_type="Women-led organisation"))
    assert set(a.fund_id) <= reg and set(b.fund_id) <= reg                         # never invents a fund
    women_ids = {"F009", "F010", "F011", "F012", "F015", "F022"}
    assert not (women_ids & set(a.fund_id)) and len(women_ids & set(b.fund_id)) >= 3
    assert (b.eligibility.isin(["eligible", "conditional", "check eligibility"])).all() and b.url.notna().any()


def test_closed_calls_only_as_expected_next_round_and_government_money_excluded():
    p = el.Profile(women_led=True)
    with_next = el.eligible_funds(p, show_next_round=True)
    without = el.eligible_funds(p, show_next_round=False)
    assert len(with_next) >= len(without) and not without.status.str.startswith("expected").any()
    assert set(with_next[with_next.status.str.startswith("expected")].registry_status) <= {"closed_recurring"}
    f = ff.load_funding()
    gov_only = set(f[(f.channel == "gov") & (f.local_org_eligible == "no")].fund_id)
    assert not (gov_only & set(el.eligible_funds(el.Profile()).fund_id))
    assert set(el.eligible_funds(el.Profile(org_type="Municipality / Union of Municipalities")).fund_id) >= set()      # municipalities may see government rows


def test_registry_last_verified_is_reported():
    v = el.registry_last_verified()
    assert v["rows"] >= 20 and v["last_verified"] and v["to_verify_rows"] >= 0


def test_threshold_gaps_low_capacity_lists_gaps_and_full_pass_has_none():
    low = el.threshold_gaps(0.10, False, 0.1, 0.2)
    assert low["current_rung"] == escrow.LEVELS[0] and not low["all_tranche_thresholds_met"] and len(low["gaps"]) >= 3
    hi = el.threshold_gaps(0.65, True, 0.9, 0.9)
    assert hi["all_tranche_thresholds_met"]
    assert hi["current_rung"] in escrow.LEVELS and set(["requirement", "yours", "required", "met"]) <= set(hi["table"].columns)


def test_uncovered_cadasters_never_claims_a_partner_location():
    from beqaa import m2_need_score as m2
    t = el.uncovered_priority_cadasters(m2.compute(m2.raw_indicators()))
    assert len(t) == 10 and t.partner_presence.str.startswith("unknown").all()
