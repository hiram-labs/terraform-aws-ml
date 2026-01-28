output "trigger_events_topic_arn" {
  description = "ARN of the SNS topic for ML job triggers"
  value       = aws_sns_topic.ml_trigger_events.arn
}

output "trigger_events_topic_name" {
  description = "Name of the SNS topic for ML job triggers"
  value       = aws_sns_topic.ml_trigger_events.name
}

output "notifications_topic_arn" {
  description = "ARN of the SNS topic for ML job notifications"
  value       = aws_sns_topic.ml_notifications.arn
}

output "notifications_topic_name" {
  description = "Name of the SNS topic for ML job notifications"
  value       = aws_sns_topic.ml_notifications.name
}
