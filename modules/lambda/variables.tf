variable "project_name" {
  description = "Name of the project"
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

variable "batch_job_queue_name" {
  description = "Name of the Batch job queue"
  type        = string
}

variable "batch_job_queue_arn" {
  description = "ARN of the Batch job queue"
  type        = string
}

variable "ml_python_job_definition_name" {
  description = "Name of the ML Python job definition"
  type        = string
}

variable "ml_notebook_job_definition_name" {
  description = "Name of the ML Notebook job definition"
  type        = string
}

variable "input_prefix" {
  description = "S3 prefix filter for triggering jobs (e.g., 'jobs/')"
  type        = string
  default     = ""
}

variable "enable_notifications" {
  description = "Enable SNS notifications for job status"
  type        = bool
  default     = false
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
  default     = ""
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

variable "default_vcpus" {
  description = "Default vCPUs override for jobs"
  type        = number
  default     = 4
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
