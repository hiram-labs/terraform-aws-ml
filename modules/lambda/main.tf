###############################################################
# Lambda Function for ML Pipeline Orchestration              #
#                                                             #
# Triggers AWS Batch jobs when scripts or notebooks are      #
# uploaded to S3 input bucket.                                #
#                                                             #
# Features:                                                   #
# - S3 event-driven job submission                            #
# - Automatic job type detection (script vs notebook)         #
# - Job parameter customization                               #
# - Error handling and notifications                          #
###############################################################

###############################################################
# IAM Role for Lambda Function                                #
###############################################################
resource "aws_iam_role" "lambda_batch_trigger_role" {
  name = "${var.project_name}-lambda-batch-trigger-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_batch_trigger_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 read access policy
resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"
  role = aws_iam_role.lambda_batch_trigger_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectMetadata",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.ml_input_bucket}/*",
          "arn:aws:s3:::${var.ml_input_bucket}"
        ]
      }
    ]
  })
}

# Batch job submission policy
resource "aws_iam_role_policy" "lambda_batch_submit" {
  name = "${var.project_name}-lambda-batch-submit"
  role = aws_iam_role.lambda_batch_trigger_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "batch:DescribeJobDefinitions",
          "batch:DescribeJobQueues"
        ]
        Resource = "*"
      }
    ]
  })
}

# SNS publish policy (for notifications)
resource "aws_iam_role_policy" "lambda_sns_publish" {
  count = var.enable_notifications ? 1 : 0
  name  = "${var.project_name}-lambda-sns-publish"
  role  = aws_iam_role.lambda_batch_trigger_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_topic_arn
      }
    ]
  })
}

###############################################################
# CloudWatch Log Group for Lambda                             #
###############################################################
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.project_name}-ml-batch-trigger"
  retention_in_days = var.log_retention_days

  tags = var.common_tags
}

###############################################################
# Lambda Function - Batch Job Trigger                         #
###############################################################
resource "aws_lambda_function" "batch_job_trigger" {
  filename         = "${path.module}/functions/trigger/trigger_function.zip"
  function_name    = "${var.project_name}-ml-batch-trigger"
  role            = aws_iam_role.lambda_batch_trigger_role.arn
  handler         = "trigger_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      BATCH_JOB_QUEUE              = var.batch_job_queue_name
      ML_PYTHON_JOB_DEFINITION     = var.ml_python_job_definition_name
      ML_NOTEBOOK_JOB_DEFINITION   = var.ml_notebook_job_definition_name
      ML_OUTPUT_BUCKET             = var.ml_output_bucket
      ENABLE_NOTIFICATIONS         = var.enable_notifications
      SNS_TOPIC_ARN                = var.enable_notifications ? var.sns_topic_arn : ""
      DEFAULT_VCPUS                = var.default_vcpus
      DEFAULT_MEMORY               = var.default_memory
      DEFAULT_GPUS                 = var.default_gpus
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_log_group,
    aws_iam_role_policy_attachment.lambda_basic_execution
  ]

  tags = var.common_tags
}

###############################################################
# Lambda Function Source Code                                 #
###############################################################
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/functions/trigger/trigger_function.py"
  output_path = "${path.module}/functions/trigger/trigger_function.zip"
}

###############################################################
# Lambda Permission for S3 to Invoke                          #
###############################################################
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_job_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.ml_input_bucket}"
}

###############################################################
# S3 Bucket Notification Configuration                        #
###############################################################
resource "aws_s3_bucket_notification" "ml_input_notification" {
  bucket = var.ml_input_bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.batch_job_trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.input_prefix
    filter_suffix       = ""
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

###############################################################
# Lambda Function for Job Status Monitoring (Optional)        #
###############################################################
resource "aws_lambda_function" "batch_job_monitor" {
  count            = var.enable_job_monitoring ? 1 : 0
  filename         = "${path.module}/functions/monitor/monitor_function.zip"
  function_name    = "${var.project_name}-ml-batch-monitor"
  role            = aws_iam_role.lambda_batch_trigger_role.arn
  handler         = "monitor_function.lambda_handler"
  source_code_hash = data.archive_file.monitor_zip[0].output_base64sha256
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      SNS_TOPIC_ARN    = var.sns_topic_arn
      ML_OUTPUT_BUCKET = var.ml_output_bucket
    }
  }

  tags = var.common_tags
}

data "archive_file" "monitor_zip" {
  count       = var.enable_job_monitoring ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/functions/monitor/monitor_function.py"
  output_path = "${path.module}/functions/monitor/monitor_function.zip"
}

###############################################################
# EventBridge Rule for Batch Job State Changes                #
###############################################################
resource "aws_cloudwatch_event_rule" "batch_job_state_change" {
  count       = var.enable_job_monitoring ? 1 : 0
  name        = "${var.project_name}-ml-batch-job-state-change"
  description = "Capture Batch job state changes"

  event_pattern = jsonencode({
    source      = ["aws.batch"]
    detail-type = ["Batch Job State Change"]
    detail = {
      jobQueue = [var.batch_job_queue_arn]
      status   = ["SUCCEEDED", "FAILED"]
    }
  })

  tags = var.common_tags
}

resource "aws_cloudwatch_event_target" "batch_monitor_lambda" {
  count = var.enable_job_monitoring ? 1 : 0
  rule  = aws_cloudwatch_event_rule.batch_job_state_change[0].name
  arn   = aws_lambda_function.batch_job_monitor[0].arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke" {
  count         = var.enable_job_monitoring ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_job_monitor[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.batch_job_state_change[0].arn
}
