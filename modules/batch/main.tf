###############################################################
# AWS Batch for GPU-Accelerated ML Workloads                 #
#                                                             #
# Provides scalable compute environment for running ML        #
# training and inference jobs with GPU acceleration.          #
#                                                             #
# Features:                                                   #
# - GPU-optimized EC2 instances (P3, P4, G4, G5 families)     #
# - Auto-scaling based on job queue demand                    #
# - Spot instance support for cost optimization               #
# - Integration with ECR for custom ML containers             #
# - CloudWatch logging for job monitoring                     #
###############################################################

###############################################################
# IAM Role for Batch Service                                  #
###############################################################
resource "aws_iam_role" "batch_service_role" {
  name = "${var.project_name}-batch-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "batch.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "batch_service_policy" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

###############################################################
# IAM Role for ECS Task Execution (Batch Jobs)                #
###############################################################
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-batch-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

###############################################################
# IAM Role for Batch Job Execution                            #
# Allows jobs to access S3, CloudWatch, and other services    #
###############################################################
resource "aws_iam_role" "batch_job_role" {
  name = "${var.project_name}-batch-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

# Policy for S3 access (read inputs, write outputs, read models)
resource "aws_iam_role_policy" "batch_job_s3_policy" {
  name = "${var.project_name}-batch-job-s3-policy"
  role = aws_iam_role.batch_job_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.ml_input_bucket}/*",
          "arn:aws:s3:::${var.ml_output_bucket}/*",
          "arn:aws:s3:::${var.ml_models_bucket}/*",
          "arn:aws:s3:::${var.ml_vault_bucket}/*",
          "arn:aws:s3:::${var.ml_input_bucket}",
          "arn:aws:s3:::${var.ml_output_bucket}",
          "arn:aws:s3:::${var.ml_models_bucket}",
          "arn:aws:s3:::${var.ml_vault_bucket}"
        ]
      }
    ]
  })
}

# Policy for CloudWatch Logs
resource "aws_iam_role_policy" "batch_job_logs_policy" {
  name = "${var.project_name}-batch-job-logs-policy"
  role = aws_iam_role.batch_job_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

###############################################################
# IAM Instance Profile for EC2 Instances                      #
###############################################################
resource "aws_iam_role" "ecs_instance_role" {
  name = "${var.project_name}-batch-ecs-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_instance_policy" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "${var.project_name}-batch-ecs-instance-profile"
  role = aws_iam_role.ecs_instance_role.name

  tags = var.common_tags
}

###############################################################
# Security Group for Batch Compute Environment                #
###############################################################
resource "aws_security_group" "batch_compute_sg" {
  name        = "${var.project_name}-batch-compute-sg"
  description = "Security group for Batch compute environment"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic for pulling images and accessing S3"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-batch-compute-sg"
    }
  )
}

###############################################################
# Launch Template for GPU Instances                           #
###############################################################
resource "aws_launch_template" "batch_gpu_lt" {
  name_prefix = "${var.project_name}-batch-gpu-"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  iam_instance_profile {
    arn = aws_iam_instance_profile.ecs_instance_profile.arn
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(
      var.common_tags,
      {
        Name = "${var.project_name}-batch-gpu-instance"
      }
    )
  }

  tags = var.common_tags
}

###############################################################
# Batch Compute Environment - GPU Optimized                   #
###############################################################
resource "aws_batch_compute_environment" "gpu_compute_env" {
  compute_environment_name_prefix = "${var.project_name}-ml-gpu-"
  type                            = "MANAGED"
  state                           = "ENABLED"
  service_role                    = aws_iam_role.batch_service_role.arn

  compute_resources {
    type                = var.use_spot_instances ? "SPOT" : "EC2"
    allocation_strategy = var.use_spot_instances ? "SPOT_CAPACITY_OPTIMIZED" : "BEST_FIT_PROGRESSIVE"

    min_vcpus     = var.min_vcpus
    max_vcpus     = var.max_vcpus
    desired_vcpus = var.desired_vcpus

    instance_role = aws_iam_instance_profile.ecs_instance_profile.arn
    instance_type = var.gpu_instance_types

    security_group_ids = [aws_security_group.batch_compute_sg.id]
    subnets            = var.private_subnets

    dynamic "ec2_configuration" {
      for_each = var.use_spot_instances ? [] : [1]
      content {
        image_type = "ECS_AL2_NVIDIA"
      }
    }

    dynamic "ec2_configuration" {
      for_each = var.use_spot_instances ? [1] : []
      content {
        image_type = "ECS_AL2_NVIDIA"
      }
    }

    spot_iam_fleet_role = var.use_spot_instances ? aws_iam_role.spot_fleet_role[0].arn : null
    bid_percentage      = var.use_spot_instances ? var.spot_bid_percentage : null

    tags = merge(
      var.common_tags,
      {
        Name = "${var.project_name}-batch-gpu-compute"
      }
    )
  }

  depends_on = [aws_iam_role_policy_attachment.batch_service_policy]

  lifecycle {
    create_before_destroy = true
  }

  tags = var.common_tags
}

###############################################################
# Spot Fleet IAM Role - GPU (Conditional)                     #
###############################################################
resource "aws_iam_role" "spot_fleet_role" {
  count = var.use_spot_instances ? 1 : 0
  name  = "${var.project_name}-batch-spot-fleet-role-gpu"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "spotfleet.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "spot_fleet_policy" {
  count      = var.use_spot_instances ? 1 : 0
  role       = aws_iam_role.spot_fleet_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

###############################################################
# Spot Fleet IAM Role - CPU (Conditional)                     #
###############################################################
resource "aws_iam_role" "spot_fleet_role_cpu" {
  count = var.cpu_use_spot_instances ? 1 : 0
  name  = "${var.project_name}-batch-spot-fleet-role-cpu"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "spotfleet.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "spot_fleet_policy_cpu" {
  count      = var.cpu_use_spot_instances ? 1 : 0
  role       = aws_iam_role.spot_fleet_role_cpu[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

###############################################################
# Batch Job Queue - High Priority for ML Jobs                 #
###############################################################
resource "aws_batch_job_queue" "ml_job_queue" {
  name     = "${var.project_name}-ml-gpu-job-queue"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.gpu_compute_env.arn
  }

  depends_on = [aws_batch_compute_environment.gpu_compute_env]

  tags = var.common_tags
}

###############################################################
# CloudWatch Log Group for Batch Jobs                         #
###############################################################
resource "aws_cloudwatch_log_group" "batch_jobs_log_group" {
  name              = "/aws/batch/${var.project_name}-ml-jobs"
  retention_in_days = var.log_retention_days

  tags = var.common_tags
}

###############################################################
# Batch Job Definition - Python ML Workload (GPU)             #
###############################################################
resource "aws_batch_job_definition" "ml_gpu_job" {
  name = "${var.project_name}-ml-gpu-job"
  type = "container"

  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image = var.ml_gpu_container_image

    resourceRequirements = [
      {
        type  = "VCPU"
        value = tostring(var.job_vcpus)
      },
      {
        type  = "MEMORY"
        value = tostring(var.job_memory)
      },
      {
        type  = "GPU"
        value = tostring(var.job_gpus)
      }
    ]

    jobRoleArn       = aws_iam_role.batch_job_role.arn
    executionRoleArn = aws_iam_role.ecs_task_execution_role.arn

    environment = [
      {
        name  = "AWS_DEFAULT_REGION"
        value = var.aws_region
      },
      {
        name  = "ML_INPUT_BUCKET"
        value = var.ml_input_bucket
      },
      {
        name  = "ML_OUTPUT_BUCKET"
        value = var.ml_output_bucket
      },
      {
        name  = "ML_MODELS_BUCKET"
        value = var.ml_models_bucket
      },
      {
        name  = "ML_VAULT_BUCKET"
        value = var.ml_vault_bucket
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.batch_jobs_log_group.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ml-job"
      }
    }

    linuxParameters = {
      devices = [
        {
          hostPath      = "/dev/nvidia0"
          containerPath = "/dev/nvidia0"
          permissions   = ["READ", "WRITE", "MKNOD"]
        },
        {
          hostPath      = "/dev/nvidiactl"
          containerPath = "/dev/nvidiactl"
          permissions   = ["READ", "WRITE", "MKNOD"]
        },
        {
          hostPath      = "/dev/nvidia-uvm"
          containerPath = "/dev/nvidia-uvm"
          permissions   = ["READ", "WRITE", "MKNOD"]
        }
      ]
    }

    mountPoints = [
      {
        sourceVolume  = "batch-cache"
        containerPath = "/opt"
        readOnly      = false
      }
    ]

    volumes = [
      {
        name = "batch-cache"
        efsVolumeConfiguration = {
          fileSystemId      = var.efs_file_system_id
          accessPointId     = var.efs_access_point_id
          transitEncryption = "ENABLED"
        }
      }
    ]
  })

  retry_strategy {
    attempts = var.job_retry_attempts
    evaluate_on_exit {
      action           = "RETRY"
      on_status_reason = "Task failed to start"
    }
    evaluate_on_exit {
      action           = "EXIT"
      on_status_reason = "Essential container in task exited"
    }
  }

  timeout {
    attempt_duration_seconds = var.job_timeout_seconds
  }

  tags = var.common_tags
}

###############################################################
# Launch Template for CPU Instances                           #
###############################################################
resource "aws_launch_template" "batch_cpu_lt" {
  name_prefix = "${var.project_name}-batch-cpu-"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  iam_instance_profile {
    arn = aws_iam_instance_profile.ecs_instance_profile.arn
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(
      var.common_tags,
      {
        Name = "${var.project_name}-batch-cpu-instance"
      }
    )
  }

  tags = var.common_tags
}

###############################################################
# Batch Compute Environment                                   #
###############################################################
resource "aws_batch_compute_environment" "cpu_compute_env" {
  compute_environment_name_prefix = "${var.project_name}-ml-cpu-"
  type                            = "MANAGED"
  state                           = "ENABLED"
  service_role                    = aws_iam_role.batch_service_role.arn

  compute_resources {
    type                = var.cpu_use_spot_instances ? "SPOT" : "EC2"
    allocation_strategy = var.cpu_use_spot_instances ? "SPOT_CAPACITY_OPTIMIZED" : "BEST_FIT_PROGRESSIVE"

    min_vcpus     = var.cpu_min_vcpus
    max_vcpus     = var.cpu_max_vcpus
    desired_vcpus = var.cpu_desired_vcpus

    instance_role = aws_iam_instance_profile.ecs_instance_profile.arn
    instance_type = var.cpu_instance_types

    security_group_ids = [aws_security_group.batch_compute_sg.id]
    subnets            = var.private_subnets

    launch_template {
      launch_template_id = aws_launch_template.batch_cpu_lt.id
      version            = "$Latest"
    }

    ec2_configuration {
      image_type = "ECS_AL2"
    }

    spot_iam_fleet_role = var.cpu_use_spot_instances ? aws_iam_role.spot_fleet_role_cpu[0].arn : null
    bid_percentage      = var.cpu_use_spot_instances ? var.spot_bid_percentage : null

    tags = merge(
      var.common_tags,
      {
        Name = "${var.project_name}-batch-cpu-compute"
      }
    )
  }

  depends_on = [aws_iam_role_policy_attachment.batch_service_policy]

  lifecycle {
    create_before_destroy = true
  }

  tags = var.common_tags
}

###############################################################
# Batch Job Queue - CPU for Non-GPU Workloads (Optional)      #
###############################################################
resource "aws_batch_job_queue" "cpu_job_queue" {
  name     = "${var.project_name}-ml-cpu-job-queue"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.cpu_compute_env.arn
  }

  depends_on = [aws_batch_compute_environment.cpu_compute_env]

  tags = var.common_tags
}

###############################################################
# Batch Job Definition - CPU (No GPU)                         #
###############################################################
resource "aws_batch_job_definition" "ml_cpu_job" {
  name = "${var.project_name}-ml-cpu-job"
  type = "container"

  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image = var.ml_cpu_container_image

    resourceRequirements = [
      {
        type  = "VCPU"
        value = tostring(var.cpu_job_vcpus)
      },
      {
        type  = "MEMORY"
        value = tostring(var.cpu_job_memory)
      }
    ]

    jobRoleArn       = aws_iam_role.batch_job_role.arn
    executionRoleArn = aws_iam_role.ecs_task_execution_role.arn

    environment = [
      {
        name  = "AWS_DEFAULT_REGION"
        value = var.aws_region
      },
      {
        name  = "ML_INPUT_BUCKET"
        value = var.ml_input_bucket
      },
      {
        name  = "ML_OUTPUT_BUCKET"
        value = var.ml_output_bucket
      },
      {
        name  = "ML_MODELS_BUCKET"
        value = var.ml_models_bucket
      },
      {
        name  = "ML_VAULT_BUCKET"
        value = var.ml_vault_bucket
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.batch_jobs_log_group.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ml-cpu-job"
      }
    }

    mountPoints = [
      {
        sourceVolume  = "batch-cache"
        containerPath = "/opt"
        readOnly      = false
      }
    ]

    volumes = [
      {
        name = "batch-cache"
        efsVolumeConfiguration = {
          fileSystemId      = var.efs_file_system_id
          accessPointId     = var.efs_access_point_id
          transitEncryption = "ENABLED"
        }
      }
    ]
  })

  timeout {
    attempt_duration_seconds = var.job_timeout_seconds
  }

  tags = var.common_tags
}
