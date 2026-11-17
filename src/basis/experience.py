"""Mortality experience analysis: actual versus expected (A/E) with credibility.

Given a dataset of exposure and observed deaths, this measures how actual
mortality compares with an expected basis (the 2015 VBT ultimate rates), by any
chosen segmentation, and applies limited-fluctuation credibility to temper small,
noisy cells.

Key quantities per segment:
  exposure        central exposed to risk (life-years)
  actual          observed deaths
  expected        Σ exposure · q_expected
  A/E             actual / expected
  Z               credibility factor, min(1, sqrt(actual / full_credibility))
  credible A/E    Z · (A/E) + (1 - Z) · 1.0   (complement is the expected basis)
  95% CI          A/E ± 1.96 · sqrt(actual) / expected   (Poisson)

Full credibility standard defaults to 1082 expected claims (90% within 5%).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd

from .mortality import load_vbt

_DATA = files("basis.data")

# 90% confidence that observed is within 5% of true: (1.645 / 0.05)^2
FULL_CREDIBILITY_CLAIMS = 1082.0


def expected_qx(age: int, sex: str, smoker_status: str) -> float:
    """Expected annual mortality rate on the 2015 VBT ultimate basis."""
    return load_vbt(sex, smoker_status).ultimate_qx(age)


@lru_cache(maxsize=1)
def load_experience_dataset() -> pd.DataFrame:
    """The vendored synthetic mortality-experience dataset
    (see scripts/generate_experience.py)."""
    return pd.read_csv(_DATA / "experience" / "mortality_experience.csv")


@dataclass
class ExperienceResult:
    by: list[str]
    segments: list[dict]
    overall: dict
    full_credibility_claims: float = FULL_CREDIBILITY_CLAIMS
    expected_basis: str = "2015 VBT ultimate"


def _expected_deaths(df: pd.DataFrame) -> np.ndarray:
    q = np.array([
        expected_qx(int(r.age), str(r.sex), str(r.smoker_status))
        for r in df.itertuples(index=False)
    ])
    return df["exposure"].to_numpy(dtype=float) * q


def analyse_experience(
    df: pd.DataFrame,
    by: list[str] | None = None,
    full_credibility: float = FULL_CREDIBILITY_CLAIMS,
) -> ExperienceResult:
    """Run an A/E analysis.  ``df`` needs columns age, sex, smoker_status,
    exposure, actual_deaths.  ``by`` lists the columns to segment on."""
    required = {"age", "sex", "smoker_status", "exposure", "actual_deaths"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    data = df.copy()
    data["expected_deaths"] = _expected_deaths(data)

    def summarise(sub: pd.DataFrame) -> dict:
        actual = float(sub["actual_deaths"].sum())
        expected = float(sub["expected_deaths"].sum())
        exposure = float(sub["exposure"].sum())
        ae = actual / expected if expected > 0 else float("nan")
        z = min(1.0, (actual / full_credibility) ** 0.5) if actual > 0 else 0.0
        credible_ae = z * ae + (1 - z) * 1.0
        half = 1.96 * (actual ** 0.5) / expected if expected > 0 else float("nan")
        return {
            "exposure": round(exposure, 1),
            "actual": round(actual, 1),
            "expected": round(expected, 2),
            "ae": round(ae, 4),
            "ae_pct": round(ae * 100, 1),
            "credibility": round(z, 4),
            "credible_ae": round(credible_ae, 4),
            "credible_ae_pct": round(credible_ae * 100, 1),
            "ci_low_pct": round((ae - half) * 100, 1),
            "ci_high_pct": round((ae + half) * 100, 1),
        }

    segments: list[dict] = []
    if by:
        for keys, sub in data.groupby(by, sort=True):
            keys = keys if isinstance(keys, tuple) else (keys,)
            seg = {col: (int(v) if isinstance(v, (np.integer,)) else v)
                   for col, v in zip(by, keys)}
            seg.update(summarise(sub))
            segments.append(seg)

    return ExperienceResult(
        by=by or [],
        segments=segments,
        overall=summarise(data),
        full_credibility_claims=full_credibility,
    )
