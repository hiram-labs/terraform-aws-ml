# GPU-Accelerated ML Pipeline

AWS infrastructure for running ML workloads on GPU instances with SNS-based event triggering.

## Architecture

Each AWS service is managed by a dedicated Terraform module for consistency and maintainability:

- **VPC Module** (`modules/vpc`) - Networking with public subnets (auto-assign public IP enabled)
- **SNS Module** (`modules/sns`) - Event topics for triggering and notifications
- **S3 Module** (`modules/s3`) - Data buckets for inputs, outputs, and models
- **Batch Module** (`modules/batch`) - GPU and CPU compute environments
- **Lambda Module** (`modules/lambda`) - Event dispatcher with compute routing and monitoring

All modules are orchestrated from the root configuration.

**Key Features:**
- **Automatic VPC creation** - Public subnets with internet gateway (no NAT gateway required)
- **GPU compute** (g4dn, g5 families) - TensorFlow 2.15 + PyTorch 2.1 + CUDA 12.2
- **CPU compute** - t3, m5 instances for non-GPU workloads
- **Auto-scaling** - Both GPU and CPU scale to zero when idle (no cost)
- **Spot instances** - Optional for both GPU and CPU (70% cost savings)
- **Dynamic routing** - Route jobs to GPU or CPU based on `compute_type` parameter
- **Configurable defaults** - Set default vCPUs/memory/GPUs in Terraform, override per-job
- **Event-driven triggers** - SNS-based job submission with pluggable architecture
- **Error handling** - Dead letter queues for both dispatcher and monitor failures
- **Email notifications** - Configurable SNS email subscriptions for job status alerts

## Quick Start

### 1. Initialize Terraform Backend

```bash
export PROJECT_NAME="ml-pipeline"
export AWS_REGION="us-east-1"

aws s3 mb s3://${PROJECT_NAME}-terraform-state --region $AWS_REGION
aws s3api put-bucket-versioning --bucket ${PROJECT_NAME}-terraform-state \
  --versioning-configuration Status=Enabled --region $AWS_REGION

aws dynamodb create-table --table-name ${PROJECT_NAME}-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region $AWS_REGION
```

All AWS resources including VPC, subnets, SNS topics, S3 buckets, Lambda functions, and Batch infrastructure are created automatically.

### 2. Deploy Infrastructure

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings (VPC is created automatically)

terraform init -backend-config="bucket=${PROJECT_NAME}-terraform-state" \
  -backend-config="dynamodb_table=${PROJECT_NAME}-terraform-lock" \
  -backend-config="region=$AWS_REGION"

terraform apply
```

### 3. Build and Push Container Image

Choose which container image to build:

**Option A: Slim Python Image (Fast - ~2 minutes)**
Minimal Python 3.11 with FFmpeg, PyTorch CPU, faster-whisper, and pyannote.audio - perfect for video processing and transcription jobs:

```bash
cd modules/batch/docker
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME ml-python-slim
cd $OLDPWD

# Copy the ECR URI from output
```

**Option B: Full GPU Image (Slow - ~15-20 minutes)**
Heavy container with CUDA, TensorFlow 2.15, PyTorch 2.1 - for GPU training/inference:

```bash
cd modules/batch/docker
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME ml-python
cd $OLDPWD

# Copy the ECR URI from output
```

**Option C: Build All Images (takes ~20-25 minutes total)**

```bash
cd modules/batch/docker
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME
cd $OLDPWD
# Choose which one to use
```

Then update `terraform.tfvars` with the ECR image URI and apply:

```bash
# Edit terraform.tfvars
ml_container_image = "<ECR_URI_from_build_output>"

