# drift_detection.py
# Purpose: Calculate Population Stability Index (PSI) to detect feature drift
# Inputs:  Baseline distribution vs current distribution
# Outputs: PSI scores per feature, drift report, alert if PSI > threshold
# Author:  Parthipan S

import json
import logging
import sys
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -- Constants ------------------------------------------------------------------
PSI_THRESHOLD_WARNING = 0.1   # Slight drift  monitor
PSI_THRESHOLD_ALERT   = 0.2   # Significant drift  retrain
N_BINS = 10


# -- PSI Calculation ------------------------------------------------------------
def calculate_psi(baseline: np.ndarray, current: np.ndarray, n_bins: int = N_BINS) -> float:
    """
    Calculate Population Stability Index between baseline and current distributions.

    PSI < 0.1  : No significant drift
    PSI 0.1-0.2: Moderate drift  monitor closely
    PSI > 0.2  : Significant drift  trigger retraining

    Formula: PSI = sum((current% - baseline%) * ln(current% / baseline%))
    """
    # Create bins from baseline distribution
    breakpoints = np.linspace(
        min(baseline.min(), current.min()),
        max(baseline.max(), current.max()),
        n_bins + 1
    )

    # Calculate proportions per bin
    baseline_counts = np.histogram(baseline, bins=breakpoints)[0]
    current_counts  = np.histogram(current,  bins=breakpoints)[0]

    # Avoid division by zero  replace 0 with small value
    baseline_pct = np.where(baseline_counts == 0, 1e-6, baseline_counts / len(baseline))
    current_pct  = np.where(current_counts  == 0, 1e-6, current_counts  / len(current))

    # PSI formula
    psi_values = (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
    return float(np.sum(psi_values))


def interpret_psi(psi: float) -> str:
    if psi < PSI_THRESHOLD_WARNING:
        return "STABLE"
    elif psi < PSI_THRESHOLD_ALERT:
        return "WARNING"
    else:
        return "ALERT"


# -- Simulate data (used when no Delta Lake available) --------------------------
def generate_baseline_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Simulate 90-day baseline training data distribution."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "cost":             rng.normal(3.20, 0.15, n_samples).clip(2.5, 4.5),
        "competitor_price": rng.normal(3.35, 0.18, n_samples).clip(2.5, 4.8),
        "volume":           rng.normal(5000, 800,  n_samples).clip(1000, 12000),
        "market":           rng.choice(["EST","CST","MST","PST"], n_samples),
        "fuel_type":        rng.choice(["regular","premium","diesel"], n_samples),
    })


def generate_current_data(drift_level: str = "none", n_samples: int = 1000) -> pd.DataFrame:
    """
    Simulate current production data with optional drift injected.
    drift_level: none | moderate | severe
    """
    rng = np.random.default_rng(99)

    if drift_level == "none":
        return pd.DataFrame({
            "cost":             rng.normal(3.20, 0.15, n_samples).clip(2.5, 4.5),
            "competitor_price": rng.normal(3.35, 0.18, n_samples).clip(2.5, 4.8),
            "volume":           rng.normal(5000, 800,  n_samples).clip(1000, 12000),
        })
    elif drift_level == "moderate":
        # Shift mean by ~1 std  moderate drift
        return pd.DataFrame({
            "cost":             rng.normal(3.45, 0.20, n_samples).clip(2.5, 4.5),
            "competitor_price": rng.normal(3.60, 0.22, n_samples).clip(2.5, 4.8),
            "volume":           rng.normal(4200, 900,  n_samples).clip(1000, 12000),
        })
    else:  # severe
        # Shift mean by ~2 std  severe drift, definitely retraining needed
        return pd.DataFrame({
            "cost":             rng.normal(3.80, 0.30, n_samples).clip(2.5, 4.5),
            "competitor_price": rng.normal(4.10, 0.35, n_samples).clip(2.5, 4.8),
            "volume":           rng.normal(2500, 1200, n_samples).clip(1000, 12000),
        })


# -- Main drift detection -------------------------------------------------------
def run_drift_detection(
    drift_level: str = "none",
    slack_webhook: str = "",
    report_path: str = ""
) -> dict:

    logger.info("=== FuelOps Drift Detection ===")
    logger.info(f"Run date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"Simulating drift level: {drift_level}")

    # Load data
    baseline = generate_baseline_data()
    current  = generate_current_data(drift_level=drift_level)

    features = ["cost", "competitor_price", "volume"]
    results  = {}
    alerts   = []

    logger.info("")
    logger.info(f"{'Feature':<20} {'PSI':>8} {'Status':>10} {'Action':>20}")
    logger.info("-" * 62)

    for feature in features:
        psi    = calculate_psi(baseline[feature].values, current[feature].values)
        status = interpret_psi(psi)
        action = {
            "STABLE":  "No action needed",
            "WARNING": "Monitor closely",
            "ALERT":   "Trigger retraining",
        }[status]

        results[feature] = {"psi": round(psi, 4), "status": status, "action": action}
        logger.info(f"{feature:<20} {psi:>8.4f} {status:>10} {action:>20}")

        if status == "ALERT":
            alerts.append(feature)

    logger.info("-" * 62)

    # Overall status
    overall = "ALERT" if alerts else ("WARNING" if any(
        r["status"] == "WARNING" for r in results.values()
    ) else "STABLE")

    logger.info(f"\nOverall drift status: {overall}")

    if alerts:
        logger.warning(f"Features with significant drift: {alerts}")
        logger.warning("Recommendation: Trigger model retraining pipeline")

    # Build report
    report = {
        "run_date":    datetime.utcnow().isoformat(),
        "drift_level": drift_level,
        "overall":     overall,
        "features":    results,
        "alerts":      alerts,
        "baseline_samples": len(baseline),
        "current_samples":  len(current),
        "thresholds": {
            "warning": PSI_THRESHOLD_WARNING,
            "alert":   PSI_THRESHOLD_ALERT,
        }
    }

    # Save report
    if report_path:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {report_path}")

    # Send Slack alert if drift detected
    if alerts and slack_webhook:
        send_slack_alert(alerts, results, slack_webhook)

    return report


def send_slack_alert(alerts: list, results: dict, webhook_url: str) -> None:
    feature_lines = "\n".join([
        f"  - {f}: PSI={results[f]['psi']:.4f} ({results[f]['status']})"
        for f in alerts
    ])

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "FuelOps: Feature Drift Detected"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Drift Alert*  {len(alerts)} feature(s) exceed PSI threshold (>{PSI_THRESHOLD_ALERT})\n\n"
                        f"*Affected features:*\n{feature_lines}\n\n"
                        f"*Recommendation:* Trigger model retraining pipeline"
                    )
                }
            }
        ]
    }

    data = json.dumps(message).encode("utf-8")
    req  = urllib.request.Request(
        webhook_url, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        logger.info(f"Slack alert sent (HTTP {resp.getcode()})")


# -- CLI entry point ------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FuelOps drift detection")
    parser.add_argument(
        "--drift", choices=["none","moderate","severe"], default="none",
        help="Drift level to simulate"
    )
    parser.add_argument("--slack", default="", help="Slack webhook URL")
    parser.add_argument("--report", default="", help="Path to save JSON report")
    args = parser.parse_args()

    report = run_drift_detection(
        drift_level=args.drift,
        slack_webhook=args.slack,
        report_path=args.report,
    )

    # Exit code 1 if drift detected (useful for CI/CD gates)
    if report["overall"] == "ALERT":
        logger.error("Drift threshold exceeded  exiting with code 1")
        sys.exit(1)