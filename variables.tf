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

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "List of availability zones for subnet deployment"
  default     = [] # Will use first 2 AZs in region if not specified
}

###############################################################
# Container Images                                             #
###############################################################

variable "ml_gpu_container_image" {
  type        = string
  description = "ECR URI for ML GPU container image"
  default     = "tensorflow/tensorflow:latest-gpu"
}

variable "ml_cpu_container_image" {
  type        = string
  description = "ECR URI for ML CPU container image"
  default     = "tensorflow/tensorflow:latest"
}

###############################################################
# GPU Instance Configuration                                   #
###############################################################

variable "ml_gpu_instance_types" {
  type        = list(string)
  description = "List of GPU instance types for ML workloads"
  default     = ["g4dn.xlarge", "g4dn.2xlarge", "g5.xlarge"]
}

variable "ml_gpu_use_spot_instances" {
  type        = bool
  description = "Use Spot instances for GPU compute (cost optimization)"
  default     = true
}

variable "ml_gpu_min_vcpus" {
  type        = number
  description = "Minimum vCPUs for GPU compute environment"
  default     = 0
}

variable "ml_gpu_max_vcpus" {
  type        = number
  description = "Maximum vCPUs for GPU compute environment"
  default     = 256
}

###############################################################
# GPU Job Resource Configuration                               #
###############################################################

variable "ml_gpu_job_vcpus" {
  type        = number
  description = "Default vCPUs per GPU job"
  default     = 4
}

variable "ml_gpu_job_memory" {
  type        = number
  description = "Default memory (MiB) per GPU job"
  default     = 16384
}

variable "ml_gpu_job_gpus" {
  type        = number
  description = "Default GPUs per job"
  default     = 1
}

variable "ml_gpu_desired_vcpus" {
  type        = number
  description = "Desired vCPUs for GPU compute environment"
  default     = 0
}

###############################################################
# CPU Instance Configuration                                   #
###############################################################

variable "ml_cpu_instance_types" {
  type        = list(string)
  description = "List of CPU instance types for non-GPU workloads"
  default     = ["m5.large", "m5.xlarge", "c6a.large", "c6a.xlarge"]
}

variable "ml_cpu_use_spot_instances" {
  type        = bool
  description = "Use Spot instances for CPU compute (cost optimization)"
  default     = true
}

variable "ml_cpu_min_vcpus" {
  type        = number
  description = "Minimum vCPUs for CPU compute environment"
  default     = 0
}

variable "ml_cpu_max_vcpus" {
  type        = number
  description = "Maximum vCPUs for CPU compute environment"
  default     = 128
}

variable "ml_cpu_desired_vcpus" {
  type        = number
  description = "Desired vCPUs for CPU compute environment"
  default     = 0
}

###############################################################
# CPU Job Resource Configuration                               #
###############################################################

variable "ml_cpu_job_vcpus" {
  type        = number
  description = "Default vCPUs per CPU job"
  default     = 2
}

variable "ml_cpu_job_memory" {
  type        = number
  description = "Default memory (MiB) per CPU job"
  default     = 4096
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

variable "ml_output_retention_days" {
  type        = number
  description = "Days to retain output results in S3"
  default     = 365
}

variable "ml_model_retention_days" {
  type        = number
  description = "Days to retain noncurrent model versions in S3"
  default     = 730
}

variable "ml_vault_retention_days" {
  type        = number
  description = "Days to retain noncurrent vault versions in S3"
  default     = 365
}

###############################################################
# Monitoring & Notifications                                   #
###############################################################

variable "enable_ml_notifications" {
  type        = bool
  description = "Enable SNS notifications for ML job status"
  default     = true
}

variable "notification_emails" {
  type        = list(string)
  description = "List of email addresses to receive job notifications"
  default     = []
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
