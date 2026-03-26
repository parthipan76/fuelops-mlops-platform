# FuelOps Rollback Toolkit

3-level rollback system. Total recovery time: < 10 minutes.

## Level 1  API Rollback (< 2 min)
Trigger: Bad container image deployed, API returning 500s

    az login --service-principal -u $CLIENT_ID -p $SECRET --tenant $TENANT_ID
    bash scripts/rollback/api_rollback.sh fuelops-api-dev rg-fuelops-dev

## Level 2  Model Rollback (< 1 min)
Trigger: RMSE spiked, predictions are wrong, Grafana alert fired

    python scripts/rollback/model_rollback.py \
      --model fuel_pricing_est \
      --host https://dbc-885f8690-54bc.cloud.databricks.com \
      --token $DATABRICKS_TOKEN

    # Then restart Container App to reload new champion:
    az containerapp revision restart --name fuelops-api-dev --resource-group rg-fuelops-dev

## Level 3  Data Rollback (< 5 min)
Trigger: Corrupted Delta table, wrong data in silver/gold layer

    1. Open Databricks notebook
    2. Run: DESCRIBE HISTORY silver_fuel_prices
    3. Find last good version number
    4. Run: RESTORE TABLE silver_fuel_prices TO VERSION AS OF <n>
    5. Re-trigger pipeline from silver -> gold -> score

## Decision Tree
API errors (500s / timeout)  -> Level 1 first
Wrong predictions (RMSE high) -> Level 2 first
Bad data in tables            -> Level 3 first
All of the above              -> Level 3 -> Level 2 -> Level 1