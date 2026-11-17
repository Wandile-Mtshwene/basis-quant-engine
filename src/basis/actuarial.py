"""Core actuarial present-value functions.

Everything here works off a :class:`~basis.mortality.MortalityTable` and returns
values *per unit sum assured*.  The functions also return a structured trace so
the API and UI can show every intermediate quantity (survival curve, discount
factors, year-by-year expected discounted cashflows) rather than just a number.

Notation (standard actuarial):
  v = 1 / (1 + i)                 one-year discount factor
  d = i / (1 + i)                 discount rate
  tpx                            probability a life aged x survives t years
  A^1_{x:n}                       EPV of a term assurance, benefit 1
  A_x                            EPV of a whole-of-life assurance, benefit 1
  ä_{x:n}                         EPV of a temporary annuity-due, payment 1
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .mortality import MortalityTable


@dataclass
class AssuranceResult:
    """EPV of an assurance plus the full calculation trace."""

    epv: float
    years: list[int]
    survival: list[float]          # tpx at start of each policy year
    death_prob: list[float]        # prob of dying in each policy year
    discount: list[float]          # discount factor applied to each year's claim
    expected_discounted: list[float]  # contribution of each year to the EPV


@dataclass
class AnnuityResult:
    epv: float
    years: list[int]
    survival: list[float]
    discount: list[float]
    expected_discounted: list[float]
    frequency: int = 1
    frequency_adjustment: float = 0.0


def discount_factor(i: float) -> float:
    return 1.0 / (1.0 + i)


# --------------------------------------------------------------------------- #
# Assurances
# --------------------------------------------------------------------------- #
def term_assurance(
    table: MortalityTable,
    issue_age: int,
    term: int,
    i: float,
    *,
    benefit_timing: str = "end",
) -> AssuranceResult:
    """EPV of a term assurance paying 1 on death within ``term`` years.

    ``benefit_timing``: ``"end"`` pays at the end of the year of death
    (claims settled annually); ``"mid"`` pays mid-year, a common proxy for the
    near-immediate settlement of funeral claims.
    """
    v = discount_factor(i)
    p = table.survival_curve(issue_age, term)          # length term + 1
    exponent = 1.0 if benefit_timing == "end" else 0.5

    years, death_prob, disc, contrib = [], [], [], []
    epv = 0.0
    for t in range(term):
        dq = p[t] - p[t + 1]                            # prob of death in year t+1
        df = v ** (t + exponent)
        c = df * dq
        epv += c
        years.append(t + 1)
        death_prob.append(float(dq))
        disc.append(float(df))
        contrib.append(float(c))

    return AssuranceResult(
        epv=float(epv),
        years=years,
        survival=[float(x) for x in p[:-1]],
        death_prob=death_prob,
        discount=disc,
        expected_discounted=contrib,
    )


def whole_life_assurance(
    table: MortalityTable,
    issue_age: int,
    i: float,
    *,
    benefit_timing: str = "end",
    omega: int = 120,
) -> AssuranceResult:
    """EPV of a whole-of-life assurance.  The table is closed at ``omega``
    (mortality forced to 1) so the cover is certain to pay out."""
    term = max(omega - issue_age, 1)
    v = discount_factor(i)
    exponent = 1.0 if benefit_timing == "end" else 0.5

    # survival curve with the table closed at omega
    p = np.empty(term + 1)
    p[0] = 1.0
    for t in range(1, term + 1):
        q = 1.0 if (issue_age + t - 1) >= omega - 1 else table.q(issue_age, t)
        p[t] = p[t - 1] * (1.0 - q)

    years, death_prob, disc, contrib = [], [], [], []
    epv = 0.0
    for t in range(term):
        dq = p[t] - p[t + 1]
        df = v ** (t + exponent)
        c = df * dq
        epv += c
        years.append(t + 1)
        death_prob.append(float(dq))
        disc.append(float(df))
        contrib.append(float(c))

    return AssuranceResult(
        epv=float(epv),
        years=years,
        survival=[float(x) for x in p[:-1]],
        death_prob=death_prob,
        discount=disc,
        expected_discounted=contrib,
    )


# --------------------------------------------------------------------------- #
# Annuities (premium payment streams)
# --------------------------------------------------------------------------- #
def annuity_due(
    table: MortalityTable,
    issue_age: int,
    term: int,
    i: float,
    *,
    frequency: int = 1,
) -> AnnuityResult:
    """EPV of a temporary annuity-due of 1 per year, payable while the life
    survives, for ``term`` years.  ``frequency`` applies the standard UDD
    m-thly adjustment ä^(m) ≈ ä − (m−1)/(2m)·(1 − v^n·npx)."""
    v = discount_factor(i)
    p = table.survival_curve(issue_age, term)

    years, disc, contrib = [], [], []
    epv = 0.0
    for t in range(term):
        df = v ** t
        c = df * p[t]
        epv += c
        years.append(t + 1)
        disc.append(float(df))
        contrib.append(float(c))

    adj = 0.0
    if frequency > 1:
        n_px = p[term]
        adj = (frequency - 1) / (2 * frequency) * (1 - v ** term * n_px)
        epv -= adj

    return AnnuityResult(
        epv=float(epv),
        years=years,
        survival=[float(x) for x in p[:-1]],
        discount=disc,
        expected_discounted=contrib,
        frequency=frequency,
        frequency_adjustment=float(adj),
    )
