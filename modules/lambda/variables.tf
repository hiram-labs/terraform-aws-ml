variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "trigger_events_topic_arn" {
  description = "ARN of the SNS topic for ML job triggers"
  type        = string
}

variable "notifications_topic_arn" {
  description = "ARN of the SNS topic for ML job notifications"
  type        = string
}

variable "ml_input_bucket" {
  description = "S3 bucket name for ML input data"
  type        = string
}

variable "ml_output_bucket" {
  description = "S3 bucket name for ML output results"
  type        = string
}

variable "ml_models_bucket" {
  description = "S3 bucket name for ML models"
  type        = string
}

variable "ml_vault_bucket" {
  description = "S3 bucket name for ML vault storage"
  type        = string
}

variable "ml_output_bucket_arn" {
  description = "ARN of the S3 bucket for ML output results"
  type        = string
}

variable "gpu_job_queue_name" {
  description = "Name of the GPU Batch job queue"
  type        = string
}

variable "gpu_job_queue_arn" {
  description = "ARN of the GPU Batch job queue"
  type        = string
}

variable "cpu_job_queue_arn" {
  description = "ARN of the CPU Batch job queue"
  type        = string
}

variable "batch_job_role_arn" {
  description = "ARN of the Batch job execution role"
  type        = string
}

variable "batch_ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role for Batch jobs"
  type        = string
}

variable "ml_gpu_job_definition_name" {
  description = "Name of the ML Python job definition"
  type        = string
}

variable "cpu_job_queue_name" {
  description = "Name of the CPU job queue"
  type        = string
}

variable "ml_cpu_job_definition_name" {
  description = "Name of the ML Python CPU job definition"
  type        = string
}

variable "enable_notifications" {
  description = "Enable SNS notifications for job status"
  type        = bool
  default     = false
}

variable "enable_job_monitoring" {
  description = "Enable Lambda function for monitoring job status"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "default_gpu_vcpus" {
  description = "Default vCPUs for GPU jobs"
  type        = number
  default     = 4
}

variable "default_gpu_memory" {
  description = "Default memory (MiB) for GPU jobs"
  type        = number
  default     = 16384
}

variable "default_gpu_gpus" {
  description = "Default GPUs for GPU jobs"
  type        = number
  default     = 1
}

variable "default_cpu_vcpus" {
  description = "Default vCPUs for CPU jobs"
  type        = number
  default     = 2
}

variable "default_cpu_memory" {
  description = "Default memory (MiB) for CPU jobs"
  type        = number
  default     = 4096
}

variable "default_memory" {
  description = "Default memory override for jobs (MiB)"
  type        = number
  default     = 16384
}

variable "default_gpus" {
  description = "Default GPUs override for jobs"
  type        = number
  default     = 1
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
