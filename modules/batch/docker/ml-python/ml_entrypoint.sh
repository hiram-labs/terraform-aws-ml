#!/bin/bash
###############################################################
# ML Job Entry Point Script                                   #
# Handles S3 downloads, job execution, and result uploads     #
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

# Download input file from S3
if [ -n "${INPUT_KEY}" ]; then
    echo "Downloading input: s3://${INPUT_BUCKET}/${INPUT_KEY}"
    aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_KEY}" /workspace/input_file
    
    # Determine file type and execute accordingly
    if [[ "${INPUT_KEY}" == *.ipynb ]]; then
        echo "Executing Jupyter notebook with papermill..."
        papermill /workspace/input_file /workspace/output.ipynb \
            --log-output \
            --report-mode
        
        # Upload executed notebook
        aws s3 cp /workspace/output.ipynb \
            "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}output.ipynb"
        
    elif [[ "${INPUT_KEY}" == *.py ]]; then
        echo "Executing Python script..."
        python3 /workspace/input_file
        
    else
        echo "Unknown file type: ${INPUT_KEY}"
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
