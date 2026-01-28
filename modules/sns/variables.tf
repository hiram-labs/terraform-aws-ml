variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "notification_emails" {
  description = "List of email addresses to receive job notifications (optional)"
  type        = list(string)
  default     = []
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}