terraform apply
```

### 4. Confirm Email Notifications

Check your email for an SNS subscription confirmation from AWS and click the confirmation link to activate job notifications.

## EC2 GPU Quotas (Required for GPU Jobs)

AWS Batch can only launch GPU instances if your account has enough EC2 vCPU quota for the GPU instance family in the target region.

**Important:** Quota increases cannot be managed by Terraform. You must request them via AWS Service Quotas (console) or the AWS CLI.

### Request via Console
1. Open **Service Quotas → AWS services → Amazon Elastic Compute Cloud (Amazon EC2)**.
2. Search for the relevant quota:
   - **Running On-Demand G and VT instances** (for g4dn/g5 on-demand)
   - **All G and VT Spot Instances** (for g4dn/g5 spot)
3. Click **Request quota increase** and submit the desired vCPU limit.

### Request via CLI
Use the AWS CLI to look up the quota code and request an increase:

```bash
# List EC2 quotas and find the quota code for G/VT On-Demand or Spot
aws service-quotas list-service-quotas --service-code ec2 --region "$AWS_REGION" \
  --query 'Quotas[?contains(QuotaName, `G and VT`)].{Name:QuotaName,Code:QuotaCode,Value:Value}'

# Request both On-Demand and Spot GPU quotas with a fixed desired vCPU value
DESIRED_VALUE=256

# Hardcoded quota codes (these are the same across all AWS accounts)
ON_DEMAND_QUOTA_CODE="L-DB2E81BA"  # Running On-Demand G and VT instances
SPOT_QUOTA_CODE="L-3819A6DF"       # All G and VT Spot Instance Requests

aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code "$ON_DEMAND_QUOTA_CODE" \
  --desired-value "$DESIRED_VALUE" \
  --region "$AWS_REGION"

aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code "$SPOT_QUOTA_CODE" \
  --desired-value "$DESIRED_VALUE" \
  --region "$AWS_REGION"
```

Once approved, AWS Batch will be able to launch GPU instances and your jobs will move from `RUNNABLE` to `STARTING`/`RUNNING`.

## Configuration

Customize defaults and settings in `terraform.tfvars`:

**GPU Defaults:**
- `ml_gpu_job_vcpus` - Default vCPUs for GPU jobs (default: 4)
- `ml_gpu_job_memory` - Default memory in MB (default: 16384)
- `ml_gpu_job_gpus` - Default GPU count (default: 1)
- `ml_gpu_use_spot_instances` - Use spot instances (default: true)

**CPU Defaults:**
- `ml_cpu_job_vcpus` - Default vCPUs for CPU jobs (default: 2)
- `ml_cpu_job_memory` - Default memory in MB (default: 4096)
- `ml_cpu_use_spot_instances` - Use spot instances (default: true)

**Notifications:**
- `notification_emails` - List of emails for job status alerts

See [terraform.tfvars.example](terraform.tfvars.example) for complete template and [variables.tf](variables.tf) for all options.

## Writing ML Scripts

### Add Your Job Script

1. **Upload script to S3:**
```bash
INPUT_BUCKET=$(terraform output -raw ml_input_bucket)
aws s3 cp my_training_script.py s3://$INPUT_BUCKET/jobs/train.py
```

2. **Available environment variables:**
   - `ML_INPUT_BUCKET` - Input and script bucket
   - `ML_OUTPUT_BUCKET` - Results bucket
   - `OUTPUT_PREFIX` - Job-specific output path
   - `COMPUTE_TYPE` - Job type (gpu/cpu)
   - `TRIGGER_USER`, `TRIGGER_PROJECT`, `TRIGGER_EXPERIMENT` - Metadata
   - `AWS_DEFAULT_REGION` - AWS region

3. **Save outputs:**
   - Write files to `/workspace/output/` - automatically uploaded to S3

4. **Examples:**
   - [examples/gpu_training.py](examples/gpu_training.py) - GPU training
   - [examples/gpu_inference.py](examples/gpu_inference.py) - GPU inference
   - [examples/cpu_processing.py](examples/cpu_processing.py) - CPU processing

## Triggering Jobs

Get the SNS topic ARN:
```bash
TOPIC_ARN=$(terraform output -raw trigger_events_topic_arn)
```

### GPU Job (Default Resources)

Uses defaults from terraform.tfvars (e.g., 4 vCPU, 16GB, 1 GPU):

```bash
aws sns publish --topic-arn "$TOPIC_ARN" --message '{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/gpu_processing.py"
  },
  "metadata": {
    "user": "ml-engineer",
    "project": "model-training"
  }
}' --region "$AWS_REGION"
```

### GPU Job (Custom Resources)

Override defaults for larger jobs:

```bash
aws sns publish --topic-arn "$TOPIC_ARN" --message '{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/gpu_processing.py",
    "vcpus": 16,
    "memory": 65536,
    "gpus": 4
  },
  "metadata": {
    "user": "ml-engineer",
    "project": "model-training"
  }
}' --region "$AWS_REGION"
```

### CPU Job (Default Resources)

Uses defaults from terraform.tfvars (e.g., 2 vCPU, 4GB):

```bash
aws sns publish --topic-arn "$TOPIC_ARN" --message '{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/cpu_processing.py",
    "compute_type": "cpu"
  },
  "metadata": {
    "user": "ml-engineer",
    "project": "data-pipeline"
  }
}'
```

### CPU Job (Custom Resources)

Override defaults for heavy processing:

```bash
aws sns publish --topic-arn "$TOPIC_ARN" --message '{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/cpu_processing.py",
    "compute_type": "cpu",
    "vcpus": 8,
    "memory": 16384
  },
  "metadata": {
    "user": "ml-engineer",
    "project": "data-pipeline"
  }
}'
```

## Monitoring

### Email Notifications

Configured emails receive alerts for:
- Job completions (SUCCESS/FAILED)
- Monitor Lambda failures (via DLQ)

### Email Notifications

Configured emails receive alerts for:
- Job completions (SUCCESS/FAILED)
- Monitor Lambda failures (via DLQ)

### Logs and Debugging

**Lambda Logs:**
```bash
# Trigger dispatcher
aws logs tail /aws/lambda/${PROJECT_NAME}-ml-trigger-dispatcher --follow

