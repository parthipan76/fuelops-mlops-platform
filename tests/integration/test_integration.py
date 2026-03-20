# Purpose: Integration tests  validate API schema and endpoint contracts
# Runs on: merge to main only (not every push)

from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/inference'))

from main import app

client = TestClient(app)
HEADERS = {"X-API-Key": "fuelops-api-key-dev-12345"}


def test_predict_response_schema():
    payload = {
        "cost": 3.50,
        "competitor_price": 3.75,
        "volume": 1000.0,
        "market": "EST",
        "fuel_type": "regular",
        "store_id": "store_001"
    }
    response = client.post("/predict", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    # Validate all required fields present
    assert "predicted_price" in data
    assert "confidence_interval" in data
    assert "model_version" in data
    assert "market" in data
    assert "fuel_type" in data
    # Validate types
    assert isinstance(data["predicted_price"], float)
    assert isinstance(data["confidence_interval"]["lower"], float)
    assert isinstance(data["confidence_interval"]["upper"], float)


def test_all_markets():
    for market in ["EST", "CST", "MST", "PST"]:
        payload = {
            "cost": 3.50, "competitor_price": 3.75,
            "volume": 1000.0, "market": market,
            "fuel_type": "regular", "store_id": "store_001"
        }
        response = client.post("/predict", json=payload, headers=HEADERS)
        assert response.status_code == 200, f"Failed for market {market}"


def test_all_fuel_types():
    for fuel_type in ["regular", "premium", "diesel"]:
        payload = {
            "cost": 3.50, "competitor_price": 3.75,
            "volume": 1000.0, "market": "EST",
            "fuel_type": fuel_type, "store_id": "store_001"
        }
        response = client.post("/predict", json=payload, headers=HEADERS)
        assert response.status_code == 200, f"Failed for fuel_type {fuel_type}"


def test_health_schema():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model_version" in data
    assert "model_type" in data


def test_metrics_contains_required_metrics():
    # Make a prediction first so counters are non-zero
    payload = {
        "cost": 3.50, "competitor_price": 3.75,
        "volume": 1000.0, "market": "EST",
        "fuel_type": "regular", "store_id": "store_001"
    }
    client.post("/predict", json=payload, headers=HEADERS)

    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.content
    assert b"request_latency_seconds" in content
    assert b"prediction_count_total" in content
    assert b"model_info_info" in content
