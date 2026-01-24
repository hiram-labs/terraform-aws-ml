###############################################################
# ML Pipeline Infrastructure                                  #
#                                                             #
# Standalone Terraform configuration for GPU-accelerated      #
# machine learning pipeline on AWS.                           #
#                                                             #
###############################################################

provider "aws" {
  region = var.aws_region
}

###############################################################
# S3 Buckets for ML Data                                      #
###############################################################

module "s3" {
  source = "./modules/s3"
  
  project_name         = var.project_name
  force_destroy        = var.force_destroy_buckets
  input_retention_days = var.ml_input_retention_days
  create_models_bucket = var.enable_ml_models_bucket
  common_tags          = local.common_tags
}

###############################################################
# AWS Batch GPU Compute Environment                           #
###############################################################

module "batch" {
  source = "./modules/batch"
  
  project_name             = var.project_name
  aws_region               = var.aws_region
  vpc_id                   = var.vpc_id
  private_subnets          = var.private_subnets
  ml_input_bucket          = module.s3.ml_input_bucket_name
  ml_output_bucket         = module.s3.ml_output_bucket_name
  ml_container_image       = var.ml_container_image
  notebook_container_image = var.notebook_container_image
  gpu_instance_types       = var.ml_gpu_instance_types
  use_spot_instances       = var.ml_use_spot_instances
  min_vcpus                = var.ml_min_vcpus
  max_vcpus                = var.ml_max_vcpus
  job_vcpus                = var.ml_job_vcpus
  job_memory               = var.ml_job_memory
  job_gpus                 = var.ml_job_gpus
  log_retention_days       = var.log_retention_days
  common_tags              = local.common_tags
}

###############################################################
# Lambda Functions for Job Orchestration                      #
###############################################################

module "lambda" {
  source = "./modules/lambda"
  
  project_name                    = var.project_name
  ml_input_bucket                 = module.s3.ml_input_bucket_name
  ml_output_bucket                = module.s3.ml_output_bucket_name
  batch_job_queue_name            = module.batch.batch_job_queue_name
  batch_job_queue_arn             = module.batch.batch_job_queue_arn
  ml_python_job_definition_name   = module.batch.ml_python_job_definition_name
  ml_notebook_job_definition_name = module.batch.ml_notebook_job_definition_name
  input_prefix                    = var.ml_trigger_prefix
  enable_notifications            = var.enable_ml_notifications
  sns_topic_arn                   = var.sns_topic_arn
  enable_job_monitoring           = var.enable_ml_job_monitoring
  log_retention_days              = var.log_retention_days
  common_tags                     = local.common_tags
}
