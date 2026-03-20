# Purpose: FuelOps inference API  serves fuel price predictions via REST
# Inputs:  POST /predict -> { cost, competitor_price, volume, market, fuel_type, store_id }
# Outputs: { predicted_price, confidence_interval, model_version }
# Author:  Parthipan S

import logging
import os
import time

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from prometheus_client import Counter, Histogram, Info, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FuelOps Inference API", version="1.0.0")

# --- Prometheus metrics ---
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency in seconds", ["endpoint"])
PREDICTION_COUNT = Counter("prediction_count_total", "Total number of predictions served", ["market", "fuel_type"])
ERROR_COUNT = Counter("error_count_total", "Total number of errors", ["type"])
MODEL_INFO = Info("model_info", "Current model information")

# --- Auth ---
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY = os.getenv("API_KEY", "fuelops-api-key-dev-12345")


def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != API_KEY:
        ERROR_COUNT.labels(type="auth_error").inc()
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# --- Model loading ---
model = None
model_version = "mock-v1.0"


@app.on_event("startup")
def load_model():
    global model, model_version
    mlflow_uri = os.getenv("MLFLOW_MODEL_URI", "")
    if mlflow_uri:
        try:
            import mlflow

            model = mlflow.pyfunc.load_model(mlflow_uri)
            model_version = mlflow_uri
            logger.info(f"Loaded MLflow model: {mlflow_uri}")
        except Exception as e:
            logger.warning(f"MLflow model not available ({e}), using mock model")
            model = None
    else:
        logger.info("No MLFLOW_MODEL_URI set  using mock model for local dev")
    MODEL_INFO.info({"version": model_version, "type": "mlflow" if model else "mock"})


# --- Request/Response schemas ---
class PredictRequest(BaseModel):
    cost: float
    competitor_price: float
    volume: float
    market: str
    fuel_type: str
    store_id: str

    def to_dataframe(self):
        return pd.DataFrame(
            [
                {
                    "cost": self.cost,
                    "competitor_price": self.competitor_price,
                    "volume": self.volume,
                    "market": self.market,
                    "fuel_type": self.fuel_type,
                    "store_id": self.store_id,
                }
            ]
        )


class PredictResponse(BaseModel):
    predicted_price: float
    confidence_interval: dict
    model_version: str
    market: str
    fuel_type: str


# --- Mock prediction ---
def mock_predict(request: PredictRequest) -> float:
    base = request.cost * 1.15
    competitor_adjustment = (request.competitor_price - base) * 0.3
    market_multiplier = {"EST": 1.02, "CST": 1.00, "MST": 0.98, "PST": 1.03}.get(request.market, 1.0)
    fuel_multiplier = {"regular": 1.0, "premium": 1.18, "diesel": 1.08}.get(request.fuel_type, 1.0)
    return round((base + competitor_adjustment) * market_multiplier * fuel_multiplier, 4)


# --- Endpoints ---
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_version": model_version,
        "model_type": "mlflow" if model else "mock",
        "uptime_check": "pass",
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, api_key: str = Depends(verify_api_key)):
    start = time.time()
    try:
        if model:
            result = model.predict(request.to_dataframe())
            predicted_price = float(result[0])
        else:
            predicted_price = mock_predict(request)

        margin = predicted_price * 0.02
        PREDICTION_COUNT.labels(market=request.market, fuel_type=request.fuel_type).inc()
        logger.info(f"Prediction: store={request.store_id} market={request.market} price={predicted_price}")

        return PredictResponse(
            predicted_price=predicted_price,
            confidence_interval={
                "lower": round(predicted_price - margin, 4),
                "upper": round(predicted_price + margin, 4),
            },
            model_version=model_version,
            market=request.market,
            fuel_type=request.fuel_type,
        )
    except Exception as e:
        ERROR_COUNT.labels(type=type(e).__name__).inc()
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.labels(endpoint="predict").observe(time.time() - start)

# this_is_a_very_long_comment_that_exceeds_the_120_character_limit_set_in_our_flake8_configuration_and_should_cause_a_failure_in_ci
