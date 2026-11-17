"""basis - an open-core actuarial pricing engine.

Public API for pricing the Life (term assurance) and Funeral (whole-of-life)
products, built on real public mortality tables (2015 VBT and ELT No. 15).
"""

from .assumptions import DEFAULT_BASIS, PricingBasis
from .mortality import load_elt, load_vbt
from .pricing import Quote, price_funeral, price_life

__all__ = [
    "price_life",
    "price_funeral",
    "Quote",
    "PricingBasis",
    "DEFAULT_BASIS",
    "load_vbt",
    "load_elt",
]

__version__ = "0.1.0"
