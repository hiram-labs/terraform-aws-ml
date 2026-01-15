# GPU-Accelerated ML Pipeline

Production-grade AWS infrastructure for running ML scripts and Jupyter notebooks on GPU instances with automatic S3 integration.

## Overview

Drop Python scripts or Jupyter notebooks into S3 → automatically run on GPU → results saved back to S3.

**Architecture**:
```
S3 Input → Lambda Trigger → AWS Batch (GPU) → S3 Output
                              ↓
                         CloudWatch Logs
                              ↓
                         SNS Notifications
```

**Features**:
- GPU instances (g4dn, g5, p3 families)
- Auto-scaling compute environment (0-256 vCPUs)
- Spot instances for cost savings (up to 70%)
- Pre-built containers (TensorFlow, PyTorch, CUDA 12.2)
- Automated notebook execution via Papermill
- EventBridge monitoring with SNS alerts

---

## Quick Start

### 1. Deploy Infrastructure

```bash
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Configure: VPC mode, GPU instances, container URIs (see Configuration)
terraform init
terraform apply
```

### 2. Build Docker Images

```bash
cd modules/batch/docker
./build-and-push.sh us-east-1 123456789012 my-project
# Update terraform.tfvars with output ECR URIs, then: terraform apply
```

### 3. Run ML Workload

**Python Script**:
```bash
INPUT_BUCKET=$(terraform output -raw ml_input_bucket)
aws s3 cp examples/training-script.py s3://$INPUT_BUCKET/jobs/
# Job auto-triggers!
```

**Jupyter Notebook**:
```bash
aws s3 cp examples/inference.ipynb s3://$INPUT_BUCKET/notebooks/
```

### 4. Retrieve Results

```bash
OUTPUT_BUCKET=$(terraform output -raw ml_output_bucket)
aws s3 sync s3://$OUTPUT_BUCKET/results/ ./results/
# For monitoring, see Monitoring section below
```

---

## Components

### S3 Buckets (`modules/s3`)
- **Input**: Scripts (`.py`, `.ipynb`) AND training data (CSV, parquet, etc.)
  - `jobs/` - Python scripts (auto-trigger jobs)
  - `notebooks/` - Jupyter notebooks (auto-trigger jobs)
  - `data/` - Training datasets, test data
  - `models/` - Pre-trained models, checkpoints
- **Output**: Job results, predictions, trained models
- **Models** (optional): Long-term versioned model storage

### AWS Batch (`modules/batch`)
- **Compute**: GPU instances (g4dn.xlarge, g5.xlarge, p3.2xlarge)
- **Scaling**: 0-256 vCPUs, auto-scales based on jobs
- **Cost**: Spot instances enabled (70% savings)
- **Containers**: TensorFlow, PyTorch, scikit-learn, XGBoost, CUDA 12.2

### Lambda Functions (`modules/lambda`)
- **Trigger**: S3 upload → Batch job submission
- **Monitor**: Job status tracking → SNS notifications
- **Events**: EventBridge integration for job state changes

### Docker Images (`modules/batch/docker`)
- **ml-python**: Python ML stack with GPU support (TensorFlow, PyTorch, CUDA 12.2)
- **ml-notebook**: Papermill for automated notebook execution
- Build: `./build-and-push.sh <region> <account-id> <project>` (from docker/ directory)

---

## Configuration

### Key Variables

**Infrastructure**:
```hcl
project_name = "ml-pipeline"
aws_region   = "us-east-1"

# Standalone mode
use_existing_vpc = false
vpc_id = "vpc-xxxxx"
private_subnets = ["subnet-a", "subnet-b"]

# Or integrated m (default)
use_existing_vpc = false
vpc_id           = "vpc-xxxxx"
private_subnets  = ["subnet-a", "subnet-b"]

# Integrated mode (uses existing VPC/SNS from core project)
use_existing_vpc 
ml_gpu_instance_types = ["g4dn.xlarge", "g5.xlarge"]
ml_max_vcpus = 256
ml_enable_spot_instances = true
```

**Job Resources**:
```hcl
ml_job_vcpus  = 4
ml_job_memory = 16384  # MB
ml_job_gpus   = 1
ml_job_timeout = 3600  # seconds
```

**Lambda Trigger** (important!):
```hcl
# Controls which S3 uploads trigger jobs
ml_trigger_prefix = ""        # ALL uploads trigger jobs (including data/)
# ml_trigger_prefix = "jobs/"  # Only uploads to jobs/ folder trigger jobs (recommended)
```

**Containers**:
```hcl
ml_container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-python:latest"
notebook_container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-notebook:latest"
```

---

## Example Workflows

### Working with Input Data

**Environment variables** (automatically configured in batch jobs):
- `ML_INPUT_BUCKET` - Input S3 bucket name
- `ML_OUTPUT_BUCKET` - Output S3 bucket name  
- `AWS_DEFAULT_REGION` - AWS region

**Upload training data to S3**:
```bash
INPUT_BUCKET=$(terraform output -raw ml_input_bucket)

# Upload CSV datasets
aws s3 cp train.csv s3://$INPUT_BUCKET/data/
aws s3 cp test.csv s3://$INPUT_BUCKET/data/
aws s3 sync ./datasets/ s3://$INPUT_BUCKET/data/  # Upload entire folder

# Upload pre-trained models or checkpoints
aws s3 cp pretrained_model.pth s3://$INPUT_BUCKET/models/
```

