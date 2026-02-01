# ML Container Images

This directory contains Docker images for AWS Batch jobs.

## Available Images

### ml-python-slim (Recommended for quick testing)

**Size:** ~500MB  
**Build Time:** ~2 minutes  
**Use Case:** CPU processing, data pipelines, testing

**Includes:**
- Python 3.11
- FFmpeg for video/audio processing
- PyTorch CPU (minimal)
- faster-whisper for transcription
- pyannote.audio for speaker diarization
- boto3 for S3 access

**Does NOT include:**
- CUDA drivers
- TensorFlow
- GPU support
- Data science libraries (removed for minimal size)

### ml-python (Full GPU-enabled)

**Size:** ~12GB  
**Build Time:** ~15-20 minutes  
**Use Case:** GPU training, deep learning inference

**Includes:**
- Everything from slim, plus:
- CUDA 12.1 + cuDNN 8
- PyTorch 2.1 (with CUDA support)
- TensorFlow 2.15
- XGBoost, LightGBM
- Transformers, Accelerate, Datasets
- TensorBoard, Weights & Biases, MLflow

## Building Images

### Quick Start - Build Only Slim Image

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline ml-python-slim
```

**Output:**
```
ECR URI: 123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-ml-python-slim:latest
```

### Build Full GPU Image

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline ml-python
```

### Build All Images

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline
```

## Using the Images

Update `terraform.tfvars` with the ECR URI:

```hcl
ml_container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-ml-python-slim:latest"
```

Then run:

```bash
terraform apply
```

## Customization

### Modifying Slim Image

Edit `Dockerfile.ml-python-slim` to add more Python packages:

```dockerfile
RUN pip3 install additional-library
```

Then rebuild:

```bash
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline ml-python-slim
```

### Modifying Full GPU Image

Edit `Dockerfile.ml-python` similarly and rebuild with `ml-python` option.

## Tips

- **First build:** Images are downloaded and built from scratch, so the first build takes longest
- **Subsequent builds:** Docker caches layers, so rebuilds are much faster
- **Disk space:** Full GPU image is ~12GB; ensure you have enough space
- **Network:** Initial build pulls large NVIDIA CUDA base image (~5GB); ensure good connectivity
- **Testing locally:** You can test the image locally before pushing to ECR:

```bash
docker build -f Dockerfile.ml-python-slim -t my-test-image:latest .
docker run --rm -it my-test-image:latest python3 --version
```
