"""European option pricing and risk: Black-Scholes, Greeks, Monte Carlo and
implied volatility.

Implemented with only ``numpy`` and the standard library (the normal CDF comes
from ``math.erf``), so there is no heavy dependency and it deploys as a small
serverless function.  The Monte Carlo price converges to the closed form, which
is exactly what the tests check, alongside put-call parity and implied-vol
round-tripping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

SQRT2 = math.sqrt(2.0)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1_d2(S, K, T, r, sigma, q):
    vol = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / vol
    return d1, d1 - vol


@dataclass
class OptionResult:
    option_type: str
    price: float
    d1: float
    d2: float
    greeks: dict
    monte_carlo: dict
    put_call_parity: dict
    value_curve: list[dict] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)


def black_scholes_price(S, K, T, r, sigma, q=0.0, option_type="call") -> float:
    """Black-Scholes price of a European option (continuous dividend yield q)."""
    if T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
        return intrinsic
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    disc_r, disc_q = math.exp(-r * T), math.exp(-q * T)
    if option_type == "call":
        return S * disc_q * _norm_cdf(d1) - K * disc_r * _norm_cdf(d2)
    return K * disc_r * _norm_cdf(-d2) - S * disc_q * _norm_cdf(-d1)


def greeks(S, K, T, r, sigma, q=0.0, option_type="call") -> dict:
    """Analytic Greeks.  Reported in common market conventions: vega per 1 vol
    point, theta per calendar day, rho per 1% rate move."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    disc_r, disc_q = math.exp(-r * T), math.exp(-q * T)
    pdf = _norm_pdf(d1)
    sqrtT = math.sqrt(T)

    gamma = disc_q * pdf / (S * sigma * sqrtT)
    vega = S * disc_q * pdf * sqrtT
    if option_type == "call":
        delta = disc_q * _norm_cdf(d1)
        theta = (-S * disc_q * pdf * sigma / (2 * sqrtT)
                 - r * K * disc_r * _norm_cdf(d2) + q * S * disc_q * _norm_cdf(d1))
        rho = K * T * disc_r * _norm_cdf(d2)
    else:
        delta = -disc_q * _norm_cdf(-d1)
        theta = (-S * disc_q * pdf * sigma / (2 * sqrtT)
                 + r * K * disc_r * _norm_cdf(-d2) - q * S * disc_q * _norm_cdf(-d1))
        rho = -K * T * disc_r * _norm_cdf(-d2)

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 6),
        "vega_per_1pct": round(vega / 100.0, 6),
        "theta_per_day": round(theta / 365.0, 6),
        "rho_per_1pct": round(rho / 100.0, 6),
    }


def monte_carlo_price(S, K, T, r, sigma, q=0.0, option_type="call",
                      n_sims=100_000, seed=7) -> dict:
    """Risk-neutral Monte Carlo price under geometric Brownian motion."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_sims)
    ST = S * np.exp((r - q - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
    payoff = np.maximum(ST - K, 0.0) if option_type == "call" else np.maximum(K - ST, 0.0)
    disc = math.exp(-r * T)
    price = disc * payoff.mean()
    stderr = disc * payoff.std(ddof=1) / math.sqrt(n_sims)
    return {
        "price": round(float(price), 4),
        "std_error": round(float(stderr), 4),
        "ci95": [round(float(price - 1.96 * stderr), 4), round(float(price + 1.96 * stderr), 4)],
        "n_sims": n_sims,
    }


def implied_volatility(price, S, K, T, r, q=0.0, option_type="call") -> float | None:
    """Back out the Black-Scholes volatility that reproduces a given price.
    Newton-Raphson on vega with a bisection fallback."""
    intrinsic = (max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)) * math.exp(-r * T)
    if price < intrinsic - 1e-8:
        return None

    sigma = 0.2
    for _ in range(50):
        p = black_scholes_price(S, K, T, r, sigma, q, option_type)
        v = greeks(S, K, T, r, sigma, q, option_type)["vega_per_1pct"] * 100.0
        if v < 1e-10:
            break
        step = (p - price) / v
        sigma -= step
        if sigma <= 0:
            sigma = 1e-4
        if abs(step) < 1e-8:
            return round(sigma, 6)

    lo, hi = 1e-4, 5.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if black_scholes_price(S, K, T, r, mid, q, option_type) > price:
            hi = mid
        else:
            lo = mid
    return round(0.5 * (lo + hi), 6)


def price_option(*, S, K, T, r, sigma, q=0.0, option_type="call",
                 n_sims=100_000, curve_points=25) -> OptionResult:
    """Full pricing: closed-form price, Greeks, a Monte Carlo cross-check, the
    put-call parity residual, and a value-versus-spot curve for plotting."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    price = black_scholes_price(S, K, T, r, sigma, q, option_type)

    call = black_scholes_price(S, K, T, r, sigma, q, "call")
    put = black_scholes_price(S, K, T, r, sigma, q, "put")
    parity_lhs = call - put
    parity_rhs = S * math.exp(-q * T) - K * math.exp(-r * T)

    lo, hi = 0.5 * S, 1.5 * S
    curve = []
    for i in range(curve_points):
        s = lo + (hi - lo) * i / (curve_points - 1)
        intrinsic = max(s - K, 0.0) if option_type == "call" else max(K - s, 0.0)
        curve.append({
            "spot": round(s, 2),
            "value": round(black_scholes_price(s, K, T, r, sigma, q, option_type), 4),
            "intrinsic": round(intrinsic, 4),
        })

    return OptionResult(
        option_type=option_type,
        price=round(price, 4),
        d1=round(d1, 6),
        d2=round(d2, 6),
        greeks=greeks(S, K, T, r, sigma, q, option_type),
        monte_carlo=monte_carlo_price(S, K, T, r, sigma, q, option_type, n_sims),
        put_call_parity={
            "call_minus_put": round(parity_lhs, 6),
            "forward_value": round(parity_rhs, 6),
            "residual": round(parity_lhs - parity_rhs, 9),
        },
        value_curve=curve,
        inputs={"S": S, "K": K, "T": T, "r": r, "sigma": sigma, "q": q,
                "option_type": option_type},
    )
