variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    project    = "fuelops"
    managed_by = "terraform"
    owner      = "parthipan"
  }
}

variable "create_container_app_env" {
  description = "Whether to create a Container Apps Environment (free tier: 1 per subscription)"
  type        = bool
  default     = false
}

variable "acr_admin_password" {
  description = "ACR admin password for Container App image pull"
  type        = string
  sensitive   = true
}
