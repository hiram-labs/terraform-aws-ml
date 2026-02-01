output "efs_file_system_id" {
  description = "EFS file system ID for model cache"
  value       = aws_efs_file_system.model_cache.id
}

output "efs_file_system_arn" {
  description = "EFS file system ARN for model cache"
  value       = aws_efs_file_system.model_cache.arn
}

output "efs_security_group_id" {
  description = "Security group ID for EFS"
  value       = aws_security_group.efs_sg.id
}
