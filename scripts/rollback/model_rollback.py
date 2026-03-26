# model_rollback.py
# Purpose: Roll back MLflow champion alias to previous model version
# Usage:   python model_rollback.py --model fuel_pricing_est --host <databricks-host> --token <token>
# Author:  Parthipan S

import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def rollback_model(model_name: str, host: str, token: str) -> None:
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(f"databricks")

    import os
    os.environ["DATABRICKS_HOST"] = host
    os.environ["DATABRICKS_TOKEN"] = token

    client = MlflowClient(tracking_uri="databricks")

    logger.info(f"=== FuelOps Model Rollback ===")
    logger.info(f"Model: {model_name}")

    # Get current champion
    try:
        current = client.get_model_version_by_alias(model_name, "champion")
        current_version = int(current.version)
        logger.info(f"Current champion: v{current_version} (run_id: {current.run_id[:8]})")
    except Exception as e:
        logger.error(f"Could not get current champion: {e}")
        sys.exit(1)

    # Find previous version
    if current_version <= 1:
        logger.error("Already at version 1. No previous version to rollback to.")
        sys.exit(1)

    prev_version = str(current_version - 1)

    # Verify previous version exists
    try:
        prev = client.get_model_version(model_name, prev_version)
        logger.info(f"Previous version: v{prev_version} (run_id: {prev.run_id[:8]})")
    except Exception as e:
        logger.error(f"Previous version v{prev_version} not found: {e}")
        sys.exit(1)

    # Swap champion alias
    logger.info(f"Swapping champion: v{current_version} -> v{prev_version}")
    client.set_registered_model_alias(model_name, "champion", prev_version)

    # Verify swap
    new_champion = client.get_model_version_by_alias(model_name, "champion")
    logger.info(f"Champion is now: v{new_champion.version}")

    if new_champion.version != prev_version:
        logger.error("Alias swap failed  version mismatch")
        sys.exit(1)

    logger.info(f"=== Model rollback complete: v{current_version} -> v{prev_version} ===")
    logger.info("NOTE: Restart FastAPI container to load new champion model")


def simulate_rollback(model_name: str) -> None:
    """Dry-run simulation when no Databricks connection available."""
    logger.info(f"=== SIMULATION MODE: Model Rollback ===")
    logger.info(f"Model: {model_name}")
    logger.info(f"Current champion: v3 (run_id: abc12345)")
    logger.info(f"Previous version: v2 (run_id: def67890)")
    logger.info(f"Swapping champion: v3 -> v2")
    logger.info(f"client.set_registered_model_alias('{model_name}', 'champion', '2')")
    logger.info(f"Champion is now: v2")
    logger.info(f"=== Simulation complete. In production, restart FastAPI to load v2 ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FuelOps MLflow model rollback")
    parser.add_argument("--model", default="fuel_pricing_est", help="Registered model name")
    parser.add_argument("--host", default="", help="Databricks workspace host")
    parser.add_argument("--token", default="", help="Databricks token")
    parser.add_argument("--simulate", action="store_true", help="Run simulation without Databricks")
    args = parser.parse_args()

    if args.simulate:
        simulate_rollback(args.model)
    else:
        if not args.host or not args.token:
            logger.error("--host and --token required (or use --simulate)")
            sys.exit(1)
        rollback_model(args.model, args.host, args.token)