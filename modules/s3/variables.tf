variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "force_destroy" {
  description = "Allow bucket deletion even if contains objects"
  type        = bool
  default     = false
}

variable "input_retention_days" {
  description = "Number of days to retain input files before deletion"
  type        = number
  default     = 90
}

variable "output_retention_days" {
  description = "Number of days to retain output results before deletion"
  type        = number
  default     = 365
}

variable "model_retention_days" {
  description = "Number of days to retain noncurrent model versions before deletion"
  type        = number
  default     = 730
}

variable "vault_retention_days" {
  description = "Number of days to retain noncurrent vault versions before deletion"
  type        = number
  default     = 365
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
