###############################################################
# Data Sources                                                #
###############################################################

# Get available AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}

###############################################################
# Local Variables                                             #
###############################################################

locals {
  # Use specified AZs or default to first 2 available
  availability_zones = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)
}
