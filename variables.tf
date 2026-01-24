###############################################################
# Core Configuration Variables                                #
###############################################################

variable "project_name" {
  type        = string
  description = "Name of the ML pipeline project"
  default     = "ml-pipeline"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name)) && length(var.project_name) >= 3 && length(var.project_name) <= 32
    error_message = "Project name must be lowercase alphanumeric with hyphens, between 3 and 32 characters."
  }
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  type        = string
  description = "AWS region for ML infrastructure"
  default     = "us-east-1"
}

###############################################################
# Network Configuration                                        #
###############################################################

variable "vpc_id" {
  type        = string
  description = "VPC ID (required if use_existing_vpc = false)"
  default     = ""
}

variable "private_subnets" {
  type        = list(string)
  description = "Private subnet IDs (required if use_existing_vpc = false)"
  default     = []
}

###############################################################
# SNS Configuration                                            #
###############################################################

variable "sns_topic_arn" {
  type        = string
  description = "SNS topic ARN for notifications (required if use_existing_sns = false)"
  default     = ""
}

###############################################################
# Container Images                                             #
###############################################################

variable "ml_container_image" {
  type        = string
  description = "ECR URI for ML Python container image"
  default     = "tensorflow/tensorflow:latest-gpu"
}

variable "notebook_container_image" {
  type        = string
  description = "ECR URI for Jupyter notebook container image"
  default     = "jupyter/tensorflow-notebook:latest"
}

###############################################################
# GPU Instance Configuration                                   #
###############################################################

variable "ml_gpu_instance_types" {
  type        = list(string)
  description = "List of GPU instance types for ML workloads"
  default     = ["g4dn.xlarge", "g4dn.2xlarge", "g5.xlarge"]
}

variable "ml_use_spot_instances" {
  type        = bool
  description = "Use Spot instances for cost optimization"
  default     = true
}

variable "ml_min_vcpus" {
  type        = number
  description = "Minimum vCPUs for Batch compute environment"
  default     = 0
}

variable "ml_max_vcpus" {
  type        = number
  description = "Maximum vCPUs for Batch compute environment"
  default     = 256
}

###############################################################
# Job Resource Configuration                                   #
###############################################################

variable "ml_job_vcpus" {
  type        = number
  description = "Default vCPUs per ML job"
  default     = 4
}

variable "ml_job_memory" {
  type        = number
  description = "Default memory (MiB) per ML job"
  default     = 16384
}

variable "ml_job_gpus" {
  type        = number
  description = "Default GPUs per ML job"
  default     = 1
}

###############################################################
# Storage Configuration                                        #
###############################################################

variable "force_destroy_buckets" {
  type        = bool
  description = "Allow S3 bucket deletion even if contains objects"
  default     = true
}

variable "ml_input_retention_days" {
  type        = number
  description = "Days to retain input files in S3"
  default     = 90
}

variable "enable_ml_models_bucket" {
  type        = bool
  description = "Create separate S3 bucket for trained models"
  default     = true
}

###############################################################
# Monitoring & Notifications                                   #
###############################################################

variable "ml_trigger_prefix" {
  type        = string
  description = "S3 prefix that triggers Lambda jobs (empty = all uploads trigger jobs)"
  default     = ""
}

variable "enable_ml_notifications" {
  type        = bool
  description = "Enable SNS notifications for ML job status"
  default     = true
}

variable "enable_ml_job_monitoring" {
  type        = bool
  description = "Enable Lambda monitoring for ML job completions"
  default     = true
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 7
}

###############################################################
# Resource Tags                                                #
###############################################################

variable "common_tags" {
  type        = map(string)
  description = "Common tags for all resources"
  default     = {}
}
