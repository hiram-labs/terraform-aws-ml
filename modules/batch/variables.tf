variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for Batch compute environment"
  type        = string
}

variable "private_subnets" {
  description = "Private subnet IDs for Batch compute instances"
  type        = list(string)
}

variable "ml_input_bucket" {
  description = "S3 bucket name for ML input data (scripts/notebooks)"
  type        = string
}

variable "ml_output_bucket" {
  description = "S3 bucket name for ML output results"
  type        = string
}

variable "ml_container_image" {
  description = "ECR container image URI for ML Python jobs"
  type        = string
  default     = "tensorflow/tensorflow:latest-gpu"
}

variable "notebook_container_image" {
  description = "ECR container image URI for Jupyter notebook execution"
  type        = string
  default     = "jupyter/tensorflow-notebook:latest"
}

variable "gpu_instance_types" {
  description = "List of GPU instance types for Batch compute environment"
  type        = list(string)
  default     = ["g4dn.xlarge", "g4dn.2xlarge", "p3.2xlarge"]
}

variable "gpu_instance_type" {
  description = "Default GPU instance type for launch template"
  type        = string
  default     = "g4dn.xlarge"
}

variable "ecs_gpu_ami_id" {
  description = "AMI ID for ECS-optimized GPU instances (leave empty for latest)"
  type        = string
  default     = "" # Will use latest ECS GPU-optimized AMI
}

variable "min_vcpus" {
  description = "Minimum number of vCPUs in compute environment"
  type        = number
  default     = 0
}

variable "max_vcpus" {
  description = "Maximum number of vCPUs in compute environment"
  type        = number
  default     = 256
}

variable "desired_vcpus" {
  description = "Desired number of vCPUs in compute environment"
  type        = number
  default     = 0
}

variable "use_spot_instances" {
  description = "Use Spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "spot_bid_percentage" {
  description = "Maximum percentage of on-demand price for spot instances"
  type        = number
  default     = 70
}

variable "job_vcpus" {
  description = "Number of vCPUs for each job"
  type        = number
  default     = 4
}

variable "job_memory" {
  description = "Memory in MiB for each job"
  type        = number
  default     = 16384 # 16 GB
}

variable "job_gpus" {
  description = "Number of GPUs for each job"
  type        = number
  default     = 1
}

variable "job_retry_attempts" {
  description = "Number of retry attempts for failed jobs"
  type        = number
  default     = 3
}

variable "job_timeout_seconds" {
  description = "Job timeout in seconds"
  type        = number
  default     = 86400 # 24 hours
}

variable "root_volume_size" {
  description = "Root volume size in GB for compute instances"
  type        = number
  default     = 100
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
