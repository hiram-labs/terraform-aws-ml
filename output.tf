###############################################################
# S3 Bucket Outputs                                           #
###############################################################

output "ml_input_bucket" {
  description = "S3 bucket for ML input (scripts/notebooks)"
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

output "ml_python_job_definition" {
  description = "Batch job definition for Python ML scripts"
  value       = module.batch.ml_python_job_definition_name
}

output "ml_python_job_definition_arn" {
  description = "ARN of the Python job definition"
  value       = module.batch.ml_python_job_definition_arn
}

output "ml_notebook_job_definition" {
  description = "Batch job definition for Jupyter notebooks"
  value       = module.batch.ml_notebook_job_definition_name
}

output "ml_notebook_job_definition_arn" {
  description = "ARN of the Notebook job definition"
  value       = module.batch.ml_notebook_job_definition_arn
}

###############################################################
# Lambda Function Outputs                                      #
###############################################################

output "lambda_trigger_function" {
  description = "Lambda function that triggers ML jobs"
  value       = module.lambda.lambda_function_name
}

output "lambda_trigger_function_arn" {
  description = "ARN of the Lambda trigger function"
  value       = module.lambda.lambda_function_arn
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
    upload_script   = "aws s3 cp script.py s3://${module.s3.ml_input_bucket_name}/jobs/"
    upload_notebook = "aws s3 cp notebook.ipynb s3://${module.s3.ml_input_bucket_name}/notebooks/"
    view_logs       = "aws logs tail /aws/batch/${var.project_name}-ml-jobs --follow"
    download_results = "aws s3 sync s3://${module.s3.ml_output_bucket_name}/results/ ./results/"
  }
}
