# Incident Report: FuelOps API High Error Rate
**Date:** 2026-03-23
**Severity:** P1 - Critical
**Status:** Resolved
**Author:** Parthipan S

---

## Timeline (UTC)

| Time | Event |
|------|-------|
| 13:05 | Bad image `fuelops-api:bad` deployed to local environment |
| 13:06 | 50 requests sent  80% returning HTTP 500 (ModelLoadError) |
| 13:07 | Prometheus scrapes error_count_total: ModelLoadError=40, NonsenseOutput=10 |
| 13:08 | Grafana High Error Rate alert fires  Slack notification received |
| 13:09 | On-call engineer (Parthipan) acknowledges alert |
| 13:10 | Root cause identified: bad container image with corrupt model weights |
| 13:11 | Level 1 rollback executed  bad container stopped, good image restored |
| 13:12 | API health check passes  model_version=mock-v1, error_count=0 |
| 13:13 | Grafana alert resolves  Slack resolve notification received |

**Total incident duration:** ~8 minutes
**Time to detect:** ~2 minutes (Grafana alert threshold: error rate > 5% for 2 min)
**Time to recover:** ~2 minutes (Level 1 rollback)

---

## Root Cause

A container image (`fuelops-api:bad`) containing a deliberately broken inference
function was deployed. The `predict` endpoint raised `ModelLoadError` on 80% of
requests due to simulated corrupt model weights. The remaining 20% returned
nonsense predictions (`predicted_price: -999.99`).

The image passed health checks (`/health` returns 200) because the health endpoint
does not validate model inference  only that the service is running.

---

## Impact

- **Predictions affected:** 50 requests during incident window
- **Error rate peak:** 80% (threshold: 5%)
- **Revenue impact:** None (simulation environment)
- **Data corruption:** None (no writes to Delta tables during incident)
- **Downstream impact:** Batch scoring pipeline not affected (Airflow DAG not running)

---

## Resolution

**Level 1 rollback executed:**
1. Stopped bad container: `docker stop fuelops-bad`
2. Started known-good image: `docker run fuelops-api:local`
3. Verified: `/health` returned `model_version=mock-v1`
4. Confirmed: `error_count_total` reset to 0

**Recovery time:** < 2 minutes from decision to healthy API.

---

## Detection Gap

The `/health` endpoint returned 200 even for the bad image. Health checks only
verify the service is running  not that the model produces valid predictions.

---

## Action Items

| # | Action | Owner | Due |
|---|--------|-------|-----|
| 1 | Add model inference smoke test to /health endpoint | Parthipan | Day 22 |
| 2 | Add CI/CD gate: run predict test before deploying to staging | Parthipan | Day 22 |
| 3 | Add prediction value range validation (reject price < 0) | Parthipan | Day 22 |
| 4 | Store last known good image SHA in Key Vault for fast rollback | Parthipan | Day 25 |

---

## What Worked Well

- Grafana alert fired within 2 minutes of error spike
- Slack notification included clear summary and description
- Alert resolved automatically when service recovered
- Rollback executed in < 2 minutes with zero data loss
- git checkout restored clean source code instantly

---

## Prevention

1. **Pre-deploy validation:** Run 10 predict requests against staging before
   promoting to production. If error rate > 1%, block deploy.
2. **Health check improvement:** `/health` should call `model.predict()` with
   a known input and validate the output is within expected range.
3. **Image tagging policy:** Never deploy `latest` tag to production.
   Always use commit SHA tags (already implemented in CI/CD Stage 4).