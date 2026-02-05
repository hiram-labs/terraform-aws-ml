#!/bin/bash
#########################################################################
# Build and Push ML Container Images to ECR                             #
#                                                                       #
# Usage:                                                                #
#   ./build-and-push.sh <region> <account_id> <project>                 #
#                                                                       #
# Optional: Specify which image to build                                #
#   ./build-and-push.sh <region> <account_id> <project> cpu-slim  #
#   ./build-and-push.sh <region> <account_id> <project> # builds all    #
#########################################################################

set -e

# Get parameters
REGION=${1:-us-east-1}
ACCOUNT_ID=${2}
PROJECT_NAME=${3:-ml-pipeline}
DOCKERFILE_NAME=${4}  # Optional: specific dockerfile name (without Dockerfile. prefix)

# Validate inputs
if [ -z "$ACCOUNT_ID" ]; then
    echo "Usage: $0 <region> <account_id> <project_name> [dockerfile_name]"
    echo ""
    echo "Examples:"
    echo "  $0 us-east-1 123456789012 ml-pipeline cpu-slim"
    echo "  $0 us-east-1 123456789012 ml-pipeline     # builds all"
    exit 1
fi

# ECR registry URL
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==================================================================="
echo "ML Container Build & Push to ECR"
echo "==================================================================="
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "ECR Registry: $ECR_REGISTRY"
echo "Project: $PROJECT_NAME"
if [ -n "$DOCKERFILE_NAME" ]; then
    echo "Dockerfile: $DOCKERFILE_NAME"
else
    echo "Building: all images"
fi
echo "==================================================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Login to ECR
echo "Logging in to ECR..."
if ! aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY"; then
    echo "Error: Failed to login to ECR. Check AWS credentials and region."
    exit 1
fi

# Function to build and push a specific image
build_and_push() {
    local dockerfile_name="$1"
    local dockerfile_path="$SCRIPT_DIR/Dockerfile.$dockerfile_name"
    local image_name="${PROJECT_NAME}-${dockerfile_name}"
    
    if [ ! -f "$dockerfile_path" ]; then
        echo "Error: Dockerfile.$dockerfile_name not found!"
        return 1
    fi
    
    # Validate image name for ECR (lowercase, alphanumeric, hyphens only)
    if ! [[ "$image_name" =~ ^[a-z0-9-]+$ ]]; then
        echo "Error: Invalid image name '$image_name'. Use only lowercase alphanumeric and hyphens."
        return 1
    fi
    
    echo ""
    echo "==================================================================="
    echo "Building $dockerfile_name Image"
    echo "==================================================================="
    echo ""
    
    # Create ECR repository if it doesn't exist
    if ! aws ecr describe-repositories \
        --repository-names "$image_name" \
        --region "$REGION" 2>/dev/null; then
        echo "Creating ECR repository: $image_name"
        aws ecr create-repository \
            --repository-name "$image_name" \
            --region "$REGION" || return 1
    fi
    # Build image
    echo "Building $dockerfile_name image..."
    docker build \
        -t "$image_name:latest" \
        -t "$image_name:$(date +%Y%m%d-%H%M%S)" \
        -f "$dockerfile_path" \
        "$SCRIPT_DIR" || return 1
    
    # Tag for ECR
    ECR_URI="${ECR_REGISTRY}/${image_name}:latest"
    docker tag "$image_name:latest" "$ECR_URI" || return 1
    
    # Push to ECR
    echo "Pushing $dockerfile_name image to ECR..."
    docker push "$ECR_URI" || return 1
    
    echo ""
    echo "✓ $dockerfile_name image pushed successfully!"
    echo "ECR URI: $ECR_URI"
    echo ""
}

# Build specific image or all images
if [ -n "$DOCKERFILE_NAME" ]; then
    # Build specific image - validate it exists first
    if [ ! -f "$SCRIPT_DIR/Dockerfile.$DOCKERFILE_NAME" ]; then
        echo "Error: Dockerfile.$DOCKERFILE_NAME not found!"
        exit 1
    fi
    build_and_push "$DOCKERFILE_NAME" || exit 1
else
    # Build all available Dockerfiles
    for dockerfile in "$SCRIPT_DIR"/Dockerfile.*; do
        if [ -f "$dockerfile" ]; then
            dockerfile_name=$(basename "$dockerfile" | sed 's/Dockerfile\.//')
            build_and_push "$dockerfile_name" || exit 1
        fi
    done
fi

echo "==================================================================="
echo "Build Complete!"
echo "==================================================================="
echo ""
echo "To use the image(s), update terraform.tfvars:"
if [ -n "$DOCKERFILE_NAME" ]; then
    echo "  ml_container_image = \"${ECR_REGISTRY}/${PROJECT_NAME}-${DOCKERFILE_NAME}:latest\""
else
    echo "  # Update with the appropriate image URI"
fi
echo ""
echo "Then run: terraform apply"
echo ""
echo "==================================="
