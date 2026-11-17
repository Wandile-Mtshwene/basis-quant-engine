"""Affordability, scorecard and decision logic."""

import math

import pytest

from basis import (
    DEFAULT_POLICY, assess_affordability, assess_credit, monthly_installment, score_application,
)

AFFORD = dict(gross_monthly_income=45_000, net_monthly_income=33_000,
              monthly_living_expenses=12_000, existing_monthly_debt=4_000,
              loan_amount=150_000, annual_rate=0.18, term_months=48)
STRONG = dict(age=40, employment_type="permanent", employment_months=120, existing_accounts=2)


# --------------------------- amortisation ---------------------------------- #
def test_installment_matches_closed_form():
    assert monthly_installment(100_000, 0.12, 12) == pytest.approx(8884.88, abs=0.01)


def test_zero_rate_is_straight_line():
    assert monthly_installment(120_000, 0.0, 24) == pytest.approx(5000.0)


def test_installment_increases_with_amount_and_rate():
    base = monthly_installment(100_000, 0.15, 60)
    assert monthly_installment(200_000, 0.15, 60) > base
    assert monthly_installment(100_000, 0.25, 60) > base


# --------------------------- affordability --------------------------------- #
def test_affordable_case():
    a = assess_affordability(**AFFORD)
    assert a.affordable
    assert a.disposable_income == pytest.approx(33_000 - 12_000 - 4_000)


def test_unaffordable_when_installment_too_large():
    a = assess_affordability(gross_monthly_income=20_000, net_monthly_income=15_000,
                             monthly_living_expenses=9_000, existing_monthly_debt=5_000,
                             loan_amount=300_000, annual_rate=0.22, term_months=24)
    assert not a.affordable
    assert any("disposable" in r.lower() or "debt-to-income" in r.lower() for r in a.reasons)


# --------------------------- scorecard ------------------------------------- #
def test_stronger_profile_scores_higher_and_lower_pd():
    strong = score_application(**STRONG)
    weak = score_application(age=20, employment_type="self_employed",
                             employment_months=3, existing_accounts=8)
    assert strong.score > weak.score
    assert strong.probability_of_default < weak.probability_of_default


def test_grades_span_the_range():
    grades = {
        "A": score_application(**STRONG).grade,
        "C": score_application(age=23, employment_type="self_employed",
                               employment_months=20, existing_accounts=2).grade,
        "E": score_application(age=20, employment_type="self_employed",
                               employment_months=3, existing_accounts=8).grade,
    }
    assert grades["A"] == "A"
    assert grades["C"] == "C"
    assert grades["E"] == "E"


def test_score_breakdown_sums_to_total():
    sc = score_application(**STRONG)
    assert sum(item["points"] for item in sc.breakdown) == sc.score


# --------------------------- decision -------------------------------------- #
def test_strong_affordable_approves():
    d = assess_credit(**STRONG, **AFFORD, adverse_history=False)
    assert d.decision == "approve"


def test_grade_c_is_referred():
    d = assess_credit(age=23, employment_type="self_employed", employment_months=20,
                      existing_accounts=2, adverse_history=False, **AFFORD)
    assert d.scorecard.grade == "C"
    assert d.decision == "refer"


def test_weak_grade_declined():
    d = assess_credit(age=20, employment_type="self_employed", employment_months=3,
                      existing_accounts=8, adverse_history=False, **AFFORD)
    assert d.decision == "decline"


@pytest.mark.parametrize("override,reason_key", [
    ({"age": 17}, "under 18"),
    ({"adverse_history": True}, "adverse"),
    ({"employment_type": "unemployed"}, "unemployed"),
])
def test_hard_knockouts_decline(override, reason_key):
    kw = {**STRONG, **AFFORD, "adverse_history": False, **override}
    d = assess_credit(**kw)
    assert d.decision == "decline"
    assert any(reason_key in r.lower() for r in d.reasons)


def test_unaffordable_declines_regardless_of_score():
    d = assess_credit(**STRONG, adverse_history=False,
                      gross_monthly_income=20_000, net_monthly_income=15_000,
                      monthly_living_expenses=9_000, existing_monthly_debt=5_000,
                      loan_amount=300_000, annual_rate=0.22, term_months=24)
    assert d.decision == "decline"


def test_policy_as_dict_is_serialisable():
    d = DEFAULT_POLICY.as_dict()
    assert d["scorecard_calibration"]["pdo"] == 30
    assert d["affordability"]["max_total_dti"] == 0.40
    assert {g["grade"] for g in d["grade_bands"]} == {"A", "B", "C", "D", "E"}
    assert not any(math.isinf(v) for row in d["numeric_characteristics"].values()
                   for item in row for v in [item["below"]] if v is not None)
