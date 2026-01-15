# GPU-Accelerated ML Pipeline

AWS infrastructure for running ML workloads on GPU instances with S3 integration.

## Architecture

```
S3 Upload → Lambda → AWS Batch (GPU) → S3 Results
```

**Features:**
- GPU compute (g4dn, g5 families) with auto-scaling (0-256 vCPUs)
- Spot instances (70% cost savings)
- TensorFlow 2.15 + PyTorch 2.1 + CUDA 12.2
- Automated notebook execution via Papermill
- SNS notifications for job status

---

## Deployment

### 0. Set Environment Variables

```bash
export PROJECT_NAME="ml-pipeline"
export AWS_REGION="us-east-1"
export ENVIRONMENT="dev"
```

### 1. State Backend Setup

```bash
# Create state bucket and lock table
aws s3 mb s3://${PROJECT_NAME}-${ENVIRONMENT}-terraform-state --region $AWS_REGION
aws s3api put-bucket-versioning \
  --bucket ${PROJECT_NAME}-${ENVIRONMENT}-terraform-state \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name ${PROJECT_NAME}-${ENVIRONMENT}-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $AWS_REGION
```

### 2. Configure and Deploy

```bash
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Update: vpc_id, subnets, sns_topic_arn, region

terraform init \
  -backend-config="bucket=${PROJECT_NAME}-${ENVIRONMENT}-terraform-state" \
  -backend-config="dynamodb_table=${PROJECT_NAME}-${ENVIRONMENT}-terraform-lock" \
  -backend-config="region=$AWS_REGION"

terraform apply
```

### 3. Build Container Images

```bash
cd modules/batch/docker
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME
cd $OLDPWD
```

Update `terraform.tfvars` with the ECR URIs shown in output, then:
```bash
cd ../../..
terraform apply
```

---

## Usage

### Running Jobs

```bash
INPUT_BUCKET=$(terraform output -raw ml_input_bucket)

# Python script (auto-triggers job)
aws s3 cp train.py s3://$INPUT_BUCKET/jobs/

# Jupyter notebook (auto-triggers job)
aws s3 cp inference.ipynb s3://$INPUT_BUCKET/notebooks/

# Retrieve results
OUTPUT_BUCKET=$(terraform output -raw ml_output_bucket)
aws s3 sync s3://$OUTPUT_BUCKET/results/ ./results/
```

### Python Script Example

```python
import torch
import boto3
import os

# GPU check
print(f"CUDA: {torch.cuda.is_available()}, GPUs: {torch.cuda.device_count()}")

# S3 access
s3 = boto3.client('s3')
input_bucket = os.environ['ML_INPUT_BUCKET']
output_bucket = os.environ['ML_OUTPUT_BUCKET']

# Download data
s3.download_file(input_bucket, 'data/train.csv', '/tmp/train.csv')

# Train model
device = torch.device('cuda')
model = YourModel().to(device)
# ... training code ...

# Save results
torch.save(model.state_dict(), '/tmp/model.pth')
s3.upload_file('/tmp/model.pth', output_bucket, 'models/trained.pth')
```

### Environment Variables (Auto-configured)

- `ML_INPUT_BUCKET` - Input bucket name
- `ML_OUTPUT_BUCKET` - Output bucket name
- `AWS_DEFAULT_REGION` - AWS region

---

## Configuration

### Key Variables (`terraform.tfvars`)

```hcl
project_name = "ml-pipeline"
aws_region   = "us-east-1"

vpc_id          = "vpc-xxxxx"
private_subnets = ["subnet-a", "subnet-b", "subnet-c"]
sns_topic_arn   = "arn:aws:sns:REGION:ACCOUNT_ID:alerts"

ml_container_image       = "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/PROJECT-ml-python:latest"
notebook_container_image = "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/PROJECT-ml-notebook:latest"

ml_gpu_instance_types = ["g4dn.xlarge", "g5.xlarge"]
ml_use_spot_instances = true
ml_max_vcpus          = 256

ml_job_vcpus  = 4
ml_job_memory = 16384  # MiB
ml_job_gpus   = 1

ml_trigger_prefix = ""  # "" = all uploads, "jobs/" = only jobs/ folder
```

See `variables.tf` for all options.

---

## Monitoring

### Logs

```bash
# Job logs
aws logs tail /aws/batch/ml-jobs --follow

# Lambda logs
aws logs tail /aws/lambda/ml-batch-trigger --follow
aws logs tail /aws/lambda/ml-batch-monitor --follow
```

### Job Status

```bash
# List running jobs
aws batch list-jobs --job-queue ml-job-queue --job-status RUNNING

# Job details
aws batch describe-jobs --jobs <job-id>
```

---

## Troubleshooting

**Jobs not triggering:**
```bash
aws s3api get-bucket-notification-configuration --bucket $INPUT_BUCKET
```

**GPU not detected:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/batch/ml-jobs \
  --filter-pattern "nvidia-smi"
```

**Increase resources:**
```hcl
ml_job_memory = 32768  # 32GB
ml_job_vcpus  = 8
```

---

## Cost Estimates

- **Idle:** $0/hour (auto-scales to zero)
- **Development:** ~$45/month (10 jobs/day × 1hr × g4dn.xlarge spot)
- **Production:** Scales with usage

**Cost controls:**
- Spot instances enabled by default (70% savings)
- `ml_max_vcpus` caps maximum scale
- S3 lifecycle policies for data retention

---

## Cleanup

```bash
terraform destroy
```