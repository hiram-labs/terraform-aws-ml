########################################################################
# Remote State Backend Configuration                                   #
#                                                                      #
# Backend configuration cannot use variables, so values must be        #
# provided via CLI flags during terraform init.                        #
#                                                                      #
# Usage:                                                               #
#   terraform init \                                                   #
#     -backend-config="bucket=ml-pipeline-dev-terraform-state" \       #
#     -backend-config="dynamodb_table=ml-pipeline-dev-terraform-lock" \#
#     -backend-config="region=us-east-1" \                             #
#     -migrate-state                                                   #
#                                                                      #
# Use your actual project_name, environment, and aws_region values.    #
########################################################################

terraform {
  backend "s3" {
    # Values provided via -backend-config flags during init
    key     = "ml-pipeline/terraform.tfstate"
    encrypt = true
  }
}
