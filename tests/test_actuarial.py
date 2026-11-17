"""Validate the present-value maths against closed-form benchmarks."""

import math

import pytest

from basis import actuarial as act
from basis.mortality import ConstantMortalityTable, load_vbt


# --------------------------------------------------------------------------- #
# Closed-form benchmark: with a flat mortality rate q and interest i, the net
# premium of a term assurance collapses to  P = A / ä = q·v = q / (1 + i).
# This is the single strongest proof that the whole chain is correct.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("q", [0.001, 0.01, 0.05])
@pytest.mark.parametrize("i", [0.0, 0.05, 0.09])
@pytest.mark.parametrize("n", [1, 10, 40])
def test_constant_mortality_net_premium_is_qv(q, i, n):
    table = ConstantMortalityTable(q)
    A = act.term_assurance(table, 40, n, i, benefit_timing="end")
    annuity = act.annuity_due(table, 40, n, i)
    net = A.epv / annuity.epv
    assert net == pytest.approx(q / (1 + i), rel=1e-12)


def test_annuity_due_sums_discounted_survival():
    """ä_{x:n} with no mortality is just an annuity-certain:  sum v^t."""
    table = ConstantMortalityTable(0.0)
    i, n = 0.09, 5
    v = 1 / (1 + i)
    expected = sum(v ** t for t in range(n))
    assert act.annuity_due(table, 30, n, i).epv == pytest.approx(expected, rel=1e-12)


def test_whole_life_identity_A_equals_1_minus_d_annuity():
    """Fundamental identity  A_x = 1 − d·ä_x  must hold exactly when the table
    is closed (end-of-year benefit, same closing age for both)."""
    table = load_vbt("male", "nonsmoker")
    i, x, omega = 0.06, 45, 120
    v = 1 / (1 + i)
    d = i * v
    A = act.whole_life_assurance(table, x, i, benefit_timing="end", omega=omega)
    term = omega - x
    annuity = act.annuity_due(table, x, term, i)
    assert A.epv == pytest.approx(1 - d * annuity.epv, abs=1e-9)


def test_death_probabilities_sum_to_mortality_over_term():
    """Σ (t-1|q) over the term equals 1 − tpx (prob of dying within the term)."""
    table = load_vbt("female", "smoker")
    A = act.term_assurance(table, 50, 20, 0.05)
    total_death = sum(A.death_prob)
    survive_term = table.survival_curve(50, 20)[-1]
    assert total_death == pytest.approx(1 - survive_term, abs=1e-12)


def test_mthly_annuity_is_smaller_than_annual():
    """The m-thly adjustment reduces the annuity-due EPV."""
    table = load_vbt("male", "nonsmoker")
    annual = act.annuity_due(table, 40, 20, 0.09, frequency=1).epv
    monthly = act.annuity_due(table, 40, 20, 0.09, frequency=12).epv
    assert monthly < annual
    assert math.isclose(annual - monthly, 11 / 24 * (1 - (1 / 1.09) ** 20 *
                        table.survival_curve(40, 20)[-1]), rel_tol=1e-9)
