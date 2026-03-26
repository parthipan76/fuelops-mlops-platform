# Runbook 01  Pipeline Failure
**Owner:** MLOps Engineer
**Last Tested:** Day 23 (2026-04-07)
**Recovery Time Target:** < 30 minutes

---

## Symptoms
- Airflow DAG marked as Failed in UI (http://localhost:8080)
- Slack alert: "FuelOps pipeline failed at task: <task_name>"
- fuel_price_predictions table not updated after 7AM UTC
- Grafana: prediction count flatlines after expected run time

---

## Diagnosis

### Step 1  Identify failed task
```bash
# Check Airflow UI
http://localhost:8080/dags/fuelops_daily_pipeline/grid

# Or via CLI
docker exec -u airflow <airflow_container_id> airflow tasks states-for-dag-run fuelops_daily_pipeline <run_id>
```

### Step 2  Check task logs
```bash
# Get logs for specific task
docker exec -u airflow <airflow_container_id> airflow tasks logs fuelops_daily_pipeline <task_id> <execution_date>
```

### Step 3  Check Databricks job status
```bash
# List recent job runs
curl -H "Authorization: Bearer <db_token>" \
  https://dbc-885f8690-54bc.cloud.databricks.com/api/2.1/jobs/runs/list?job_id=<job_id>&limit=5
```

### Step 4  Check data freshness
```sql
-- Run in Databricks
SELECT MAX(_ingested_at), COUNT(*) 
FROM bronze_fuel_prices 
WHERE DATE(_ingested_at) = CURRENT_DATE()
```

---

## Resolution

### Case A: Databricks job failed
```bash
# Re-trigger the specific job manually
curl -X POST -H "Authorization: Bearer <db_token>" \
  https://dbc-885f8690-54bc.cloud.databricks.com/api/2.1/jobs/run-now \
  -d '{"job_id": <job_id>}'

# Then re-trigger downstream Airflow tasks
docker exec -u airflow <airflow_container_id> \
  airflow tasks clear fuelops_daily_pipeline -t process_bronze --yes
```

### Case B: Data quality check failed (bad data)
```sql
-- Check quarantine table
SELECT quarantine_reason, COUNT(*) 
FROM quarantine_fuel_prices 
WHERE DATE(_ingested_at) = CURRENT_DATE()
GROUP BY quarantine_reason

-- If acceptable, force-pass by clearing the task
docker exec -u airflow <airflow_container_id> \
  airflow tasks clear fuelops_daily_pipeline -t data_quality_check --yes
```

### Case C: Airflow scheduler down
```bash
# Restart scheduler
docker-compose restart airflow-scheduler

# Verify
docker ps | grep airflow-scheduler
```

### Case D: Approval gate timed out
```bash
# Manually approve
docker exec -u airflow <airflow_container_id> \
  airflow variables set "approve_<run_id>" "approved"
```

---

## Escalation
- **30 min:** No resolution  notify data engineering team
- **2 hours:** Pipeline still failed  use previous day predictions (already in Delta table)
- **Next day:** Root cause analysis required, document in incident report

---

## Prevention
- Set Airflow SLA: `sla=timedelta(hours=2)` on score_predictions task
- Monitor data freshness panel in Grafana
- Ensure Databricks cluster auto-terminates and restarts cleanly