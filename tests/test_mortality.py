"""Checks on the real vendored mortality tables and rating-factor ordering."""

import pytest

from basis.mortality import load_elt, load_vbt


def test_vbt_rates_are_valid_probabilities():
    for sex in ("male", "female"):
        for smoker in ("nonsmoker", "smoker"):
            t = load_vbt(sex, smoker)
            for age in (20, 40, 60, 80):
                q = t.q(age, 1)
                assert 0.0 <= q <= 1.0


def test_smokers_have_higher_mortality_than_nonsmokers():
    for sex in ("male", "female"):
        ns = load_vbt(sex, "nonsmoker")
        sm = load_vbt(sex, "smoker")
        for age in (35, 45, 55, 65):
            assert sm.q(age, 1) > ns.q(age, 1)


def test_males_have_higher_mortality_than_females_nonsmoker():
    m = load_vbt("male", "nonsmoker")
    f = load_vbt("female", "nonsmoker")
    for age in (40, 50, 60, 70):
        assert m.q(age, 1) >= f.q(age, 1)


def test_select_mortality_below_ultimate_at_same_attained_age():
    """Recently underwritten (select) lives have lower mortality than lives at
    the same attained age who are already in the ultimate period."""
    t = load_vbt("male", "nonsmoker")
    select_q = t.q(40, 1)           # just selected, attained age 40
    ultimate_q = t.q(15, 26)        # attained age 40 but 26 years in -> ultimate
    assert select_q < ultimate_q


def test_mortality_increases_with_age():
    t = load_elt("male")
    rates = [t.qx(a) for a in range(30, 90, 10)]
    assert rates == sorted(rates)


def test_elt_spans_full_life():
    assert load_elt("male").min_age == 0
    assert load_elt("female").max_age >= 100
