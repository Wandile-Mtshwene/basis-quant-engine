"""FastAPI service exposing the basis pricing engine.

Every pricing endpoint supports an ``explain`` flag.  When set, the response
includes the full calculation trace (survival curve, discount factors,
year-by-year expected discounted cashflows and the expense loading) so the
backend is completely transparent and auditable, not a black box.

Run locally:
    uv run uvicorn api.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from basis import assess_credit, implied_volatility, price_funeral, price_life, price_option, project_retirement
from basis.assumptions import DEFAULT_BASIS
from basis.credit import DEFAULT_POLICY
from basis.experience import analyse_experience, load_experience_dataset
from basis.mortality import load_elt, load_vbt
from dataclasses import asdict

# Everything is served under /api so the same paths work locally and when the
# engine is deployed as a serverless function behind a Next.js front end.
app = FastAPI(
    title="Basis Pricing Engine",
    version="0.1.0",
    description=(
        "Actuarial pricing API for level term Life assurance and whole-of-life "
        "Funeral cover. Built on real public mortality tables (2015 VBT and "
        "ELT No. 15). Every quote can return its full calculation trace."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")


# --------------------------------------------------------------------------- #
# Request models (with validation)
# --------------------------------------------------------------------------- #
class LifeQuoteRequest(BaseModel):
    issue_age: int = Field(18, ge=18, le=80, description="Age at policy start")
    sex: Literal["male", "female"] = "male"
    smoker_status: Literal["nonsmoker", "smoker"] = "nonsmoker"
    sum_assured: float = Field(500_000, gt=0, le=50_000_000)
    term: int = Field(20, ge=1, le=50, description="Cover term in years")
    underwriting_class: Literal[
        "preferred", "standard", "rated_125", "rated_150", "rated_200"
    ] = "standard"
    frequency: Literal["annual", "semiannual", "quarterly", "monthly"] = "monthly"
    explain: bool = Field(True, description="Include the full calculation trace")


class FuneralQuoteRequest(BaseModel):
    issue_age: int = Field(45, ge=0, le=85)
    sex: Literal["male", "female"] = "female"
    sum_assured: float = Field(30_000, gt=0, le=100_000)
    frequency: Literal["annual", "semiannual", "quarterly", "monthly"] = "monthly"
    cover_to_age: int = Field(120, ge=90, le=120)
    explain: bool = True


class RetirementRequest(BaseModel):
    current_age: int = Field(40, ge=18, le=74)
    retirement_age: int = Field(65, ge=45, le=75)
    end_age: int = Field(95, ge=75, le=110)
    current_savings: float = Field(500_000, ge=0)
    annual_contribution: float = Field(120_000, ge=0)
    contribution_escalation: float = Field(0.05, ge=0, le=0.2)
    expected_return: float = Field(0.10, ge=0, le=0.3)
    return_volatility: float = Field(0.12, ge=0, le=0.5)
    inflation: float = Field(0.05, ge=0, le=0.2)
    target_income: float = Field(300_000, ge=0, description="Desired retirement income per year, in today's money")
    n_sims: int = Field(10_000, ge=500, le=50_000)


class CreditRequest(BaseModel):
    # applicant / scorecard
    age: int = Field(35, ge=16, le=90)
    employment_type: Literal["permanent", "contract", "self_employed", "unemployed"] = "permanent"
    employment_months: int = Field(36, ge=0, le=600)
    existing_accounts: int = Field(2, ge=0, le=50)
    adverse_history: bool = False
    # affordability
    gross_monthly_income: float = Field(45_000, gt=0)
    net_monthly_income: float = Field(33_000, gt=0)
    monthly_living_expenses: float = Field(12_000, ge=0)
    existing_monthly_debt: float = Field(4_000, ge=0)
    # loan requested
    loan_amount: float = Field(150_000, gt=0)
    annual_rate: float = Field(0.18, ge=0, le=0.6)
    term_months: int = Field(48, ge=1, le=360)


def _strip_trace(payload: dict, explain: bool) -> dict:
    if not explain:
        payload = dict(payload)
        payload.pop("trace", None)
    return payload


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@router.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "basis-pricing-engine", "version": "0.1.0"}


@router.post("/price/life", tags=["pricing"])
def quote_life(req: LifeQuoteRequest) -> dict:
    """Price a level term life assurance (2015 VBT smoker-distinct tables)."""
    quote = price_life(
        issue_age=req.issue_age, sex=req.sex, smoker_status=req.smoker_status,
        sum_assured=req.sum_assured, term=req.term,
        underwriting_class=req.underwriting_class, frequency=req.frequency,
    )
    return _strip_trace(quote.__dict__, req.explain)


@router.post("/price/funeral", tags=["pricing"])
def quote_funeral(req: FuneralQuoteRequest) -> dict:
    """Price whole-of-life funeral cover (ELT No. 15 population tables)."""
    quote = price_funeral(
        issue_age=req.issue_age, sex=req.sex, sum_assured=req.sum_assured,
        frequency=req.frequency, cover_to_age=req.cover_to_age,
    )
    return _strip_trace(quote.__dict__, req.explain)


@router.post("/retirement/project", tags=["pricing"])
def retirement(req: RetirementRequest) -> dict:
    """Monte Carlo projection of a retirement plan: the fan of wealth over time,
    capital at retirement, and the probability the money lasts."""
    if req.retirement_age <= req.current_age or req.end_age < req.retirement_age:
        from fastapi import HTTPException
        raise HTTPException(422, "need current_age < retirement_age <= end_age")
    return project_retirement(**req.model_dump()).__dict__


@router.post("/credit/assess", tags=["pricing"])
def credit(req: CreditRequest) -> dict:
    """Assess a loan application: affordability (NCA-style), a points scorecard
    with probability of default, and an approve / refer / decline decision with
    the full reason trail."""
    return asdict(assess_credit(**req.model_dump()))


@router.get("/credit/policy", tags=["admin"])
def credit_policy() -> dict:
    """The credit rule book: scorecard calibration, points tables, affordability
    limits and grade bands. Everything the decision depends on, auditable."""
    return DEFAULT_POLICY.as_dict()


class OptionRequest(BaseModel):
    S: float = Field(100, gt=0, description="Spot price")
    K: float = Field(100, gt=0, description="Strike")
    T: float = Field(1.0, gt=0, le=30, description="Time to expiry in years")
    r: float = Field(0.05, ge=-0.1, le=0.5, description="Risk-free rate")
    sigma: float = Field(0.20, gt=0, le=3, description="Volatility")
    q: float = Field(0.0, ge=0, le=0.5, description="Dividend yield")
    option_type: Literal["call", "put"] = "call"
    n_sims: int = Field(100_000, ge=1000, le=1_000_000)


class ImpliedVolRequest(BaseModel):
    price: float = Field(..., gt=0)
    S: float = Field(100, gt=0)
    K: float = Field(100, gt=0)
    T: float = Field(1.0, gt=0, le=30)
    r: float = Field(0.05, ge=-0.1, le=0.5)
    q: float = Field(0.0, ge=0, le=0.5)
    option_type: Literal["call", "put"] = "call"


class ExperienceRequest(BaseModel):
    by: list[Literal["age_band", "sex", "smoker_status"]] = Field(
        default_factory=lambda: ["smoker_status"],
        description="Segmentation dimensions for the A/E analysis",
    )


@router.post("/options/price", tags=["pricing"])
def options_price(req: OptionRequest) -> dict:
    """Price a European option: Black-Scholes price, Greeks, a Monte Carlo
    cross-check, the put-call parity residual and a value-versus-spot curve."""
    return asdict(price_option(**req.model_dump()))


@router.post("/options/implied-vol", tags=["pricing"])
def options_implied_vol(req: ImpliedVolRequest) -> dict:
    """Back out the implied volatility that reproduces a given option price."""
    iv = implied_volatility(**req.model_dump())
    return {"implied_volatility": iv, "inputs": req.model_dump()}


@router.post("/experience/analyse", tags=["pricing"])
def experience(req: ExperienceRequest) -> dict:
    """Actual-versus-expected mortality analysis with credibility, on the
    bundled synthetic experience dataset, segmented by the chosen dimensions."""
    df = load_experience_dataset().copy()
    by = list(req.by)
    if "age_band" in by:
        df["age_band"] = (df["age"] // 10 * 10).astype(int).astype(str) + "s"
    result = analyse_experience(df, by=by)
    return asdict(result)


@router.get("/experience/dataset", tags=["admin"])
def experience_dataset() -> dict:
    """Summary of the bundled experience dataset."""
    df = load_experience_dataset()
    return {
        "cells": len(df),
        "life_years": round(float(df["exposure"].sum()), 0),
        "deaths": int(df["actual_deaths"].sum()),
        "ages": [int(df["age"].min()), int(df["age"].max())],
        "dimensions": ["age", "sex", "smoker_status"],
        "expected_basis": "2015 VBT ultimate",
    }


@router.get("/assumptions", tags=["admin"])
def assumptions() -> dict:
    """The full pricing basis: interest rate, expense loadings and every rating
    factor.  This is the source of truth the admin view renders."""
    return DEFAULT_BASIS.as_dict()


@router.get("/tables", tags=["admin"])
def tables() -> dict:
    """Metadata and sample rates from the underlying mortality tables."""
    out = {"life": [], "funeral": []}
    for sex in ("male", "female"):
        for smoker in ("nonsmoker", "smoker"):
            t = load_vbt(sex, smoker)
            out["life"].append({
                "sex": sex, "smoker_status": smoker, "name": t.name,
                "select_period": t.select_period,
                "sample_q": {str(a): round(t.q(a, 1), 6) for a in (30, 40, 50, 60, 70)},
            })
        e = load_elt(sex)
        out["funeral"].append({
            "sex": sex, "name": e.name, "min_age": e.min_age, "max_age": e.max_age,
            "sample_q": {str(a): round(e.qx(a), 6) for a in (30, 50, 70, 90)},
        })
    return out


app.include_router(router)
