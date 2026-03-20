# Purpose: Reusable storage module  ADLS Gen2 account + blob container
# Inputs:  environment, location, resource_group_name, common_tags
# Outputs: storage_account_name, storage_account_id, container_name

resource "azurerm_storage_account" "datalake" {
  name                     = "fuelopsdata${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
  tags                     = var.common_tags
}

resource "azurerm_storage_container" "data" {
  name                  = "fuelops-data"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}
