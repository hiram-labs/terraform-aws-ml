# Slim Python ML Container
# Lightweight image for CPU processing and testing
# - Python 3.11
# - AWS CLI + boto3
# - Essential data science libraries
# - No CUDA, no GPU frameworks

FROM python:3.11-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    ca-certificates \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install AWS CLI for S3 access
RUN pip3 install awscli boto3

# Install essential ML libraries (no heavy frameworks)
RUN pip3 install \
    numpy==1.24.3 \
    pandas==2.1.0 \
    scikit-learn==1.3.0 \
    scipy==1.11.2 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    plotly==5.17.0 \
    pillow==10.0.1

# Create working directory
WORKDIR /workspace

# Copy entry point script (shared across images)
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set entry point
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python3"]
