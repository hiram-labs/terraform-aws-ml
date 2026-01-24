output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.batch_job_trigger.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.batch_job_trigger.function_name
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_batch_trigger_role.arn
}

output "lambda_log_group_name" {
  description = "Name of the Lambda CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_log_group.name
}

output "monitor_lambda_function_arn" {
  description = "ARN of the monitoring Lambda function"
  value       = var.enable_job_monitoring ? aws_lambda_function.batch_job_monitor[0].arn : null
}
