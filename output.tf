###############################################################
# VPC and Networking Outputs                                  #
###############################################################

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = module.vpc.internet_gateway_id
}

###############################################################
# SNS Topics for ML Pipeline Events                           #
###############################################################

output "trigger_events_topic_arn" {
  description = "SNS topic ARN for ML job triggers"
  value       = module.sns.trigger_events_topic_arn
}

output "trigger_events_topic_name" {
  description = "SNS topic name for ML job triggers"
  value       = module.sns.trigger_events_topic_name
}

output "notifications_topic_arn" {
  description = "SNS topic ARN for ML job notifications"
  value       = module.sns.notifications_topic_arn
}

output "notifications_topic_name" {
  description = "SNS topic name for ML job notifications"
  value       = module.sns.notifications_topic_name
}

###############################################################
# S3 Bucket Outputs                                           #
###############################################################

output "ml_input_bucket" {
  description = "S3 bucket for ML input (scripts)"
  value       = module.s3.ml_input_bucket_name
}

output "ml_input_bucket_arn" {
  description = "ARN of the ML input bucket"
  value       = module.s3.ml_input_bucket_arn
}

output "ml_output_bucket" {
  description = "S3 bucket for ML results"
  value       = module.s3.ml_output_bucket_name
}

output "ml_output_bucket_arn" {
  description = "ARN of the ML output bucket"
  value       = module.s3.ml_output_bucket_arn
}

output "ml_models_bucket" {
  description = "S3 bucket for trained models"
  value       = module.s3.ml_models_bucket_name
}

output "ml_models_bucket_arn" {
  description = "ARN of the ML models bucket"
  value       = module.s3.ml_models_bucket_arn
}

###############################################################
# AWS Batch Outputs                                            #
###############################################################

output "batch_compute_environment_arn" {
  description = "ARN of the Batch compute environment"
  value       = module.batch.batch_compute_environment_arn
}

output "batch_job_queue" {
  description = "AWS Batch job queue name for ML workloads"
  value       = module.batch.batch_job_queue_name
}

output "batch_job_queue_arn" {
  description = "ARN of the Batch job queue"
  value       = module.batch.batch_job_queue_arn
}

output "ml_gpu_job_definition" {
  description = "Batch job definition for Python ML scripts"
  value       = module.batch.ml_gpu_job_definition_name
}

output "ml_gpu_job_definition_arn" {
  description = "ARN of the Python job definition"
  value       = module.batch.ml_gpu_job_definition_arn
}

###############################################################
# Lambda Function and Event Outputs                            #
###############################################################

output "trigger_dispatcher_function" {
  description = "Lambda function that dispatches trigger events"
  value       = module.lambda.trigger_dispatcher_name
}

output "trigger_dispatcher_function_arn" {
  description = "ARN of the trigger dispatcher Lambda function"
  value       = module.lambda.trigger_dispatcher_arn
}

output "trigger_dlq_url" {
  description = "URL of the SQS dead letter queue for failed triggers"
  value       = module.lambda.trigger_dlq_url
}

output "lambda_monitor_function" {
  description = "Lambda function for job monitoring"
  value       = module.lambda.monitor_lambda_function_arn
}

###############################################################
# CloudWatch Logs Outputs                                      #
###############################################################

output "batch_log_group" {
  description = "CloudWatch log group for ML Batch jobs"
  value       = module.batch.batch_log_group_name
}

output "lambda_log_group" {
  description = "CloudWatch log group for Lambda functions"
  value       = module.lambda.lambda_log_group_name
}

###############################################################
# IAM Role Outputs                                             #
###############################################################

output "batch_job_role_arn" {
  description = "IAM role ARN for Batch job execution"
  value       = module.batch.batch_job_role_arn
}

output "lambda_execution_role_arn" {
  description = "IAM role ARN for Lambda execution"
  value       = module.lambda.lambda_role_arn
}

###############################################################
# Quick Reference                                              #
###############################################################

output "quick_start_commands" {
  description = "Quick start commands for using the ML pipeline"
  value = {
    publish_trigger  = "aws sns publish --topic-arn '${module.lambda.trigger_events_topic_arn}' --message '{\"trigger_type\": \"batch_job\", \"data\": {\"script_key\": \"jobs/train.py\"}, \"metadata\": {\"user\": \"data-scientist\"}}'  "
    view_logs        = "aws logs tail /aws/lambda/${var.project_name}-ml-trigger-dispatcher --follow"
    check_dlq        = "aws sqs receive-message --queue-url '${module.lambda.trigger_dlq_url}'"
    download_results = "aws s3 sync s3://${module.s3.ml_output_bucket_name}/results/ ./results/"
  }
}
