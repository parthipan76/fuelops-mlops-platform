# Purpose: Unit tests for FuelOps inference API
# Tests:   health endpoint, predict endpoint, mock model logic, auth

from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/inference'))

from main import app, mock_predict, PredictRequest

client = TestClient(app)
HEADERS = {"X-API-Key": "fuelops-api-key-dev-12345"}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model_version" in data

def test_predict_success():
    payload = {
        "cost": 3.50,
        "competitor_price": 3.75,
        "market": "EST",
        "fuel_type": "regular",
        "volume": 1000.0,
        "store_id": "store_001"
    }
    response = client.post("/predict", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_price" in data
    assert "confidence_interval" in data
    assert data["confidence_interval"]["lower"] < data["predicted_price"]
    assert data["confidence_interval"]["upper"] > data["predicted_price"]
    assert data["market"] == "EST"

def test_predict_missing_auth():
    payload = {
        "cost": 3.50, "competitor_price": 3.75,
        "market": "EST", "fuel_type": "regular",
        "volume": 1000.0, "store_id": "store_001"
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 403

def test_predict_wrong_key():
    payload = {
        "cost": 3.50, "competitor_price": 3.75,
        "market": "EST", "fuel_type": "regular",
        "volume": 1000.0, "store_id": "store_001"
    }
    response = client.post("/predict", json=payload, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"prediction_count_total" in response.content

def test_mock_predict_logic():
    req = PredictRequest(
        cost=3.50, competitor_price=3.75,
        market="EST", fuel_type="regular",
        volume=1000.0, store_id="store_001"
    )
    price = mock_predict(req)
    assert price > 0
    assert 3.0 < price < 6.0  # sanity bounds for fuel price


def test_intentional_failure():
    assert 1 == 2, 'intentional failure for CI/CD practice'
