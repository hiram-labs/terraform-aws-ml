# ML Container Images

This directory contains Docker images for AWS Batch jobs.

## Available Images

### ml-python-slim (Recommended for quick testing)

**Size:** ~500MB  
**Build Time:** ~2 minutes  
**Use Case:** CPU processing, data pipelines, testing

**Includes:**
- Python 3.11
- AWS CLI + boto3
- NumPy, Pandas, Scikit-learn, Scipy
- Matplotlib, Seaborn, Plotly
- Pillow, OpenCV (headless)

**Does NOT include:**
- CUDA drivers
- TensorFlow
- PyTorch
- GPU support

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
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline slim
```

**Output:**
```
ECR URI: 123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-ml-python-slim:latest
```

### Build Full GPU Image

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline full
```

### Build Both

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

Edit `ml-python-slim/Dockerfile` to add more Python packages:

```dockerfile
RUN pip3 install additional-library
```

Then rebuild:

```bash
./build-and-push.sh us-east-1 $ACCOUNT_ID ml-pipeline slim
```

### Modifying Full GPU Image

Edit `ml-python/Dockerfile` similarly and rebuild with `full` option.

## Tips

- **First build:** Images are downloaded and built from scratch, so the first build takes longest
- **Subsequent builds:** Docker caches layers, so rebuilds are much faster
- **Disk space:** Full GPU image is ~12GB; ensure you have enough space
- **Network:** Initial build pulls large NVIDIA CUDA base image (~5GB); ensure good connectivity
- **Testing locally:** You can test the image locally before pushing to ECR:

```bash
docker build -f ml-python-slim/Dockerfile -t my-test-image:latest .
docker run --rm -it my-test-image:latest python3 --version
```
