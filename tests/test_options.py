"""Option pricing: textbook benchmark, parity, Greeks, MC convergence, implied vol."""

import math

import pytest

from basis import (
    black_scholes_price, greeks, implied_volatility, monte_carlo_price, price_option,
)

# Standard textbook case: S=K=100, T=1, r=5%, sigma=20%, no dividend.
BASE = dict(S=100, K=100, T=1.0, r=0.05, sigma=0.20, q=0.0)


def test_black_scholes_textbook_values():
    call = black_scholes_price(**BASE, option_type="call")
    put = black_scholes_price(**BASE, option_type="put")
    assert call == pytest.approx(10.4506, abs=1e-3)
    assert put == pytest.approx(5.5735, abs=1e-3)


def test_put_call_parity_holds():
    call = black_scholes_price(**BASE, option_type="call")
    put = black_scholes_price(**BASE, option_type="put")
    rhs = BASE["S"] * math.exp(-BASE["q"] * BASE["T"]) - BASE["K"] * math.exp(-BASE["r"] * BASE["T"])
    assert call - put == pytest.approx(rhs, abs=1e-9)


def test_call_delta_between_0_and_1_put_delta_negative():
    assert 0 < greeks(**BASE, option_type="call")["delta"] < 1
    assert greeks(**BASE, option_type="put")["delta"] < 0


def test_gamma_and_vega_positive_and_shared():
    cg = greeks(**BASE, option_type="call")
    pg = greeks(**BASE, option_type="put")
    assert cg["gamma"] > 0 and cg["vega_per_1pct"] > 0
    assert cg["gamma"] == pytest.approx(pg["gamma"], abs=1e-9)   # gamma/vega identical call vs put
    assert cg["vega_per_1pct"] == pytest.approx(pg["vega_per_1pct"], abs=1e-9)


def test_vega_matches_finite_difference():
    base = black_scholes_price(**{**BASE}, option_type="call")
    bumped = black_scholes_price(**{**BASE, "sigma": 0.21}, option_type="call")
    fd_vega_per_1pct = bumped - base
    assert greeks(**BASE, option_type="call")["vega_per_1pct"] == pytest.approx(fd_vega_per_1pct, abs=1e-2)


def test_monte_carlo_converges_to_closed_form():
    bs = black_scholes_price(**BASE, option_type="call")
    mc = monte_carlo_price(**BASE, option_type="call", n_sims=400_000, seed=1)
    # converges to the closed form: within a few standard errors
    assert abs(mc["price"] - bs) < 4 * mc["std_error"]
    assert mc["std_error"] < 0.05


def test_implied_vol_round_trips():
    price = black_scholes_price(**BASE, option_type="call")
    iv = implied_volatility(price, S=100, K=100, T=1.0, r=0.05, q=0.0, option_type="call")
    assert iv == pytest.approx(0.20, abs=1e-4)


def test_deep_itm_call_approaches_intrinsic_discounted():
    # very low vol, deep in the money -> ~ forward intrinsic
    p = black_scholes_price(S=150, K=100, T=1.0, r=0.05, sigma=0.01, q=0.0, option_type="call")
    assert p == pytest.approx(150 - 100 * math.exp(-0.05), abs=0.1)


def test_price_option_bundle():
    res = price_option(S=100, K=105, T=0.5, r=0.04, sigma=0.25, option_type="put", n_sims=50_000)
    assert res.price > 0
    assert len(res.value_curve) == 25
    assert abs(res.put_call_parity["residual"]) < 1e-6
    assert set(res.greeks) == {"delta", "gamma", "vega_per_1pct", "theta_per_day", "rho_per_1pct"}
