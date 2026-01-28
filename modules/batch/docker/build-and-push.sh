#!/bin/bash
###############################################################
# Build and Push ML Container Images to ECR                   #
#                                                             #
# Usage:                                                      #
#   ./build-and-push.sh <region> <account_id> <project>      #
#                                                             #
# Optional: Specify which images to build                     #
#   ./build-and-push.sh <region> <account_id> <project> slim #
#   ./build-and-push.sh <region> <account_id> <project> full #
#   ./build-and-push.sh <region> <account_id> <project>      # builds both
###############################################################

set -e

# Get parameters
REGION=${1:-us-east-1}
ACCOUNT_ID=${2}
PROJECT_NAME=${3:-ml-pipeline}
BUILD_TYPE=${4:-both}  # slim, full, or both (default: both)

# Validate inputs
if [ -z "$ACCOUNT_ID" ]; then
    echo "Usage: $0 <region> <account_id> <project_name> [slim|full|both]"
    echo ""
    echo "Examples:"
    echo "  $0 us-east-1 123456789012 ml-pipeline slim"
    echo "  $0 us-east-1 123456789012 ml-pipeline full"
    echo "  $0 us-east-1 123456789012 ml-pipeline     # builds both"
    exit 1
fi

# ECR registry URL
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Image names
SLIM_IMAGE_NAME="${PROJECT_NAME}-ml-python-slim"
FULL_IMAGE_NAME="${PROJECT_NAME}-ml-python"

echo "==================================================================="
echo "ML Container Build & Push to ECR"
echo "==================================================================="
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "ECR Registry: $ECR_REGISTRY"
echo "Project: $PROJECT_NAME"
echo "Build Type: $BUILD_TYPE"
echo "==================================================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push slim image
if [ "$BUILD_TYPE" = "slim" ] || [ "$BUILD_TYPE" = "both" ]; then
    echo ""
    echo "==================================================================="
    echo "Building SLIM Image (lightweight Python ML container)"
    echo "==================================================================="
    echo ""
    
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories \
        --repository-names $SLIM_IMAGE_NAME \
        --region $REGION 2>/dev/null || \
        aws ecr create-repository \
            --repository-name $SLIM_IMAGE_NAME \
            --region $REGION
    
    # Build slim image
    echo "Building slim image..."
    docker build \
        -t $SLIM_IMAGE_NAME:latest \
        -t $SLIM_IMAGE_NAME:$(date +%Y%m%d-%H%M%S) \
        -f $SCRIPT_DIR/ml-python-slim/Dockerfile \
        $SCRIPT_DIR
    
    # Tag for ECR
    SLIM_ECR_URI="${ECR_REGISTRY}/${SLIM_IMAGE_NAME}:latest"
    docker tag $SLIM_IMAGE_NAME:latest $SLIM_ECR_URI
    
    # Push to ECR
    echo "Pushing slim image to ECR..."
    docker push $SLIM_ECR_URI
    
    echo ""
    echo "✓ Slim image pushed successfully!"
    echo "ECR URI: $SLIM_ECR_URI"
    echo ""
fi

# Build and push full GPU image
if [ "$BUILD_TYPE" = "full" ] || [ "$BUILD_TYPE" = "both" ]; then
    echo ""
    echo "==================================================================="
    echo "Building FULL Image (GPU ML container with TensorFlow + PyTorch)"
    echo "==================================================================="
    echo ""
    
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories \
        --repository-names $FULL_IMAGE_NAME \
        --region $REGION 2>/dev/null || \
        aws ecr create-repository \
            --repository-name $FULL_IMAGE_NAME \
            --region $REGION
    
    # Build full image (this takes longer)
    echo "Building full image (this may take 10-20 minutes)..."
    docker build \
        -t $FULL_IMAGE_NAME:latest \
        -t $FULL_IMAGE_NAME:$(date +%Y%m%d-%H%M%S) \
        -f $SCRIPT_DIR/ml-python/Dockerfile \
        $SCRIPT_DIR
    
    # Tag for ECR
    FULL_ECR_URI="${ECR_REGISTRY}/${FULL_IMAGE_NAME}:latest"
    docker tag $FULL_IMAGE_NAME:latest $FULL_ECR_URI
    
    # Push to ECR
    echo "Pushing full image to ECR..."
    docker push $FULL_ECR_URI
    
    echo ""
    echo "✓ Full image pushed successfully!"
    echo "ECR URI: $FULL_ECR_URI"
    echo ""
fi

echo "==================================================================="
echo "Build Complete!"
echo "==================================================================="
echo ""
echo "To use the image, update terraform.tfvars:"
if [ "$BUILD_TYPE" = "slim" ] || [ "$BUILD_TYPE" = "both" ]; then
    echo "  ml_container_image = \"${ECR_REGISTRY}/${SLIM_IMAGE_NAME}:latest\""
fi
if [ "$BUILD_TYPE" = "full" ] || [ "$BUILD_TYPE" = "both" ]; then
    echo "  ml_container_image = \"${ECR_REGISTRY}/${FULL_IMAGE_NAME}:latest\""
fi
echo ""
echo "Then run: terraform apply"
echo ""
echo "==================================="
