#!/usr/bin/env python3
"""
Simple Training Script for AWS Batch

This script demonstrates a minimal ML training pipeline:
1. Create synthetic data
2. Train a PyTorch model (GPU-accelerated)
3. Save model and metrics to S3
"""

import os
import json
import boto3
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime

# Environment variables set by Batch job
INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'gpu')

s3_client = boto3.client('s3')
device = torch.device('cuda' if torch.cuda.is_available() and COMPUTE_TYPE == 'gpu' else 'cpu')

print(f"Training on {device}")
if torch.cuda.is_available():
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Simple model
class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(20, 64)
        self.fc2 = nn.Linear(64, 10)
    
    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))

# Training
model = SimpleModel().to(device)
optimizer = optim.SGD(model.parameters(), lr=0.01)
loss_fn = nn.CrossEntropyLoss()

# Synthetic data
X = torch.randn(1000, 20, device=device)
y = torch.randint(0, 10, (1000,), device=device)

print("Training...")
for epoch in range(10):
    optimizer.zero_grad()
    output = model(X)
    loss = loss_fn(output, y)
    loss.backward()
    optimizer.step()
    print(f"  Epoch {epoch+1}/10, Loss: {loss.item():.4f}")

# Save results
os.makedirs('/workspace/output', exist_ok=True)
model_path = '/workspace/output/model.pth'
torch.save(model.state_dict(), model_path)

metrics = {
    'final_loss': float(loss.item()),
    'device': str(device),
    'timestamp': datetime.now().isoformat()
}

metrics_path = '/workspace/output/metrics.json'
with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"\nModel saved to {model_path}")
print(f"Metrics: {metrics}")

# Upload to S3
print(f"\nUploading to s3://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}...")
s3_client.upload_file(model_path, OUTPUT_BUCKET, f"{OUTPUT_PREFIX}model.pth")
s3_client.upload_file(metrics_path, OUTPUT_BUCKET, f"{OUTPUT_PREFIX}metrics.json")
print("Done!")
