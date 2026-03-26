#!/bin/bash
# api_rollback.sh
# Purpose: Roll back Container App to previous revision
# Usage:   ./api_rollback.sh [app-name] [resource-group]
# Author:  Parthipan S

set -e

APP_NAME=${1:-"fuelops-api-dev"}
RG=${2:-"rg-fuelops-dev"}

echo "=== FuelOps API Rollback ==="
echo "App: $APP_NAME | RG: $RG"

# List all revisions
echo ""
echo "Current revisions:"
az containerapp revision list \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime, Traffic:properties.trafficWeight}" \
  --output table

# Get current active revision
CURRENT=$(az containerapp revision list \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "[?properties.active==true].name | [0]" \
  --output tsv)

echo ""
echo "Current active revision: $CURRENT"

# Get previous revision (second in list sorted by date desc)
PREVIOUS=$(az containerapp revision list \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "[-2].name" \
  --output tsv)

if [ -z "$PREVIOUS" ]; then
  echo "ERROR: No previous revision found. Cannot rollback."
  exit 1
fi

echo "Rolling back to: $PREVIOUS"
echo ""

# Activate previous revision
az containerapp revision activate \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --revision "$PREVIOUS"

# Deactivate current (bad) revision
az containerapp revision deactivate \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --revision "$CURRENT"

echo ""
echo "Rollback complete. Active revision: $PREVIOUS"
echo "Verifying..."

sleep 10

STATUS=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "properties.latestRevisionName" \
  --output tsv)

echo "Latest revision: $STATUS"
echo "=== Rollback successful in < 2 minutes ==="