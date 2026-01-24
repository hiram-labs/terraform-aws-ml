#!/bin/bash
###############################################################
# Build and Push ML Docker Images to ECR                      #
###############################################################

set -e

# Configuration
AWS_REGION="${1:-us-east-1}"
AWS_ACCOUNT_ID="${2:-$(aws sts get-caller-identity --query Account --output text)}"
PROJECT_NAME="${3:-my-project}"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Building and pushing ML container images..."
echo "Registry: ${ECR_REGISTRY}"
echo "Project: ${PROJECT_NAME}"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Create ECR repositories if they don't exist
aws ecr create-repository \
    --repository-name ${PROJECT_NAME}-ml-python \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || true

aws ecr create-repository \
    --repository-name ${PROJECT_NAME}-ml-notebook \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || true

# Build Python ML image
echo "Building ML Python image..."
docker build \
    -f ml-python/Dockerfile.ml-python \
    -t ${PROJECT_NAME}-ml-python:latest \
    .

docker tag ${PROJECT_NAME}-ml-python:latest \
    ${ECR_REGISTRY}/${PROJECT_NAME}-ml-python:latest

docker push ${ECR_REGISTRY}/${PROJECT_NAME}-ml-python:latest

# Build Notebook image
echo "Building ML Notebook image..."
docker build \
    -f ml-notebook/Dockerfile.notebook \
    -t ${PROJECT_NAME}-ml-notebook:latest \
    .

docker tag ${PROJECT_NAME}-ml-notebook:latest \
    ${ECR_REGISTRY}/${PROJECT_NAME}-ml-notebook:latest

docker push ${ECR_REGISTRY}/${PROJECT_NAME}-ml-notebook:latest

echo "==================================="
echo "Images pushed successfully!"
echo ""
echo "Python ML Image:"
echo "  ${ECR_REGISTRY}/${PROJECT_NAME}-ml-python:latest"
echo ""
echo "Notebook Image:"
echo "  ${ECR_REGISTRY}/${PROJECT_NAME}-ml-notebook:latest"
echo "==================================="
