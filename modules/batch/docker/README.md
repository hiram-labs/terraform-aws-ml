# ML Container Images

This directory contains Docker images for AWS Batch jobs.

## Building Images

Set these helper variables once per shell so the commands stay short:

```bash
export AWS_REGION=${AWS_REGION:-us-east-1}
export PROJECT_NAME=${PROJECT_NAME:-ml-pipeline}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### Build CPU Slim Image (Fastest)

```bash
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME cpu-slim
```

### Build GPU Slim Image (Recommended for GPU jobs)

```bash
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME gpu-slim
```

### Build All Images

```bash
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME
```

## Using the Images

Update `terraform.tfvars` with the ECR URIs:

```hcl
ml_gpu_container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-gpu-slim:latest"
ml_cpu_container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-cpu-slim:latest"
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
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME cpu-slim
```

### Modifying GPU Slim Image

Edit `Dockerfile.gpu-slim` to add more Python packages:

```dockerfile
RUN pip3 install additional-packages
```

Then rebuild:

```bash
./build-and-push.sh $AWS_REGION $ACCOUNT_ID $PROJECT_NAME gpu-slim
```

## Tips

```bash
docker build -f Dockerfile.cpu-slim -t my-test-image:latest .
docker run --rm -it my-test-image:latest python3 --version
```
