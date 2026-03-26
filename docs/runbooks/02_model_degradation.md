# Runbook 02  Model Degradation
**Owner:** MLOps Engineer
**Last Tested:** Day 19 (incident simulation) + Day 23 (chaos test)
**Recovery Time Target:** < 5 minutes

---

## Symptoms
- Grafana: RMSE > 1.5x baseline for any market
- Slack alert: "Model performance degraded: <market> RMSE = <value>"
- Prediction distribution shifted (visible in Grafana predictions panel)
- Store managers reporting unrealistic price recommendations

---

## Diagnosis

### Step 1  Check model performance log
```sql
-- Run in Databricks
SELECT market, rmse, mae, mape, run_date
FROM model_performance_log
WHERE run_date >= CURRENT_DATE() - INTERVAL 7 DAYS
ORDER BY run_date DESC, market
```

### Step 2  Check current champion version
```python
from mlflow.tracking import MlflowClient
client = MlflowClient()
for market in ["est", "cst", "mst", "pst"]:
    model = client.get_model_version_by_alias(f"fuel_pricing_{market}", "champion")
    print(f"{market}: v{model.version} | run_id: {model.run_id}")
```

### Step 3  Check API predictions
```bash
# Sample prediction  does it look reasonable?
curl -X POST https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/predict \
  -H "X-API-Key: fuelops-api-key-dev-12345" \
  -H "Content-Type: application/json" \
  -d '{"cost":3.20,"competitor_price":3.35,"volume":500,"market":"EST","fuel_type":"regular","store_id":"1001"}'
# Expected: predicted_price between 3.50-3.80
# If < 1.0 or > 10.0  model is broken
```

### Step 4  Check drift scores
```sql
SELECT market, psi_score, drift_status, check_date
FROM drift_detection_log
ORDER BY check_date DESC
LIMIT 8
```

---

## Resolution

### Case A: Recent bad model deployed  rollback
```python
# scripts/rollback/model_rollback.py
from mlflow.tracking import MlflowClient
client = MlflowClient()

for market in ["est", "cst", "mst", "pst"]:
    current = client.get_model_version_by_alias(f"fuel_pricing_{market}", "champion")
    prev_version = str(int(current.version) - 1)
    client.set_registered_model_alias(f"fuel_pricing_{market}", "champion", prev_version)
    print(f"{market}: rolled back v{current.version} -> v{prev_version}")
```

### Case B: Model stale  data drift detected  retrain
```bash
# Trigger retraining DAG manually
docker exec -u airflow <airflow_container_id> \
  airflow dags trigger fuelops_daily_pipeline \
  --conf '{"force_retrain": "true"}'
```

### Case C: Specific market only  targeted rollback
```python
from mlflow.tracking import MlflowClient
client = MlflowClient()
market = "est"  # Only EST degraded
current = client.get_model_version_by_alias(f"fuel_pricing_{market}", "champion")
client.set_registered_model_alias(f"fuel_pricing_{market}", "champion", str(int(current.version) - 1))
print(f"Rolled back {market} only")
```

---

## Escalation
- **5 min:** Rollback executed  verify RMSE returns to baseline
- **15 min:** RMSE still elevated  force retrain with last 90 days clean data
- **1 hour:** Still degraded  escalate to data science team for investigation

---

## Prevention
- Champion/challenger evaluation before every promotion
- RMSE alert threshold: 1.5x baseline (currently configured in Grafana)
- Drift detection runs daily before scoring (check_drift Airflow task)