"""End-to-end pricing behaviour: rating factors must move premiums the right way."""

import pytest

from basis import price_funeral, price_life


def base_life(**over):
    kw = dict(issue_age=40, sex="male", smoker_status="nonsmoker",
              sum_assured=500_000, term=20, frequency="monthly")
    kw.update(over)
    return price_life(**kw)


def test_life_quote_is_positive_and_consistent():
    q = base_life()
    assert q.premium > 0
    assert q.annual_premium == pytest.approx(q.premium * 12, rel=1e-9)
    assert q.net_premium_rate < q.office_premium_rate  # expenses add a loading


def test_smoker_pays_more_than_nonsmoker():
    assert base_life(smoker_status="smoker").premium > base_life(smoker_status="nonsmoker").premium


def test_older_life_pays_more():
    assert base_life(issue_age=55).premium > base_life(issue_age=35).premium


def test_heavier_underwriting_rating_costs_more():
    assert base_life(underwriting_class="rated_200").premium > \
           base_life(underwriting_class="preferred").premium


def test_larger_sum_assured_has_lower_rate_per_unit():
    small = base_life(sum_assured=200_000)
    large = base_life(sum_assured=1_500_000)
    assert large.office_premium_rate < small.office_premium_rate


def test_longer_term_costs_more_per_period():
    assert base_life(term=30).premium > base_life(term=10).premium


def test_funeral_quote_prices_and_traces():
    q = price_funeral(issue_age=60, sex="female", sum_assured=30_000, frequency="monthly")
    assert q.premium > 0
    assert q.product == "funeral_wol"
    assert len(q.trace["benefits"]["years"]) > 10      # whole-of-life -> many years
    assert q.steps[-1]["label"].startswith("Per-period premium")


def test_frequency_changes_per_period_amount():
    annual = base_life(frequency="annual")
    monthly = base_life(frequency="monthly")
    # roughly 12x fewer rand per monthly payment than the annual single payment
    assert monthly.premium < annual.premium
    assert monthly.annual_premium == pytest.approx(monthly.premium * 12, rel=1e-9)
