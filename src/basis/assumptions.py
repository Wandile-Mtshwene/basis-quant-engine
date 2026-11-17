"""Pricing assumptions and rating-factor tables.

These are deliberately held as plain, inspectable data so the admin view can
render every number the premium depends on.  Values are illustrative (a demo
built on public mortality tables), not a specific insurer's rate book.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpenseBasis:
    """Expense and commission loadings used to turn a net premium into an
    office (gross) premium.

    Gross premium G solves:
        G · ä · (1 − renewal_pct − commission_pct) =
            SA · A  +  initial_fixed  +  initial_per_mille · SA/1000  +  policy_fee · ä
    """

    initial_fixed: float = 350.0        # once-off rand cost to set the policy up
    initial_per_mille: float = 1.5      # once-off cost per R1,000 of sum assured
    policy_fee: float = 60.0            # rand expense loaded into every year's premium
    renewal_pct: float = 0.05           # % of each premium for ongoing admin
    commission_pct: float = 0.03        # % of each premium paid as commission


@dataclass
class RatingFactors:
    """Multiplicative rating factors applied on top of the base table mortality
    and the net premium.  Every entry is a simple, auditable multiplier."""

    # Underwriting / health class -> mortality multiplier.
    underwriting_class: dict[str, float] = field(
        default_factory=lambda: {
            "preferred": 0.85,
            "standard": 1.00,
            "rated_125": 1.25,
            "rated_150": 1.50,
            "rated_200": 2.00,
        }
    )
    # Sum-assured band -> premium discount factor (larger policies, lower per-unit cost).
    sum_assured_bands: list[tuple[float, float, float]] = field(
        default_factory=lambda: [
            # (lower_inclusive, upper_exclusive, multiplier)
            (0, 250_000, 1.00),
            (250_000, 500_000, 0.97),
            (500_000, 1_000_000, 0.95),
            (1_000_000, float("inf"), 0.92),
        ]
    )
    # Premium frequency -> payments per year (drives the m-thly annuity adjustment).
    frequency: dict[str, int] = field(
        default_factory=lambda: {"annual": 1, "semiannual": 2, "quarterly": 4, "monthly": 12}
    )

    def underwriting_multiplier(self, uw_class: str) -> float:
        return self.underwriting_class[uw_class]

    def sum_assured_multiplier(self, sum_assured: float) -> float:
        for lo, hi, mult in self.sum_assured_bands:
            if lo <= sum_assured < hi:
                return mult
        return 1.0

    def frequency_payments(self, freq: str) -> int:
        return self.frequency[freq]


@dataclass
class PricingBasis:
    """The full set of assumptions behind a quote."""

    interest_rate: float = 0.09         # valuation / pricing interest rate (net of tax)
    expenses: ExpenseBasis = field(default_factory=ExpenseBasis)
    rating: RatingFactors = field(default_factory=RatingFactors)

    def as_dict(self) -> dict:
        """Flat, JSON-friendly view for the admin endpoint."""
        return {
            "interest_rate": self.interest_rate,
            "expenses": self.expenses.__dict__,
            "rating": {
                "underwriting_class": self.rating.underwriting_class,
                "sum_assured_bands": [
                    {"from": lo, "to": hi, "multiplier": m}
                    for lo, hi, m in self.rating.sum_assured_bands
                ],
                "frequency": self.rating.frequency,
            },
        }


# A single shared default basis the API and UI read from.
DEFAULT_BASIS = PricingBasis()
