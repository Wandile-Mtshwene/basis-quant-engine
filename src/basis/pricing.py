"""Premium pricing for the Life and Funeral products.

Pulls together the mortality tables, the present-value maths and the rating
factors, and returns a fully itemised breakdown so every step is explainable:

  1. pick the base mortality table from sex + smoker status
  2. apply the underwriting-class mortality multiplier
  3. compute EPV of benefits  A  and EPV of the premium annuity  ä
  4. net premium rate       P_net = A / ä          (per unit sum assured)
  5. load for expenses and commission              -> office premium rate
  6. apply the sum-assured band discount and sum assured
  7. convert to the chosen payment frequency
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import actuarial as act
from .assumptions import DEFAULT_BASIS, PricingBasis
from .mortality import MortalityTable, load_elt, load_vbt


@dataclass
class Quote:
    """A priced quote with the full calculation trace."""

    product: str
    premium: float                 # payable each period (rand)
    frequency: str
    annual_premium: float          # total payable per year (rand)
    net_premium_rate: float        # net premium per unit sum assured
    office_premium_rate: float     # gross/office premium per unit sum assured
    epv_benefits: float            # A, per unit sum assured
    annuity: float                 # ä
    table: str
    inputs: dict = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)
    trace: dict = field(default_factory=dict)


def _apply_underwriting(table: MortalityTable, multiplier: float) -> MortalityTable:
    """Wrap a table so every rate is scaled by the underwriting multiplier
    (capped at 1.0 so a heavy rating never produces nonsensical q > 1)."""
    if multiplier == 1.0:
        return table

    class _Rated(MortalityTable):
        name = f"{table.name} x{multiplier:g}"

        def q(self, issue_age: int, policy_year: int) -> float:
            return min(1.0, table.q(issue_age, policy_year) * multiplier)

    return _Rated()


def _gross_premium(epv_benefits: float, annuity: float, sum_assured: float,
                   basis: PricingBasis) -> tuple[float, dict]:
    """Solve the equation of value for the annual office (gross) premium G, in rand.

        G·ä·(1 − renewal% − commission%) =
            SA·A + initial_fixed + initial_per_mille·SA/1000 + policy_fee·ä
    """
    e = basis.expenses
    epv_claims = sum_assured * epv_benefits
    epv_init = e.initial_fixed + e.initial_per_mille * sum_assured / 1000.0
    epv_policy_fee = e.policy_fee * annuity
    loadable = 1.0 - e.renewal_pct - e.commission_pct

    gross = (epv_claims + epv_init + epv_policy_fee) / (annuity * loadable)
    detail = {
        "epv_claims": epv_claims,
        "epv_initial_expenses": epv_init,
        "epv_policy_fee": epv_policy_fee,
        "renewal_pct": e.renewal_pct,
        "commission_pct": e.commission_pct,
        "loadable_fraction": loadable,
    }
    return gross, detail


def price_life(
    *,
    issue_age: int,
    sex: str,
    smoker_status: str,
    sum_assured: float,
    term: int,
    underwriting_class: str = "standard",
    frequency: str = "monthly",
    basis: PricingBasis = DEFAULT_BASIS,
) -> Quote:
    """Price a level term life assurance using the 2015 VBT tables."""
    base = load_vbt(sex, smoker_status)
    uw_mult = basis.rating.underwriting_multiplier(underwriting_class)
    table = _apply_underwriting(base, uw_mult)

    A = act.term_assurance(table, issue_age, term, basis.interest_rate, benefit_timing="end")
    annuity = act.annuity_due(
        table, issue_age, term, basis.interest_rate,
        frequency=basis.rating.frequency_payments(frequency),
    )
    return _assemble(
        product="life_term", table_name=base.name, A=A, annuity=annuity,
        sum_assured=sum_assured, frequency=frequency,
        sum_assured_mult=basis.rating.sum_assured_multiplier(sum_assured),
        basis=basis,
        inputs={
            "issue_age": issue_age, "sex": sex, "smoker_status": smoker_status,
            "sum_assured": sum_assured, "term": term,
            "underwriting_class": underwriting_class, "underwriting_multiplier": uw_mult,
            "frequency": frequency,
        },
    )


def price_funeral(
    *,
    issue_age: int,
    sex: str,
    sum_assured: float,
    frequency: str = "monthly",
    cover_to_age: int = 120,
    basis: PricingBasis = DEFAULT_BASIS,
) -> Quote:
    """Price a whole-of-life funeral benefit using the ELT population tables.
    Benefit is assumed paid mid-year (near-immediate funeral settlement).
    Funeral cover is not smoker- or underwriting-rated."""
    table = load_elt(sex)
    A = act.whole_life_assurance(
        table, issue_age, basis.interest_rate, benefit_timing="mid", omega=cover_to_age,
    )
    term = max(cover_to_age - issue_age, 1)
    annuity = act.annuity_due(
        table, issue_age, term, basis.interest_rate,
        frequency=basis.rating.frequency_payments(frequency),
    )
    return _assemble(
        product="funeral_wol", table_name=table.name, A=A, annuity=annuity,
        sum_assured=sum_assured, frequency=frequency,
        sum_assured_mult=1.0, basis=basis,
        inputs={
            "issue_age": issue_age, "sex": sex, "sum_assured": sum_assured,
            "cover_to_age": cover_to_age, "frequency": frequency,
        },
    )


def _assemble(
    *, product, table_name, A, annuity, sum_assured, frequency,
    sum_assured_mult, basis, inputs,
) -> Quote:
    net_rate = A.epv / annuity.epv
    gross_annual, loading = _gross_premium(A.epv, annuity.epv, sum_assured, basis)

    # Sum-assured band discount applies to the office premium.
    gross_annual *= sum_assured_mult
    office_rate_total = gross_annual / sum_assured

    m = basis.rating.frequency_payments(frequency)
    per_period = round(gross_annual / m, 2)
    annual_premium = round(per_period * m, 2)   # what the client actually pays

    steps = [
        {"step": 1, "label": "Base mortality table", "value": table_name},
        {"step": 2, "label": "EPV of benefits  A (per unit)", "value": round(A.epv, 6)},
        {"step": 3, "label": "Premium annuity  ä", "value": round(annuity.epv, 6)},
        {"step": 4, "label": "Net premium rate  A / ä", "value": round(net_rate, 6)},
        {"step": 5, "label": "Office premium rate (after expenses)", "value": round(office_rate_total, 6)},
        {"step": 6, "label": "Sum-assured band multiplier", "value": sum_assured_mult},
        {"step": 7, "label": "Annual office premium (rand)", "value": round(annual_premium, 2)},
        {"step": 8, "label": f"Per-period premium ({frequency})", "value": round(per_period, 2)},
    ]

    return Quote(
        product=product,
        premium=round(per_period, 2),
        frequency=frequency,
        annual_premium=round(annual_premium, 2),
        net_premium_rate=net_rate,
        office_premium_rate=office_rate_total,
        epv_benefits=A.epv,
        annuity=annuity.epv,
        table=table_name,
        inputs=inputs,
        steps=steps,
        trace={
            "interest_rate": basis.interest_rate,
            "expense_loading": loading,
            "benefits": asdict(A),
            "annuity": asdict(annuity),
        },
    )
