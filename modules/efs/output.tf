output "efs_file_system_id" {
  description = "EFS file system ID for model cache"
  value       = aws_efs_file_system.batch_cache.id
}

output "efs_file_system_arn" {
  description = "EFS file system ARN for model cache"
  value       = aws_efs_file_system.batch_cache.arn
}

output "efs_access_point_id" {
  description = "EFS access point ID for model cache"
  value       = aws_efs_access_point.batch_cache.id
}
