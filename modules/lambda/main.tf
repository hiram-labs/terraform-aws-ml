###############################################################
# SQS Dead Letter Queue for Failed Messages                   #
###############################################################
resource "aws_sqs_queue" "ml_trigger_dlq" {
  name                      = "${var.project_name}-ml-trigger-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.common_tags
}

###############################################################
# IAM Role for Lambda Trigger Dispatcher                      #
###############################################################
resource "aws_iam_role" "lambda_trigger_dispatcher_role" {
  name = "${var.project_name}-lambda-trigger-dispatcher-role"

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
  role       = aws_iam_role.lambda_trigger_dispatcher_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Batch job submission policy
resource "aws_iam_role_policy" "lambda_batch_submit" {
  name = "${var.project_name}-lambda-batch-submit"
  role = aws_iam_role.lambda_trigger_dispatcher_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "batch:DescribeJobDefinitions",
          "batch:DescribeJobQueues",
          "batch:RegisterJobDefinition",
          "batch:TagResource"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          var.batch_job_role_arn,
          var.batch_ecs_task_execution_role_arn
        ]
      }
    ]
  })
}

# SNS publish policy (for notifications and DLQ)
resource "aws_iam_role_policy" "lambda_sns_publish" {
  name = "${var.project_name}-lambda-sns-publish"
  role = aws_iam_role.lambda_trigger_dispatcher_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          var.trigger_events_topic_arn,
          var.notifications_topic_arn
        ]
      }
    ]
  })
}

# SQS send message policy (for DLQ)
resource "aws_iam_role_policy" "lambda_sqs_dlq" {
  name = "${var.project_name}-lambda-sqs-dlq"
  role = aws_iam_role.lambda_trigger_dispatcher_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.ml_trigger_dlq.arn
      }
    ]
  })
}

###############################################################
# CloudWatch Log Group for Lambda                             #
###############################################################
resource "aws_cloudwatch_log_group" "lambda_trigger_dispatcher_log" {
  name              = "/aws/lambda/${var.project_name}-ml-trigger-dispatcher"
  retention_in_days = var.log_retention_days

  tags = var.common_tags
}

###############################################################
# Lambda Function - Trigger Dispatcher                        #
###############################################################
data "archive_file" "lambda_dispatcher_zip" {
  type        = "zip"
  source_dir  = "${path.module}/functions/trigger"
  output_path = "${path.module}/functions/trigger/dispatcher.zip"
}

resource "aws_lambda_function" "trigger_dispatcher" {
  filename         = data.archive_file.lambda_dispatcher_zip.output_path
  function_name    = "${var.project_name}-ml-trigger-dispatcher"
  role             = aws_iam_role.lambda_trigger_dispatcher_role.arn
  handler          = "dispatcher.lambda_handler"
  source_code_hash = data.archive_file.lambda_dispatcher_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      BATCH_JOB_QUEUE       = var.batch_job_queue_name
      ml_gpu_job_DEFINITION = var.ml_gpu_job_definition_name
      CPU_JOB_QUEUE         = var.cpu_job_queue_name
      ml_cpu_job_DEFINITION = var.ml_cpu_job_definition_name
      ML_INPUT_BUCKET       = var.ml_input_bucket
      ML_OUTPUT_BUCKET      = var.ml_output_bucket
      ML_MODELS_BUCKET      = var.ml_models_bucket
      ENABLE_NOTIFICATIONS  = var.enable_notifications
      SNS_TOPIC_ARN         = var.notifications_topic_arn
      DLQ_URL               = aws_sqs_queue.ml_trigger_dlq.id
      DEFAULT_GPU_VCPUS     = var.default_gpu_vcpus
      DEFAULT_GPU_MEMORY    = var.default_gpu_memory
      DEFAULT_GPU_GPUS      = var.default_gpu_gpus
      DEFAULT_CPU_VCPUS     = var.default_cpu_vcpus
      DEFAULT_CPU_MEMORY    = var.default_cpu_memory
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_trigger_dispatcher_log,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_batch_submit,
    aws_iam_role_policy.lambda_sns_publish,
    aws_iam_role_policy.lambda_sqs_dlq
  ]

  tags = var.common_tags
}

