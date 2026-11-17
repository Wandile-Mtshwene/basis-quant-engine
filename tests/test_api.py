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


def test_assumptions_and_tables_endpoints():
    a = client.get("/api/assumptions").json()
    assert a["interest_rate"] == 0.09
    assert "standard" in a["rating"]["underwriting_class"]
    t = client.get("/api/tables").json()
    assert len(t["life"]) == 4 and len(t["funeral"]) == 2
