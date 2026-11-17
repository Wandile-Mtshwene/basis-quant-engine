"""basis - an open-core actuarial pricing engine.

Public API for pricing the Life (term assurance) and Funeral (whole-of-life)
products, built on real public mortality tables (2015 VBT and ELT No. 15).
"""

from .assumptions import DEFAULT_BASIS, PricingBasis
from .mortality import load_elt, load_vbt
from .pricing import Quote, price_funeral, price_life
from .credit import (
    CreditDecision,
    CreditPolicy,
    DEFAULT_POLICY,
    assess_affordability,
    assess_credit,
    monthly_installment,
    score_application,
)
from .options import (
    OptionResult,
    black_scholes_price,
    greeks,
    implied_volatility,
    monte_carlo_price,
    price_option,
)
from .retirement import RetirementProjection, project_retirement

__all__ = [
    "price_life",
    "price_funeral",
    "Quote",
    "PricingBasis",
    "DEFAULT_BASIS",
    "load_vbt",
    "load_elt",
    "project_retirement",
    "RetirementProjection",
    "assess_credit",
    "assess_affordability",
    "score_application",
    "monthly_installment",
    "CreditDecision",
    "CreditPolicy",
    "DEFAULT_POLICY",
    "price_option",
    "black_scholes_price",
    "greeks",
    "monte_carlo_price",
    "implied_volatility",
    "OptionResult",
]

__version__ = "0.1.0"
