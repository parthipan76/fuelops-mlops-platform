# Runbook 03  Data Drift Detected
**Owner:** MLOps Engineer
**Last Tested:** Day 20 (drift detection implementation)
**Recovery Time Target:** < 2 hours (investigation) + retrain if needed

---

## Symptoms
- Slack alert: "DRIFT ALERT: PSI > 0.2 for feature <name> in market <market>"
- Airflow DAG paused at await_approval  Slack message shows HIGH drift status
- Model predictions gradually shifting over days
- PSI score > 0.2 in drift_detection_log

---

## Diagnosis

### Step 1  Check drift report
```bash
# Latest drift report
cat docs/drift_report_$(date +%Y-%m-%d).json

# Or check Delta table
```
```sql
SELECT market, feature_name, psi_score, drift_status, check_date
FROM drift_detection_log
WHERE check_date = CURRENT_DATE()
ORDER BY psi_score DESC
```

### Step 2  Run drift detection manually
```bash
python src/monitoring/drift_detection.py --drift none
# Output shows per-feature PSI scores
```

### Step 3  Identify which features drifted
```python
# PSI interpretation:
# < 0.1  = STABLE (no action)
# 0.1-0.2 = WARNING (monitor closely)
# > 0.2  = ALERT (consider retraining)
```

### Step 4  Check data source
```sql
-- Is upstream data changing?
SELECT DATE(date) as day, AVG(cost) as avg_cost, AVG(competitor_price) as avg_comp
FROM bronze_fuel_prices
WHERE date >= CURRENT_DATE() - INTERVAL 14 DAYS
GROUP BY day
ORDER BY day DESC
```

---

## Resolution

### Case A: PSI 0.1-0.2 (WARNING)  monitor
```bash
# No immediate action. Set reminder to check tomorrow.
# Update drift log comment
echo "WARNING drift detected $(date). Monitoring." >> docs/drift_notes.txt
```

### Case B: PSI > 0.2 (ALERT)  retrain challenger
```bash
# Approve Airflow pipeline to proceed with retrain
docker exec -u airflow <airflow_container_id> \
  airflow variables set "approve_<run_id>" "approved"

# This triggers: train_models -> evaluate_models -> await_approval -> score
```

### Case C: Sudden spike  bad data ingested
```sql
-- Check for anomalies in today's bronze data
SELECT 
  DATE(date) as day,
  MIN(cost) as min_cost,
  MAX(cost) as max_cost,
  COUNT(*) as row_count
FROM bronze_fuel_prices
WHERE date >= CURRENT_DATE() - INTERVAL 3 DAYS
GROUP BY day
ORDER BY day DESC

-- If anomaly found, restore bronze to yesterday
RESTORE TABLE bronze_fuel_prices TO VERSION AS OF <yesterday_version>
```

---

## Escalation
- **PSI > 0.2 for 3+ consecutive days:** Mandatory retrain
- **PSI > 0.5:** Data source investigation required  notify data engineering
- **All markets drifting simultaneously:** Likely upstream data issue, not model issue

---

## Prevention
- Daily drift check as first task in Airflow pipeline
- Baseline updated every 90 days with fresh training data
- Alert threshold: PSI > 0.2 triggers Slack notification automatically