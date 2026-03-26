# =============================================================================
# monitoring.tf  Azure Managed Prometheus + Grafana
# Purpose: Production observability stack for FuelOps
# =============================================================================

#  Azure Monitor Workspace (Managed Prometheus) 
resource "azurerm_monitor_workspace" "main" {
  name                = "amw-fuelops-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.common_tags
}

#  Azure Managed Grafana 
resource "azurerm_dashboard_grafana" "main" {
  name                              = "grafana-fuelops-${var.environment}"
  resource_group_name               = azurerm_resource_group.main.name
  location                          = azurerm_resource_group.main.location
  sku                               = "Standard"
  grafana_major_version = 11
  public_network_access_enabled     = true

  azure_monitor_workspace_integrations {
    resource_id = azurerm_monitor_workspace.main.id
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags
}

#  Role: Grafana  Prometheus (Monitoring Data Reader) 
resource "azurerm_role_assignment" "grafana_prometheus" {
  scope                = azurerm_monitor_workspace.main.id
  role_definition_name = "Monitoring Data Reader"
  principal_id         = azurerm_dashboard_grafana.main.identity[0].principal_id
}

#  Role: Your identity  Grafana Admin 
resource "azurerm_role_assignment" "user_grafana_admin" {
  scope                = azurerm_dashboard_grafana.main.id
  role_definition_name = "Grafana Admin"
  principal_id         = data.azurerm_client_config.current.object_id
}

#  Role: Grafana  Monitor Reader (for Azure Monitor metrics) 
resource "azurerm_role_assignment" "grafana_monitor_reader" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Monitoring Reader"
  principal_id         = azurerm_dashboard_grafana.main.identity[0].principal_id
}

#  Data Collection Endpoint 
resource "azurerm_monitor_data_collection_endpoint" "main" {
  name                = "dce-fuelops-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.common_tags
}

#  Data Collection Rule (scrape Container App /metrics) 
resource "azurerm_monitor_data_collection_rule" "prometheus" {
  name                        = "dcr-fuelops-${var.environment}"
  resource_group_name         = azurerm_resource_group.main.name
  location                    = azurerm_resource_group.main.location
  data_collection_endpoint_id = azurerm_monitor_data_collection_endpoint.main.id
  tags                        = var.common_tags

  destinations {
    monitor_account {
      monitor_account_id = azurerm_monitor_workspace.main.id
      name               = "fuelops-prometheus"
    }
  }

  data_flow {
    streams      = ["Microsoft-PrometheusMetrics"]
    destinations = ["fuelops-prometheus"]
  }

  data_sources {
    prometheus_forwarder {
      name    = "fuelops-prom-forwarder"
      streams = ["Microsoft-PrometheusMetrics"]
    }
  }
}

#  Link DCR to Container App Environment 
resource "azurerm_monitor_data_collection_rule_association" "container_env" {
  count                   = var.create_container_app_env ? 1 : 0
  name                    = "dcra-fuelops-${var.environment}"
  target_resource_id      = azurerm_container_app_environment.main[0].id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.prometheus.id
}

#  Outputs 
output "grafana_endpoint" {
  value       = azurerm_dashboard_grafana.main.endpoint
  description = "Azure Managed Grafana URL"
}

output "prometheus_endpoint" {
  value       = azurerm_monitor_workspace.main.query_endpoint
  description = "Azure Managed Prometheus query endpoint"
}