###############################################################
# SNS Subscription to Lambda                                  #
###############################################################
resource "aws_sns_topic_subscription" "lambda_trigger_dispatcher" {
  topic_arn = var.trigger_events_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.trigger_dispatcher.arn
}

###############################################################
# Lambda Permission for SNS to Invoke                         #
###############################################################
resource "aws_lambda_permission" "allow_sns_invoke" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger_dispatcher.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.trigger_events_topic_arn
}

###############################################################
# IAM Role for Lambda Monitor                                 #
###############################################################
resource "aws_iam_role" "lambda_monitor_role" {
  count = var.enable_job_monitoring ? 1 : 0
  name  = "${var.project_name}-lambda-monitor-role"

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

# Monitor basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_monitor_basic_execution" {
  count      = var.enable_job_monitoring ? 1 : 0
  role       = aws_iam_role.lambda_monitor_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Monitor Batch read policy
resource "aws_iam_role_policy" "lambda_monitor_batch_read" {
  count = var.enable_job_monitoring ? 1 : 0
  name  = "${var.project_name}-lambda-monitor-batch-read"
  role  = aws_iam_role.lambda_monitor_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "batch:DescribeJobs"
        ]
        Resource = "*"
      }
    ]
  })
}

# Monitor SNS publish policy
resource "aws_iam_role_policy" "lambda_monitor_sns_publish" {
  count = var.enable_job_monitoring ? 1 : 0
  name  = "${var.project_name}-lambda-monitor-sns-publish"
  role  = aws_iam_role.lambda_monitor_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.notifications_topic_arn
      }
    ]
  })
}

# Monitor SQS DLQ policy for failed events
resource "aws_iam_role_policy" "lambda_monitor_sqs_dlq" {
  count = var.enable_job_monitoring ? 1 : 0
  name  = "${var.project_name}-lambda-monitor-sqs-dlq"
  role  = aws_iam_role.lambda_monitor_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.ml_trigger_dlq.arn
      }
    ]
  })
}

###############################################################
# Lambda Function for Job Status Monitoring (Optional)        #
###############################################################
resource "aws_cloudwatch_log_group" "lambda_monitor_log" {
  count             = var.enable_job_monitoring ? 1 : 0
  name              = "/aws/lambda/${var.project_name}-ml-batch-monitor"
  retention_in_days = var.log_retention_days

  tags = var.common_tags
}

data "archive_file" "lambda_monitor_zip" {
  count       = var.enable_job_monitoring ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/functions/monitor/monitor.py"
  output_path = "${path.module}/functions/monitor/monitor.zip"
}

resource "aws_lambda_function" "batch_job_monitor" {
  count            = var.enable_job_monitoring ? 1 : 0
  filename         = data.archive_file.lambda_monitor_zip[0].output_path
  function_name    = "${var.project_name}-ml-batch-monitor"
  role             = aws_iam_role.lambda_monitor_role[0].arn
  handler          = "monitor.lambda_handler"
  source_code_hash = data.archive_file.lambda_monitor_zip[0].output_base64sha256
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      SNS_TOPIC_ARN = var.notifications_topic_arn
      DLQ_URL       = aws_sqs_queue.ml_trigger_dlq.id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_monitor_log,
    aws_iam_role_policy_attachment.lambda_monitor_basic_execution,
    aws_iam_role_policy.lambda_monitor_batch_read,
    aws_iam_role_policy.lambda_monitor_sns_publish,
    aws_iam_role_policy.lambda_monitor_sqs_dlq
  ]

  tags = var.common_tags
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

  dead_letter_config {
    arn = aws_sqs_queue.ml_trigger_dlq.arn
  }
}

resource "aws_lambda_permission" "allow_eventbridge_invoke" {
  count         = var.enable_job_monitoring ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_job_monitor[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.batch_job_state_change[0].arn
}

###############################################################
# Data Source for AWS Account ID                              #
###############################################################
data "aws_caller_identity" "current" {}
