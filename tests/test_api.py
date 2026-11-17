"""API-level tests for the FastAPI pricing service."""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_price_life_returns_premium_and_trace():
    r = client.post("/api/price/life", json={
        "issue_age": 40, "sex": "male", "smoker_status": "nonsmoker",
        "sum_assured": 1_000_000, "term": 20, "frequency": "monthly", "explain": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["premium"] > 0
    assert len(body["steps"]) == 8
    assert "benefits" in body["trace"] and "annuity" in body["trace"]


def test_explain_false_strips_trace():
    r = client.post("/api/price/life", json={"issue_age": 30, "explain": False})
    assert "trace" not in r.json()


def test_smoker_dearer_via_api():
    def prem(smoker):
        return client.post("/api/price/life", json={
            "issue_age": 45, "smoker_status": smoker, "sum_assured": 500_000, "term": 15,
        }).json()["premium"]
    assert prem("smoker") > prem("nonsmoker")


def test_funeral_endpoint():
    r = client.post("/api/price/funeral", json={"issue_age": 65, "sex": "female", "sum_assured": 30_000})
    assert r.status_code == 200 and r.json()["product"] == "funeral_wol"


def test_validation_rejects_out_of_range():
    assert client.post("/api/price/life", json={"issue_age": 5}).status_code == 422
    assert client.post("/api/price/life", json={"sum_assured": -10}).status_code == 422


def test_retirement_projection_endpoint():
    r = client.post("/api/retirement/project", json={
        "current_age": 40, "retirement_age": 65, "current_savings": 500_000,
        "annual_contribution": 120_000, "target_income": 300_000, "n_sims": 1000,
    })
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["success_probability"] <= 1.0
    assert len(body["ages"]) == len(body["percentiles"]["p50"])
    assert client.post("/api/retirement/project",
                       json={"current_age": 70, "retirement_age": 65}).status_code == 422


def test_credit_assess_and_policy_endpoints():
    r = client.post("/api/credit/assess", json={
        "age": 40, "employment_type": "permanent", "employment_months": 120,
        "existing_accounts": 2, "adverse_history": False,
        "gross_monthly_income": 45_000, "net_monthly_income": 33_000,
        "monthly_living_expenses": 12_000, "existing_monthly_debt": 4_000,
        "loan_amount": 150_000, "annual_rate": 0.18, "term_months": 48,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] in {"approve", "refer", "decline"}
    assert body["scorecard"]["grade"] in {"A", "B", "C", "D", "E"}
    assert body["affordability"]["installment"] > 0
    assert client.post("/api/credit/assess", json={"age": 10}).status_code == 422
    p = client.get("/api/credit/policy").json()
    assert p["scorecard_calibration"]["pdo"] == 30


def test_experience_endpoints():
    r = client.post("/api/experience/analyse", json={"by": ["sex", "smoker_status"]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["segments"]) == 4
    assert body["overall"]["ae_pct"] > 0
    assert all("credible_ae_pct" in s for s in body["segments"])
    d = client.get("/api/experience/dataset").json()
    assert d["cells"] > 0 and d["deaths"] > 0


def test_assumptions_and_tables_endpoints():
    a = client.get("/api/assumptions").json()
    assert a["interest_rate"] == 0.09
    assert "standard" in a["rating"]["underwriting_class"]
    t = client.get("/api/tables").json()
    assert len(t["life"]) == 4 and len(t["funeral"]) == 2
