# Runbook 05  Emergency Rollback (All 3 Levels)
**Owner:** MLOps Engineer
**Last Tested:** Day 18 (rollback toolkit) + Day 23 (chaos test)
**Recovery Time Target:** < 10 minutes total

---

## When to Use This Runbook
Use when multiple systems are failing simultaneously or when you need to
roll back everything quickly without time to diagnose root cause.

Decision tree:
```
Is the API returning errors?
  YES  Execute Level 1 (API rollback) first
  
Are predictions unrealistic (< $1 or > $20)?
  YES  Execute Level 2 (model rollback)
  
Is Silver/Gold data corrupted or missing rows?
  YES  Execute Level 3 (data rollback)
```

---

## Level 1  API Rollback (< 2 minutes)
```bash
# Step 1: List all revisions
az containerapp revision list \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --output table

# Step 2: Identify last known good revision
# Look for the revision before the current active one

# Step 3: Activate previous revision
az containerapp revision activate \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --revision <previous_revision_name>

# Step 4: Verify (wait 20 seconds)
sleep 20
curl https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/health \
  -H "X-API-Key: fuelops-api-key-dev-12345"
# Expected: {"status": "ok"}
```

---

## Level 2  Model Rollback (< 1 minute)
```python
# scripts/rollback/model_rollback.py
from mlflow.tracking import MlflowClient

client = MlflowClient()
markets = ["est", "cst", "mst", "pst"]

print("Current champions:")
for market in markets:
    current = client.get_model_version_by_alias(f"fuel_pricing_{market}", "champion")
    print(f"  {market}: v{current.version}")

print("\nRolling back all markets...")
for market in markets:
    current = client.get_model_version_by_alias(f"fuel_pricing_{market}", "champion")
    prev = str(int(current.version) - 1)
    client.set_registered_model_alias(f"fuel_pricing_{market}", "champion", prev)
    print(f"  {market}: v{current.version} -> v{prev}")

print("\nVerify by calling /predict and checking predicted_price is realistic (3.50-4.50)")
```

---

## Level 3  Data Rollback (< 5 minutes)
```sql
-- Run in Databricks notebook

-- Step 1: Check Silver table history
DESCRIBE HISTORY silver_fuel_prices LIMIT 10;

-- Step 2: Identify last clean version
-- Look for version before today's pipeline run

-- Step 3: Restore Silver table
RESTORE TABLE silver_fuel_prices TO VERSION AS OF <version_number>;

-- Step 4: Verify row count matches expected
SELECT COUNT(*) FROM silver_fuel_prices;
-- Expected: ~540,000 rows

-- Step 5: Also restore Gold if needed
DESCRIBE HISTORY gold_fuel_features LIMIT 5;
RESTORE TABLE gold_fuel_features TO VERSION AS OF <version_number>;
```

---

## Full System Rollback (all 3 levels sequentially)
```bash
# STEP 1: API rollback (immediate  stops bad predictions reaching users)
az containerapp revision activate \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --revision <previous_revision>

# STEP 2: Model rollback (run in Python)
python scripts/rollback/model_rollback.py

# STEP 3: Data rollback (run in Databricks)
# RESTORE TABLE silver_fuel_prices TO VERSION AS OF <n>

# STEP 4: Verify all 3 levels
curl https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/health \
  -H "X-API-Key: fuelops-api-key-dev-12345"

curl -X POST \
  https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/predict \
  -H "X-API-Key: fuelops-api-key-dev-12345" \
  -H "Content-Type: application/json" \
  -d '{"cost":3.20,"competitor_price":3.35,"volume":500,"market":"EST","fuel_type":"regular","store_id":"1001"}'
# Check: predicted_price is between 3.50-4.50
```

---

## Post-Rollback Checklist
- [ ] API health endpoint returns ok
- [ ] /predict returns realistic price (3.50-4.50 for regular, EST, cost=3.20)
- [ ] Grafana alerts resolved (no more firing)
- [ ] Silver row count matches pre-incident count
- [ ] MLflow champion alias points to previous version
- [ ] Write incident report (use docs/incident_report template)

---

## Escalation
- **10 min:** All 3 rollbacks complete  system stable
- **15 min:** System still unstable  freeze all deployments, escalate to senior engineer
- **30 min:** Major outage  activate incident bridge, notify stakeholders

---

## Incident Report Template
After every emergency rollback, document in docs/:
```markdown
## Incident Report  <date>
**Severity:** P1 / P2 / P3
**Duration:** <start> to <end>
**Impact:** <what was affected>

### Timeline
- HH:MM  Alert fired
- HH:MM  Investigation started
- HH:MM  Root cause identified
- HH:MM  Rollback executed
- HH:MM  System restored

### Root Cause
<what caused the issue>

### Resolution
<what was done to fix it>

### Prevention
<what will prevent recurrence>
```