#!/usr/bin/env python3
"""
Simple CPU Processing Script for AWS Batch

This script demonstrates a CPU-only workload:
1. Generate or load data
2. Process with pandas/NumPy
3. Save results to S3
"""

import os
import json
import boto3
import pandas as pd
import numpy as np
from datetime import datetime

# Environment variables set by Batch job
INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'cpu')

s3_client = boto3.client('s3')

print(f"Processing on CPU (compute_type={COMPUTE_TYPE})")

# Generate synthetic data
print("Generating data...")
data = {
    'id': np.arange(10000),
    'value': np.random.randn(10000),
    'category': np.random.choice(['A', 'B', 'C', 'D'], 10000),
    'timestamp': [datetime.now().isoformat()] * 10000
}
df = pd.DataFrame(data)

# Process data
print("Processing...")
results = {
    'total_rows': len(df),
    'null_count': int(df.isnull().sum().sum()),
    'mean_value': float(df['value'].mean()),
    'std_value': float(df['value'].std()),
    'categories': df['category'].value_counts().to_dict(),
    'timestamp': datetime.now().isoformat()
}

# Save processed data
os.makedirs('/workspace/output', exist_ok=True)

# Save as CSV
csv_path = '/workspace/output/processed_data.csv'
df.to_csv(csv_path, index=False)
print(f"Data saved to {csv_path}")

# Save summary statistics
stats_path = '/workspace/output/statistics.json'
with open(stats_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"Statistics: {results}")

# Upload to S3
print(f"\nUploading to s3://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}...")
s3_client.upload_file(csv_path, OUTPUT_BUCKET, f"{OUTPUT_PREFIX}processed_data.csv")
s3_client.upload_file(stats_path, OUTPUT_BUCKET, f"{OUTPUT_PREFIX}statistics.json")
print("Done!")
