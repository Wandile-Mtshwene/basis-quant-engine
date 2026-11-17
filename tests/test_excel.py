"""Prove the Excel parallel model reproduces the engine.

Builds the workbook, evaluates every live formula with an independent Excel
formula engine (the `formulas` library, nothing to do with our code), and checks
the spreadsheet lands on the same EPVs and premium as the Python engine.
"""

import warnings

import pytest

from basis import price_life
from basis.assumptions import DEFAULT_BASIS

formulas = pytest.importorskip("formulas")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "excel"))
import build_model  # noqa: E402


@pytest.fixture(scope="module")
def solved(tmp_path_factory):
    build_model.OUT = tmp_path_factory.mktemp("xl") / "Life_Premium_Model.xlsx"
    path = build_model.build()
    warnings.filterwarnings("ignore")
    xl = formulas.ExcelModel().loads(str(path)).finish()
    sol = xl.calculate()
    out = {}
    for k, v in sol.items():
        if "PREMIUM'!B" in k.upper():
            cell = k.upper().split("!")[1]
            try:
                out[cell] = float(v.value[0, 0])
            except Exception:
                out[cell] = v
    return out


@pytest.fixture(scope="module")
def engine_quote():
    return price_life(basis=DEFAULT_BASIS, **build_model.SCENARIO)


def test_excel_epv_benefits_matches_engine(solved, engine_quote):
    assert solved["B3"] == pytest.approx(engine_quote.epv_benefits, rel=1e-6)


def test_excel_annuity_matches_engine(solved, engine_quote):
    assert solved["B6"] == pytest.approx(engine_quote.annuity, rel=1e-6)


def test_excel_net_rate_matches_engine(solved, engine_quote):
    assert solved["B7"] == pytest.approx(engine_quote.net_premium_rate, rel=1e-6)


def test_excel_monthly_premium_matches_engine(solved, engine_quote):
    # within a cent of the engine's rounded premium
    assert solved["B14"] == pytest.approx(engine_quote.premium, abs=0.01)
