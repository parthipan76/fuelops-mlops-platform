# Runbook 04  API Outage
**Owner:** MLOps Engineer
**Last Tested:** Day 23 (chaos test  missing secret scenario)
**Recovery Time Target:** < 5 minutes

---

## Symptoms
- Grafana: API Status panel shows DOWN (red)
- Grafana: "API Down" alert firing to Slack
- HTTP requests to /health return 5xx or timeout
- Store managers unable to get price recommendations

---

## Diagnosis

### Step 1  Check health endpoint
```bash
curl -f https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/health \
  -H "X-API-Key: fuelops-api-key-dev-12345"
# Expected: {"status": "ok", ...}
# If timeout or 5xx -> container issue
```

### Step 2  Check Container App status
```bash
az containerapp show \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --query "properties.runningStatus" -o tsv
# Expected: Running
```

### Step 3  Check active revision
```bash
az containerapp revision list \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --output table
# Look for active=True revision
```

### Step 4  Check container logs
```bash
az containerapp logs show \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --tail 50
# Look for: startup errors, missing env vars, import errors
```

### Step 5  Check Key Vault secrets
```bash
az keyvault secret show \
  --vault-name kv-fuelops-dev \
  --name dummy-api-key \
  --query "name" -o tsv
# If SecretNotFound -> secret was deleted
```

---

## Resolution

### Case A: Container crashed  rollback to previous revision
```bash
# List revisions
az containerapp revision list \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --output table

# Activate previous good revision
az containerapp revision activate \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --revision <previous_revision_name>

# Verify
sleep 20
curl https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/health \
  -H "X-API-Key: fuelops-api-key-dev-12345"
```

### Case B: Missing Key Vault secret
```bash
# Restore soft-deleted secret
az keyvault secret recover \
  --vault-name kv-fuelops-dev \
  --name dummy-api-key

# Force new revision to pick up secret
az containerapp update \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --set-env-vars "RESTART=$(date +%s)"
```

### Case C: Container App scaled to 0 (cold start)
```bash
# Send a warm-up request  first request wakes it up
curl -X POST \
  https://fuelops-api-dev.delightfulhill-d5055901.eastus.azurecontainerapps.io/predict \
  -H "X-API-Key: fuelops-api-key-dev-12345" \
  -H "Content-Type: application/json" \
  -d '{"cost":3.20,"competitor_price":3.35,"volume":500,"market":"EST","fuel_type":"regular","store_id":"1001"}'
# First request may timeout (cold start)  retry immediately
```

### Case D: Bad image deployed via CI/CD
```bash
# Identify the bad revision
az containerapp revision list \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --output table

# Rollback to last known good SHA
az containerapp revision activate \
  --name fuelops-api-dev \
  --resource-group rg-fuelops-dev \
  --revision fuelops-api-dev--<good_revision_number>
```

---

## Escalation
- **2 min:** Health check failing  start rollback immediately
- **5 min:** Rollback complete  verify health endpoint
- **10 min:** Still down  escalate to Azure support + notify stakeholders
- **Fallback:** Use batch predictions from fuel_price_predictions Delta table

---

## Prevention
- Minimum replicas: set to 1 during business hours to avoid cold starts
- Health check probe configured on Container App
- Grafana "API Down" alert fires after 1 minute of no scrape data
- Manual production gate prevents untested images reaching prod