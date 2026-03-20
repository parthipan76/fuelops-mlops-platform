output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "resource_group_location" {
  value = azurerm_resource_group.main.location
}

output "storage_account_name" {
  value = module.storage.storage_account_name
}

output "storage_account_id" {
  value = module.storage.storage_account_id
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "container_app_environment_name" {
  value = length(azurerm_container_app_environment.main) > 0 ? azurerm_container_app_environment.main[0].name : "not-provisioned"
}

output "container_app_url" {
  value = length(azurerm_container_app.api) > 0 ? "https://${azurerm_container_app.api[0].ingress[0].fqdn}" : "not-provisioned"
}
