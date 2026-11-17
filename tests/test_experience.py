"""Experience analysis: exact A/E arithmetic, credibility and the vendored data."""

import math

import pandas as pd
import pytest

from basis.experience import (
    FULL_CREDIBILITY_CLAIMS, analyse_experience, expected_qx, load_experience_dataset,
)


def one_cell(age, sex, smoker, exposure, deaths):
    return pd.DataFrame([{
        "age": age, "sex": sex, "smoker_status": smoker,
        "exposure": exposure, "actual_deaths": deaths,
    }])


def test_ae_is_actual_over_expected_exactly():
    exposure, deaths = 10_000.0, 60
    df = one_cell(50, "male", "nonsmoker", exposure, deaths)
    expected = exposure * expected_qx(50, "male", "nonsmoker")
    r = analyse_experience(df)
    assert r.overall["expected"] == pytest.approx(expected, rel=1e-9)
    assert r.overall["ae"] == pytest.approx(deaths / expected, rel=1e-9)


def test_credibility_formula_and_blend():
    deaths = 500
    df = one_cell(60, "male", "smoker", 20_000.0, deaths)
    r = analyse_experience(df).overall
    z = min(1.0, (deaths / FULL_CREDIBILITY_CLAIMS) ** 0.5)
    assert r["credibility"] == pytest.approx(z, abs=1e-4)   # stored rounded to 4dp
    # credible A/E sits between the raw A/E and the 100% expected basis
    assert r["credibility"] < 1.0
    lo, hi = sorted([r["ae"], 1.0])
    assert lo <= r["credible_ae"] <= hi


def test_full_credibility_reached_for_large_claim_counts():
    df = one_cell(70, "male", "nonsmoker", 500_000.0, 5000)
    r = analyse_experience(df).overall
    assert r["credibility"] == 1.0
    assert r["credible_ae"] == pytest.approx(r["ae"], rel=1e-9)


def test_confidence_interval_brackets_point_estimate():
    df = one_cell(55, "female", "nonsmoker", 30_000.0, 200)
    r = analyse_experience(df).overall
    assert r["ci_low_pct"] < r["ae_pct"] < r["ci_high_pct"]


def test_missing_columns_raise():
    with pytest.raises(ValueError):
        analyse_experience(pd.DataFrame({"age": [40]}))


# ---- behaviour on the vendored synthetic dataset (known distortions) ------- #
def test_dataset_shows_designed_signals():
    df = load_experience_dataset()
    overall = analyse_experience(df).overall
    assert overall["ae_pct"] > 100          # experience designed worse than table
    assert overall["credibility"] == 1.0    # plenty of claims overall

    by_smoker = {s["smoker_status"]: s for s in analyse_experience(df, by=["smoker_status"]).segments}
    assert by_smoker["smoker"]["ae_pct"] > by_smoker["nonsmoker"]["ae_pct"]
    # the baked-in smoker loading is ~12%
    ratio = by_smoker["smoker"]["ae"] / by_smoker["nonsmoker"]["ae"]
    assert 1.05 < ratio < 1.25


def test_segment_count_matches_distinct_values():
    df = load_experience_dataset()
    res = analyse_experience(df, by=["sex", "smoker_status"])
    assert len(res.segments) == 4
    assert all("ae_pct" in s and "exposure" in s for s in res.segments)
