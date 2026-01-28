output "trigger_dispatcher_arn" {
  description = "ARN of the trigger dispatcher Lambda function"
  value       = aws_lambda_function.trigger_dispatcher.arn
}

output "trigger_dispatcher_name" {
  description = "Name of the trigger dispatcher Lambda function"
  value       = aws_lambda_function.trigger_dispatcher.function_name
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_trigger_dispatcher_role.arn
}

output "lambda_log_group_name" {
  description = "Name of the Lambda CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_trigger_dispatcher_log.name
}

output "trigger_events_topic_arn" {
  description = "ARN of the SNS topic for trigger events"
  value       = var.trigger_events_topic_arn
}

output "trigger_events_topic_name" {
  description = "Name of the SNS topic for trigger events"
  value       = split(":", var.trigger_events_topic_arn)[5]
}

output "trigger_dlq_url" {
  description = "URL of the SQS dead letter queue"
  value       = aws_sqs_queue.ml_trigger_dlq.id
}

output "monitor_lambda_function_arn" {
  description = "ARN of the monitoring Lambda function"
  value       = var.enable_job_monitoring ? aws_lambda_function.batch_job_monitor[0].arn : null
}
