"""Loan affordability assessment and credit decisioning.

Three auditable stages, each of which records exactly why it reached its result:

  1. Affordability  - an NCA-style disposable-income and debt-to-income check.
  2. Scorecard      - a configurable points-based scorecard mapped to a
                      probability of default and a risk grade.
  3. Decision       - policy knock-out rules + affordability + grade combine
                      into approve / refer / decline, with the full reason trail.

The scorecard and policy are plain inspectable data (see :class:`CreditPolicy`)
so the whole rule book can be served to an admin view and audited.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Amortisation
# --------------------------------------------------------------------------- #
def monthly_installment(principal: float, annual_rate: float, term_months: int) -> float:
    """Level amortised monthly installment for a loan (PMT)."""
    if term_months <= 0:
        raise ValueError("term_months must be positive")
    r = annual_rate / 12.0
    if r == 0:
        return principal / term_months
    return principal * r / (1.0 - (1.0 + r) ** (-term_months))


# --------------------------------------------------------------------------- #
# Configurable policy & scorecard (the auditable rule book)
# --------------------------------------------------------------------------- #
@dataclass
class ScorecardCharacteristic:
    """One scorecard characteristic: ordered bins mapping an applicant value to
    points.  Each bin is (upper_bound_exclusive, points); the final bin uses inf."""

    name: str
    bins: list[tuple[float, int]]

    def points(self, value: float) -> tuple[int, str]:
        for upper, pts in self.bins:
            if value < upper:
                label = f"< {upper:g}" if upper != math.inf else "highest band"
                return pts, label
        return self.bins[-1][1], "highest band"


@dataclass
class CategoricalCharacteristic:
    name: str
    points_map: dict[str, int]

    def points(self, value: str) -> tuple[int, str]:
        return self.points_map.get(value, 0), value


@dataclass
class CreditPolicy:
    """Everything the decision depends on, in one inspectable place."""

    base_points: int = 580

    # scorecard calibration: at `base_score` the good:bad odds are `base_odds`,
    # and every `pdo` points doubles the odds.
    base_score: int = 600
    base_odds: float = 12.0
    pdo: int = 30

    # affordability
    max_installment_to_disposable: float = 0.90   # installment <= 90% of disposable
    max_total_dti: float = 0.40                    # all debt <= 40% of gross income

    # risk-grade PD bands (upper bound exclusive)
    grade_bands: list[tuple[str, float]] = field(default_factory=lambda: [
        ("A", 0.02), ("B", 0.05), ("C", 0.10), ("D", 0.20), ("E", 1.01),
    ])

    numeric: dict[str, ScorecardCharacteristic] = field(default_factory=lambda: {
        "age": ScorecardCharacteristic("age", [(21, -20), (25, 5), (35, 35), (50, 45), (65, 25), (math.inf, 5)]),
        "employment_months": ScorecardCharacteristic(
            "employment_months", [(6, -30), (24, 5), (60, 30), (math.inf, 45)]),
        "existing_accounts": ScorecardCharacteristic(
            "existing_accounts", [(1, -15), (3, 25), (6, 5), (math.inf, -35)]),
    })
    categorical: dict[str, CategoricalCharacteristic] = field(default_factory=lambda: {
        "employment_type": CategoricalCharacteristic("employment_type", {
            "permanent": 45, "contract": 10, "self_employed": 0, "unemployed": -60,
        }),
    })

    def grade_for_pd(self, pd: float) -> str:
        for grade, upper in self.grade_bands:
            if pd < upper:
                return grade
        return self.grade_bands[-1][0]

    def as_dict(self) -> dict:
        return {
            "base_points": self.base_points,
            "scorecard_calibration": {
                "base_score": self.base_score, "base_odds": self.base_odds, "pdo": self.pdo,
            },
            "affordability": {
                "max_installment_to_disposable": self.max_installment_to_disposable,
                "max_total_dti": self.max_total_dti,
            },
            "grade_bands": [{"grade": g, "pd_below": u} for g, u in self.grade_bands],
            "numeric_characteristics": {
                k: [{"below": (None if u == math.inf else u), "points": p} for u, p in c.bins]
                for k, c in self.numeric.items()
            },
            "categorical_characteristics": {k: c.points_map for k, c in self.categorical.items()},
        }


DEFAULT_POLICY = CreditPolicy()


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
@dataclass
class Affordability:
    disposable_income: float
    installment: float
    total_debt_after: float
    debt_to_income: float
    installment_to_disposable: float
    affordable: bool
    reasons: list[str]


@dataclass
class Scorecard:
    score: int
    probability_of_default: float
    grade: str
    breakdown: list[dict]


@dataclass
class CreditDecision:
    decision: str                 # approve | refer | decline
    installment: float
    affordability: Affordability
    scorecard: Scorecard
    reasons: list[str]
    inputs: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Stage 1: affordability
# --------------------------------------------------------------------------- #
def assess_affordability(
    *, gross_monthly_income, net_monthly_income, monthly_living_expenses,
    existing_monthly_debt, loan_amount, annual_rate, term_months,
    policy: CreditPolicy = DEFAULT_POLICY,
) -> Affordability:
    installment = monthly_installment(loan_amount, annual_rate, term_months)
    disposable = net_monthly_income - monthly_living_expenses - existing_monthly_debt
    total_debt_after = existing_monthly_debt + installment
    dti = total_debt_after / gross_monthly_income if gross_monthly_income else math.inf
    inst_to_disp = installment / disposable if disposable > 0 else math.inf

    reasons = []
    ok = True
    if disposable <= 0:
        ok = False
        reasons.append(f"No disposable income after expenses and existing debt (R{disposable:,.0f}).")
    if inst_to_disp > policy.max_installment_to_disposable:
        ok = False
        reasons.append(
            f"Installment is {inst_to_disp:.0%} of disposable income, above the "
            f"{policy.max_installment_to_disposable:.0%} limit.")
    if dti > policy.max_total_dti:
        ok = False
        reasons.append(
            f"Total debt-to-income {dti:.0%} exceeds the {policy.max_total_dti:.0%} policy limit.")
    if ok:
        reasons.append(
            f"Affordable: installment R{installment:,.0f} fits within disposable income R{disposable:,.0f}.")

    return Affordability(
        disposable_income=round(disposable, 2),
        installment=round(installment, 2),
        total_debt_after=round(total_debt_after, 2),
        debt_to_income=round(dti, 4),
        installment_to_disposable=round(inst_to_disp, 4),
        affordable=ok,
        reasons=reasons,
    )


# --------------------------------------------------------------------------- #
# Stage 2: scorecard
# --------------------------------------------------------------------------- #
def score_application(
    *, age, employment_type, employment_months, existing_accounts,
    policy: CreditPolicy = DEFAULT_POLICY,
) -> Scorecard:
    breakdown = [{"characteristic": "base", "value": "-", "points": policy.base_points}]
    score = policy.base_points

    for name, value in (("age", age), ("employment_months", employment_months),
                        ("existing_accounts", existing_accounts)):
        pts, band = policy.numeric[name].points(value)
        score += pts
        breakdown.append({"characteristic": name, "value": value, "band": band, "points": pts})

    pts, band = policy.categorical["employment_type"].points(employment_type)
    score += pts
    breakdown.append({"characteristic": "employment_type", "value": employment_type, "points": pts})

    # score -> odds -> probability of default
    log_odds = math.log(policy.base_odds) + (score - policy.base_score) / policy.pdo * math.log(2)
    odds = math.exp(log_odds)
    pd = 1.0 / (1.0 + odds)
    return Scorecard(
        score=int(score),
        probability_of_default=round(pd, 5),
        grade=policy.grade_for_pd(pd),
        breakdown=breakdown,
    )


# --------------------------------------------------------------------------- #
# Stage 3: decision
# --------------------------------------------------------------------------- #
def assess_credit(
    *, age, employment_type, employment_months, existing_accounts, adverse_history,
    gross_monthly_income, net_monthly_income, monthly_living_expenses,
    existing_monthly_debt, loan_amount, annual_rate, term_months,
    policy: CreditPolicy = DEFAULT_POLICY,
) -> CreditDecision:
    aff = assess_affordability(
        gross_monthly_income=gross_monthly_income, net_monthly_income=net_monthly_income,
        monthly_living_expenses=monthly_living_expenses, existing_monthly_debt=existing_monthly_debt,
        loan_amount=loan_amount, annual_rate=annual_rate, term_months=term_months, policy=policy)
    sc = score_application(age=age, employment_type=employment_type,
                           employment_months=employment_months,
                           existing_accounts=existing_accounts, policy=policy)

    reasons: list[str] = []
    decision = "approve"

    # hard policy knock-outs (always decline)
    if age < 18:
        decision = "decline"; reasons.append("Applicant under 18 (regulatory knock-out).")
    if adverse_history:
        decision = "decline"; reasons.append("Adverse credit history on file (policy knock-out).")
    if employment_type == "unemployed":
        decision = "decline"; reasons.append("Applicant is unemployed (policy knock-out).")
    if not aff.affordable:
        decision = "decline"; reasons.extend(aff.reasons)

    # grade-based routing when no knock-out fired
    if decision != "decline":
        if sc.grade in ("A", "B"):
            decision = "approve"
            reasons.append(f"Grade {sc.grade} (PD {sc.probability_of_default:.1%}) and affordable: approved.")
        elif sc.grade == "C":
            decision = "refer"
            reasons.append(f"Grade {sc.grade} (PD {sc.probability_of_default:.1%}): refer for manual review.")
        else:
            decision = "decline"
            reasons.append(f"Grade {sc.grade} (PD {sc.probability_of_default:.1%}) above risk appetite: declined.")

    return CreditDecision(
        decision=decision,
        installment=aff.installment,
        affordability=aff,
        scorecard=sc,
        reasons=reasons,
        inputs={
            "age": age, "employment_type": employment_type, "employment_months": employment_months,
            "existing_accounts": existing_accounts, "adverse_history": adverse_history,
            "gross_monthly_income": gross_monthly_income, "net_monthly_income": net_monthly_income,
            "monthly_living_expenses": monthly_living_expenses,
            "existing_monthly_debt": existing_monthly_debt, "loan_amount": loan_amount,
            "annual_rate": annual_rate, "term_months": term_months,
        },
    )