# Job monitor
aws logs tail /aws/lambda/${PROJECT_NAME}-ml-job-monitor --follow
```

**Batch Jobs:**
```bash
# List running jobs
aws batch list-jobs --job-queue ${PROJECT_NAME}-ml-gpu-job-queue --job-status RUNNING --region $AWS_REGION
aws batch list-jobs --job-queue ${PROJECT_NAME}-ml-cpu-job-queue --job-status RUNNING --region $AWS_REGION

# View job logs
aws logs tail /aws/batch/${PROJECT_NAME}-ml-jobs --follow
```

**Dead Letter Queues:**
```bash
# Check failed dispatcher messages
DLQ_URL=$(terraform output -raw trigger_dlq_url)
aws sqs receive-message --queue-url "$DLQ_URL" --max-number-of-messages 10

# Check failed monitor events
MONITOR_DLQ_URL=$(terraform output -raw monitor_dlq_url)
aws sqs receive-message --queue-url "$MONITOR_DLQ_URL" --max-number-of-messages 10
```

**Terminate Stuck Jobs:**
```bash
# Terminate a specific job
aws batch terminate-job --job-id <JOB_ID> --reason "Manual termination" --region $AWS_REGION
```

## Cost

- **Idle:** $0/hour (auto-scales to zero)
- **Development:** ~$45/month (10 jobs/day × 1hr × g4dn.xlarge spot)
- **Production:** Scales with usage (spot instances save 70%)

## Advanced: Custom Triggers

Add new trigger types by extending `BaseTrigger`:

1. Create `modules/lambda/functions/triggers/my_trigger.py`
2. Implement `execute()` method
3. Register in `dispatcher.py` `TRIGGER_REGISTRY`

See code comments for examples.

## Cleanup

### EFS Cache Management

The EFS file system caches downloaded models to avoid repeated downloads across batch jobs. Models are automatically downloaded and cached on the first job run.

To clear cached model files (stop EFS storage charges) while keeping the cache ready for reuse, trigger the cleanup job:

```bash
TOPIC_ARN=$(terraform output -raw trigger_events_topic_arn)

aws sns publish --topic-arn "$TOPIC_ARN" --message '{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/cleanup_processor.py",
    "compute_type": "cpu",
    "operation": "cleanup-cache"
  }
}' --region "$AWS_REGION"
```

The cleanup job will:
- Delete all cached models from `/opt/models`
- Log the freed space
- Keep the EFS and mount targets intact for reuse
- Models auto-download on the next job that needs them

### Full Infrastructure Cleanup

```bash
terraform destroy
```
