# Day 23 Chaos Test Log
Date: 2026-04-07

| # | Scenario | Detection | Recovery | Status |
|---|----------|-----------|----------|--------|
| 1 | Corrupt Bronze data | Quarantine table (partial) | DELETE from bronze/silver |  Complete |
| 2 | Deploy bad model | Azure Grafana HTTP traffic spike | az containerapp revision activate |  Complete |
| 3 | API overload (100 req) | 100% success, avg 3491ms | Auto-scale, no action needed |  Complete |
| 4 | Wrong SP credentials | GitLab deploy-staging fails | Restore AZURE_TENANT_ID variable |  Complete |
| 5 | Missing Key Vault secret | No live impact detected | az keyvault secret recover |  Complete |

## Key Findings
1. Silver layer accepts invalid market/fuel_type  no enum validation
2. NULL cost rows silently dropped  not quarantined, no observability
3. Key Vault secret deletion has no impact on running containers  secret baked in at deploy time
4. GitLab runner cache masks SP credential failures on build stage
5. Container Apps auto-scaling handled 100 concurrent requests with 0% error rate

## Bonus Achievements
- Azure Managed Prometheus provisioned via Terraform
- Azure Managed Grafana provisioned via Terraform (Grafana v11)
- 10-panel dashboard migrated to Azure Grafana
- Azure Monitor dashboard created with Container App platform metrics
- Key Vault access policy fixed (added Recover permission)
- Terraform provider upgraded to azurerm ~> 4.0