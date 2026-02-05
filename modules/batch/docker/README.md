# ML Container Images

This directory contains Docker images for AWS Batch jobs.

## Available Images

### cpu-slim (Recommended for CPU processing)

**Size:** ~500MB  
**Build Time:** ~2 minutes  
**Use Case:** CPU processing, video/audio handling, data pipelines, testing

**Includes:**
- Python 3.11
- FFmpeg for video/audio processing
- boto3 for S3 access
- Minimal dependencies

**Does NOT include:**
- CUDA drivers
- GPU support
- PyTorch/TensorFlow
- Heavy ML frameworks

### gpu-slim (Recommended for quick GPU testing)

**Size:** ~2-3GB  
**Build Time:** ~5-10 minutes  
**Use Case:** GPU inference, fast training, transcription jobs

**Includes:**
- CUDA 12.1 + cuDNN 8
- Python 3.11
- FFmpeg for video/audio processing
- PyTorch 2.1 (GPU)
- faster-whisper for transcription
- pyannote.audio for speaker diarization
- boto3 for S3 access

## Building Images

### Quick Start - Build CPU Slim Image (Fastest)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline cpu-slim
```

### Build GPU Slim Image (Recommended for GPU jobs)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline cpu-slim-slim
```

### Build Full GPU Image

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline cpu-slim
```

### Build All Images

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline
```

## Using the Images

Update `terraform.tfvars` with the ECR URI:

```hcl
ml_container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-cpu-slim:latest"
```

Then run:

```bash
terraform apply
```

## Customization

### Modifying CPU Slim Image

Edit `Dockerfile.cpu-slim` to add more Python packages:

```dockerfile
RUN pip3 install numpy pandas requests
```

Then rebuild:

```bash
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline cpu-slim
```

### Modifying GPU Slim Image

Edit `Dockerfile.cpu-slim` similarly and rebuild with `cpu-slim` option.

### Modifying Full GPU Image

Edit `Dockerfile.cpu-slim` similarly and rebuild with `cpu-slim` option.

## Tips

- **First build:** Images are downloaded and built from scratch, so the first build takes longest
- **Subsequent builds:** Docker caches layers, so rebuilds are much faster
- **Disk space:** Full GPU image is ~12GB; ensure you have enough space
- **Network:** Initial build pulls large NVIDIA CUDA base image (~5GB); ensure good connectivity
- **Testing locally:** You can test the image locally before pushing to ECR:

```bash
docker build -f Dockerfile.cpu-slim -t my-test-image:latest .
docker run --rm -it my-test-image:latest python3 --version
```
