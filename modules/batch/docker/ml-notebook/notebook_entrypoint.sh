#!/bin/bash
###############################################################
# Notebook Execution Entry Point                              #
###############################################################

set -e

echo "Notebook Execution Job Starting"
echo "Input: s3://${INPUT_BUCKET}/${INPUT_KEY}"

# Download notebook
aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_KEY}" /workspace/input.ipynb

# Execute notebook with papermill
papermill /workspace/input.ipynb /workspace/output.ipynb \
    --log-output \
    --report-mode \
    --cwd /workspace

# Upload executed notebook
aws s3 cp /workspace/output.ipynb \
    "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}output.ipynb"

# Convert to HTML for easy viewing
jupyter nbconvert --to html /workspace/output.ipynb
aws s3 cp /workspace/output.html \
    "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}output.html"

# Upload any additional outputs
if [ -d "/workspace/output" ]; then
    aws s3 sync /workspace/output/ \
        "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}artifacts/"
fi

echo "Notebook execution completed"
echo "Results: s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}"
