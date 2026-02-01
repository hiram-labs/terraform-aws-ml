output "ml_input_bucket_name" {
  description = "Name of the ML input bucket"
  value       = aws_s3_bucket.ml_input_bucket.id
}

output "ml_input_bucket_arn" {
  description = "ARN of the ML input bucket"
  value       = aws_s3_bucket.ml_input_bucket.arn
}

output "ml_output_bucket_name" {
  description = "Name of the ML output bucket"
  value       = aws_s3_bucket.ml_output_bucket.id
}

output "ml_output_bucket_arn" {
  description = "ARN of the ML output bucket"
  value       = aws_s3_bucket.ml_output_bucket.arn
}

output "ml_models_bucket_name" {
  description = "Name of the ML models bucket"
  value       = aws_s3_bucket.ml_models_bucket.id
}

output "ml_models_bucket_arn" {
  description = "ARN of the ML models bucket"
  value       = aws_s3_bucket.ml_models_bucket.arn
}
