# Production-Grade ML Container with GPU Support
# Based on NVIDIA CUDA and TensorFlow/PyTorch

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    curl \
    wget \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install core dependencies
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install AWS CLI for S3 access
RUN pip3 install awscli boto3

# Install ML frameworks
RUN pip3 install \
    torch==2.1.0 \
    torchvision==0.16.0 \
    torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu121

RUN pip3 install tensorflow==2.15.0

# Install common ML libraries
RUN pip3 install \
    numpy==1.24.3 \
    pandas==2.1.0 \
    scikit-learn==1.3.0 \
    scipy==1.11.2 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    plotly==5.17.0 \
    xgboost==2.0.0 \
    lightgbm==4.1.0 \
    transformers==4.34.0 \
    accelerate==0.23.0 \
    datasets==2.14.5 \
    tokenizers==0.14.1 \
    sentencepiece==0.1.99 \
    pillow==10.0.1 \
    opencv-python-headless==4.8.1.78 \
    albumentations==1.3.1

# Install monitoring and logging
RUN pip3 install \
    tensorboard==2.15.0 \
    wandb==0.15.12 \
    mlflow==2.7.1

# Create working directory
WORKDIR /workspace

# Copy entry point script (shared across images)
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set entry point
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python3"]