**Access data in your script**:
```python
import boto3
import os

s3 = boto3.client('s3')
input_bucket = os.environ['ML_INPUT_BUCKET']
output_bucket = os.environ['ML_OUTPUT_BUCKET']

# Download input data
s3.download_file(input_bucket, 'data/dataset.csv', '/tmp/data.csv')
s3.download_file(input_bucket, 'models/pretrained.pth', '/tmp/model.pth')

# Process data
# ... your ML code ...

# Upload results
s3.upload_file('/tmp/predictions.csv', output_bucket, 'results/predictions.csv')
```

### Training Script

Create `train.py`:
```python
import tensorflow as tf
import boto3
import os

# GPU check
print(f"GPUs: {len(tf.config.list_physical_devices('GPU'))}")

# Load training data from S3
s3 = boto3.client('s3')
input_bucket = os.environ['ML_INPUT_BUCKET']
output_bucket = os.environ['ML_OUTPUT_BUCKET']

s3.download_file(input_bucket, 'data/train.csv', '/tmp/train.csv')
# Load your data...

# Train model
model = tf.keras.Sequential([...])
model.fit(X_train, y_train)

# Save to S3
model.save('/tmp/model')
s3.upload_file('/tmp/model', output_bucket, 'models/trained.h5')
```

Upload:
```bash
aws s3 cp train.py s3://$INPUT_BUCKET/jobs/
```

### Inference Notebook

Create `inference.ipynb` with Papermill parameters:
```python
# Cell 1 (tagged as "parameters")
input_data_key = "data/test.csv"
model_key = "models/trained.pth"
output_key = "results/predictions.csv"

# Cell 2
import torch
import boto3
import os

s3 = boto3.client('s3')
input_bucket = os.environ['ML_INPUT_BUCKET']
output_bucket = os.environ['ML_OUTPUT_BUCKET']

# Download model and data
s3.download_file(input_bucket, model_key, '/tmp/model.pth')
s3.download_file(input_bucket, input_data_key, '/tmp/data.csv')

# Run inference
model = torch.load('/tmp/model.pth')
predictions = model.predict(data)

# Cell 3
# Upload results
predictions.to_csv('/tmp/predictions.csv')
s3.upload_file('/tmp/predictions.csv', output_bucket, output_key)
```

Upload:
```bash
aws s3 cp inference.ipynb s3://$INPUT_BUCKET/notebooks/
```

---

## Monitoring

### CloudWatch Logs
```bash
# Batch job logs
aws logs tail /aws/batch/ml-jobs --follow

# Lambda trigger logs
aws logs tail /aws/lambda/ml-batch-trigger --follow

# Monitor function logs
aws logs tail /aws/lambda/ml-batch-monitor --follow
```

### Job Status
```bash
# List running jobs
aws batch list-jobs --job-queue ml-job-queue --job-status RUNNING

# Describe specific job
aws batch describe-jobs --jobs <job-id>
```

### Metrics
- **CloudWatch Dashboard**: Auto-created with job metrics
- **SNS Alerts**: Success/failure notifications
- **EventBridge**: Job state change events

---

## Cost Optimization

**Development** (~$45/month):
- Idle: $0/hour (scales to zero)
- 10 jobs/day, 1 hour each
- g4dn.xlarge spot: ~$0.15/hour
- S3 storage: minimal
Estimated Costs**:
- Development: ~$45/month (10 jobs/day × 1hr × $0.15/hr spot + S3)
- Idle: $0/hour (auto-scales to zero)
- Production: Scales with usage

**Cost Controls**:
```hcl
ml_enable_spot_instances = true    # 70% savings vs on-demand
ml_max_vcpus = 256                  # Cap maximum scale
ml_job_timeout = 3600               # Prevent runaway jobs (1 hour)
```
Enable S3 lifecycle policies and CloudWatch budget alerts for production.
### Jobs Not Triggering
```bash
# Check Lambda permissions
aws lambda get-policy --function-name ml-batch-trigger

# Verify S3 event notifications
aws s3api get-bucket-notification-configuration --bucket $INPUT_BUCKET
```

### GPU Not Detected
```bash
# Check nvidia-smi in logs
aws logs filter-log-events \
  --log-group-name /aws/batch/ml-jobs \
  --filter-pattern "nvidia-smi"
```

### Out of Memory
```hcl
# Increase job memory
ml_job_memory = 32768  # 32GB
```

### Jobs Timing Out
```hcl
# Increase timeout
ml_job_timeout = 7200  # 2 hours
```

---

## Outputs

After deployment:
```bash
terraform output
```

**Available outputs**:
- `ml_input_bucket` - Upload scripts/notebooks here
- `ml_output_bucket` - Results saved here
- `ml_models_bucket` - Model storage
- `batch_compute_environment` - Compute env ARN
- `batch_job_queue` - Job queue ARN
- `sns_topic_arn` - Notification topic

## Cleanup

```bash
# Remove all ML pipeline resources
terraform destroy -target=module.ml_s3 \
                  -target=module.batch \
                  -target=module.lambda

# Or destroy everything
terraform destroy
```
terraform destroy  # Removes all resources