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
# VPC and Networking                                          #
###############################################################

module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  vpc_cidr           = var.vpc_cidr
  availability_zones = local.availability_zones
  common_tags        = local.common_tags
}

###############################################################
# SNS Topics for ML Pipeline Events                           #
###############################################################

module "sns" {
  source = "./modules/sns"

  project_name        = var.project_name
  notification_emails = var.notification_emails
  common_tags         = local.common_tags
}

###############################################################
# S3 Buckets for ML Data                                      #
###############################################################

module "s3" {
  source = "./modules/s3"

  project_name           = var.project_name
  force_destroy          = var.force_destroy_buckets
  input_retention_days   = var.ml_input_retention_days
  output_retention_days  = var.ml_output_retention_days
  model_retention_days   = var.ml_model_retention_days
  vault_retention_days   = var.ml_vault_retention_days
  common_tags            = local.common_tags
}

###############################################################
# EFS for Model Caching                                       #
###############################################################

module "efs" {
  source = "./modules/efs"

  project_name       = var.project_name
  vpc_id             = module.vpc.vpc_id
  vpc_cidr           = var.vpc_cidr
  private_subnet_ids = module.vpc.public_subnet_ids
  common_tags        = local.common_tags
}

###############################################################
# AWS Batch GPU Compute Environment                           #
###############################################################

module "batch" {
  source = "./modules/batch"

  project_name           = var.project_name
  aws_region             = var.aws_region
  vpc_id                 = module.vpc.vpc_id
  efs_file_system_id     = module.efs.efs_file_system_id
  efs_access_point_id    = module.efs.efs_access_point_id
  private_subnets        = module.vpc.public_subnet_ids
  ml_input_bucket        = module.s3.ml_input_bucket_name
  ml_output_bucket       = module.s3.ml_output_bucket_name
  ml_models_bucket       = module.s3.ml_models_bucket_name
  ml_vault_bucket        = module.s3.ml_vault_bucket_name
  ml_gpu_container_image = var.ml_gpu_container_image
  ml_cpu_container_image = var.ml_cpu_container_image
  gpu_instance_types     = var.ml_gpu_instance_types
  use_spot_instances     = var.ml_gpu_use_spot_instances
  min_vcpus              = var.ml_gpu_min_vcpus
  max_vcpus              = var.ml_gpu_max_vcpus
  desired_vcpus          = var.ml_gpu_desired_vcpus
  job_vcpus              = var.ml_gpu_job_vcpus
  job_memory             = var.ml_gpu_job_memory
  job_gpus               = var.ml_gpu_job_gpus
  cpu_instance_types     = var.ml_cpu_instance_types
  cpu_use_spot_instances = var.ml_cpu_use_spot_instances
  cpu_min_vcpus          = var.ml_cpu_min_vcpus
  cpu_max_vcpus          = var.ml_cpu_max_vcpus
  cpu_desired_vcpus      = var.ml_cpu_desired_vcpus
  cpu_job_vcpus          = var.ml_cpu_job_vcpus
  cpu_job_memory         = var.ml_cpu_job_memory
  log_retention_days     = var.log_retention_days
  common_tags            = local.common_tags
}

###############################################################
# Lambda Functions for Job Orchestration                      #
###############################################################

module "lambda" {
  source = "./modules/lambda"

  project_name               = var.project_name
  trigger_events_topic_arn   = module.sns.trigger_events_topic_arn
  notifications_topic_arn    = module.sns.notifications_topic_arn
  ml_input_bucket            = module.s3.ml_input_bucket_name
  ml_output_bucket           = module.s3.ml_output_bucket_name
  ml_output_bucket_arn       = module.s3.ml_output_bucket_arn
  ml_models_bucket           = module.s3.ml_models_bucket_name
  ml_vault_bucket            = module.s3.ml_vault_bucket_name
  batch_job_queue_name       = module.batch.batch_job_queue_name
  batch_job_queue_arn        = module.batch.batch_job_queue_arn
  batch_job_role_arn         = module.batch.batch_job_role_arn
  batch_ecs_task_execution_role_arn = module.batch.batch_ecs_task_execution_role_arn
  ml_gpu_job_definition_name = module.batch.ml_gpu_job_definition_name
  cpu_job_queue_name         = module.batch.cpu_job_queue_name
  ml_cpu_job_definition_name = module.batch.ml_cpu_job_definition_name
  enable_notifications       = var.enable_ml_notifications
  enable_job_monitoring      = var.enable_ml_job_monitoring
  log_retention_days         = var.log_retention_days
  default_gpu_vcpus          = var.ml_gpu_job_vcpus
  default_gpu_memory         = var.ml_gpu_job_memory
  default_gpu_gpus           = var.ml_gpu_job_gpus
  default_cpu_vcpus          = var.ml_cpu_job_vcpus
  default_cpu_memory         = var.ml_cpu_job_memory
  common_tags                = local.common_tags
}
