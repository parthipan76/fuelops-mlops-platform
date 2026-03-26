terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.5.0"
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = "rg-fuelops-${var.environment}"
  location = var.location
  tags     = var.common_tags
}

module "storage" {
  source              = "./modules/storage"
  environment         = var.environment
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  common_tags         = var.common_tags
}

resource "azurerm_key_vault" "main" {
  name                = "kv-fuelops-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
  access_policy {
    tenant_id          = data.azurerm_client_config.current.tenant_id
    object_id          = data.azurerm_client_config.current.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
  }
  tags = var.common_tags
}

resource "azurerm_key_vault_secret" "storage_key" {
  name         = "storage-account-key"
  value        = "placeholder-will-replace-with-real-key"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "api_key" {
  name         = "dummy-api-key"
  value        = "fuelops-api-key-dev-12345"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "db_token" {
  name         = "db-token"
  value        = "placeholder-databricks-token"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_container_registry" "main" {
  name                = "fuelopsacr${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.common_tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-fuelops-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.common_tags
}

resource "azurerm_container_app_environment" "main" {
  count               = var.create_container_app_env ? 1 : 0
  name                = "cae-fuelops-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.common_tags
}

resource "azurerm_container_app" "api" {
  count                        = var.create_container_app_env ? 1 : 0
  name                         = "fuelops-api-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = var.acr_admin_password
  }

  secret {
    name  = "api-key"
    value = "fuelops-api-key-dev-12345"
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "fuelops-api"
      image  = "${azurerm_container_registry.main.login_server}/fuelops-api:v1"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "API_KEY"
        secret_name = "api-key"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.common_tags
}
