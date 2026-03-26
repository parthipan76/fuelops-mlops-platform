# data_rollback.sql
# Purpose: Roll back Delta Lake tables using time travel
# Usage:   Run in Databricks notebook or paste into SQL editor
# Author:  Parthipan S

-- =============================================================================
-- FuelOps Data Rollback Runbook
-- =============================================================================
-- Step 1: Check current table version and history
DESCRIBE HISTORY silver_fuel_prices;

-- Step 2: Find the version BEFORE the corruption
-- Look for the last MERGE operation before the bad write
-- Note the version number (e.g., version 5)

-- Step 3: Preview what the rollback will restore (verify row counts)
SELECT COUNT(*) as row_count, MAX(date) as latest_date
FROM silver_fuel_prices
VERSION AS OF 5;  -- replace 5 with your target version

-- Step 4: Execute the rollback (RESTORE to previous version)
RESTORE TABLE silver_fuel_prices TO VERSION AS OF 5;

-- Step 5: Verify restore was successful
SELECT COUNT(*) as restored_rows FROM silver_fuel_prices;
DESCRIBE HISTORY silver_fuel_prices LIMIT 3;

-- =============================================================================
-- Same pattern for other tables
-- =============================================================================

-- Gold layer rollback (if feature engineering was corrupted)
-- DESCRIBE HISTORY gold_fuel_features;
-- RESTORE TABLE gold_fuel_features TO VERSION AS OF <version>;

-- Bronze layer rollback (if raw ingestion was bad)
-- DESCRIBE HISTORY bronze_fuel_prices;
-- RESTORE TABLE bronze_fuel_prices TO VERSION AS OF <version>;

-- =============================================================================
-- Time-based rollback (alternative to version-based)
-- =============================================================================
-- RESTORE TABLE silver_fuel_prices
-- TO TIMESTAMP AS OF '2026-03-22 06:00:00';

-- =============================================================================
-- After restore: re-run downstream pipeline
-- =============================================================================
-- 1. Verify silver table health
SELECT market, COUNT(*) as rows
FROM silver_fuel_prices
GROUP BY market
ORDER BY market;

-- 2. Check no quarantine records exist from bad run
SELECT COUNT(*) FROM quarantine_fuel_prices
WHERE ingestion_date = CURRENT_DATE();

-- 3. Re-trigger gold layer rebuild
-- (run Module 2 notebook: silver -> gold feature engineering)