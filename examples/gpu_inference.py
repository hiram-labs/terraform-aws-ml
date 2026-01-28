#!/usr/bin/env python3
"""
Simple Inference Script for AWS Batch

This script demonstrates minimal batch inference:
1. Create synthetic test data
2. Run inference with PyTorch
3. Save predictions to S3
"""

import os
import json
import boto3
import torch
import torch.nn as nn
from datetime import datetime

# Environment variables set by Batch job
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'gpu')

s3_client = boto3.client('s3')
device = torch.device('cuda' if torch.cuda.is_available() and COMPUTE_TYPE == 'gpu' else 'cpu')

print(f"Inference on {device}")
if torch.cuda.is_available():
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Simple model (same as training script)
class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(20, 64)
        self.fc2 = nn.Linear(64, 10)
    
    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))

# Load pretrained model
model = SimpleModel().to(device)
model.eval()

# Synthetic test data
X_test = torch.randn(100, 20, device=device)

print(f"Running inference on {X_test.shape[0]} samples...")
with torch.no_grad():
    predictions = model(X_test)
    predicted_classes = torch.argmax(predictions, dim=1)

# Save results
os.makedirs('/workspace/output', exist_ok=True)
results = {
    'num_samples': X_test.shape[0],
    'predictions': predicted_classes.cpu().tolist(),
    'timestamp': datetime.now().isoformat(),
    'device': str(device)
}

results_path = '/workspace/output/predictions.json'
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"Predictions saved to {results_path}")

# Upload to S3
print(f"Uploading to s3://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}...")
s3_client.upload_file(results_path, OUTPUT_BUCKET, f"{OUTPUT_PREFIX}predictions.json")
print("Done!")
