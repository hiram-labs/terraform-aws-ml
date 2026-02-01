#!/bin/bash
###############################################################
# ML Job Entry Point Script                                   #
# Handles S3 downloads, Python script execution, and uploads  #
###############################################################

set -e

echo "==================================="
echo "ML Batch Job Starting"
echo "==================================="
echo "Job Name: ${AWS_BATCH_JOB_ID}"
echo "Timestamp: $(date)"
echo "Input Bucket: ${ML_INPUT_BUCKET}"
echo "Output Bucket: ${ML_OUTPUT_BUCKET}"
echo "==================================="

# Verify GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Information:"
    nvidia-smi
    echo "==================================="
else
    echo "WARNING: nvidia-smi not found. Running in CPU mode."
fi

# Download and execute Python script from S3
if [ -n "${INPUT_KEY}" ]; then
    if [[ "${INPUT_KEY}" == *.py ]]; then
        echo "Downloading Python script: s3://${INPUT_BUCKET}/${INPUT_KEY}"
        aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_KEY}" /workspace/script.py

        echo "Executing Python script..."
        # Pass SNS_MESSAGE to script via stdin
        if [ -n "${SNS_MESSAGE}" ]; then
            echo "${SNS_MESSAGE}" | python3 /workspace/script.py
        else
            python3 /workspace/script.py
        fi
    else
        echo "Error: Only Python scripts (.py) are supported. Received: ${INPUT_KEY}"
        exit 1
    fi
else
    echo "No INPUT_KEY specified, running default command..."
    exec "$@"
fi

# Upload all output files to S3
echo "Uploading results to S3..."
if [ -d "/workspace/output" ]; then
    aws s3 sync /workspace/output/ \
        "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}" \
        --exclude "*.pyc" \
        --exclude "__pycache__/*"
fi

# Upload logs
if [ -d "/workspace/logs" ]; then
    aws s3 sync /workspace/logs/ \
        "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}logs/"
fi

echo "==================================="
echo "ML Batch Job Completed Successfully"
echo "Results: s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}"
echo "==================================="
