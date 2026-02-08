output "batch_compute_environment_arn" {
  description = "ARN of the Batch compute environment"
  value       = aws_batch_compute_environment.gpu_compute_env.arn
}

output "gpu_job_queue_arn" {
  description = "ARN of the GPU Batch job queue"
  value       = aws_batch_job_queue.ml_job_queue.arn
}

output "gpu_job_queue_name" {
  description = "Name of the GPU Batch job queue"
  value       = aws_batch_job_queue.ml_job_queue.name
}

output "ml_gpu_job_definition_arn" {
  description = "ARN of the ML Python job definition"
  value       = aws_batch_job_definition.ml_gpu_job.arn
}

output "ml_gpu_job_definition_name" {
  description = "Name of the ML Python job definition"
  value       = aws_batch_job_definition.ml_gpu_job.name
}

output "batch_job_role_arn" {
  description = "ARN of the Batch job execution role"
  value       = aws_iam_role.batch_job_role.arn
}

output "batch_job_role_name" {
  description = "Name of the Batch job execution role"
  value       = aws_iam_role.batch_job_role.name
}

output "batch_ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role for Batch jobs"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "batch_log_group_name" {
  description = "Name of the CloudWatch log group for Batch jobs"
  value       = aws_cloudwatch_log_group.batch_jobs_log_group.name
}

output "batch_security_group_id" {
  description = "Security group ID for Batch compute environment"
  value       = aws_security_group.batch_compute_sg.id
}
###############################################################
# CPU Compute Resources (Always Available - Scales to Zero)   #
###############################################################

output "cpu_compute_environment_arn" {
  description = "ARN of the CPU-only Batch compute environment"
  value       = aws_batch_compute_environment.cpu_compute_env.arn
}

output "cpu_job_queue_arn" {
  description = "ARN of the CPU job queue"
  value       = aws_batch_job_queue.cpu_job_queue.arn
}

output "cpu_job_queue_name" {
  description = "Name of the CPU job queue"
  value       = aws_batch_job_queue.cpu_job_queue.name
}

output "ml_cpu_job_definition_arn" {
  description = "ARN of the ML Python CPU job definition"
  value       = aws_batch_job_definition.ml_cpu_job.arn
}

output "ml_cpu_job_definition_name" {
  description = "Name of the ML Python CPU job definition"
  value       = aws_batch_job_definition.ml_cpu_job.name
}