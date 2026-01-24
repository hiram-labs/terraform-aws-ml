###############################################################
# Local Variables                                             #
###############################################################

locals {
  common_tags = merge(
    var.common_tags,
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Module      = "ML-Pipeline"
    }
  )
}
