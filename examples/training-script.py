"""
Example ML Training Script for AWS Batch

This script demonstrates a complete ML training pipeline that:
1. Downloads training data from S3
2. Trains a model with GPU acceleration
3. Saves results and model back to S3
4. Logs metrics and progress
"""

import os
import sys
import json
import time
from datetime import datetime
import boto3
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

# Environment variables set by Batch job
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', '')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', '')
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX', 'results/')

# Initialize S3 client
s3_client = boto3.client('s3')

# Setup logging
def log(message):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {message}", flush=True)

class SimpleNeuralNetwork(nn.Module):
    """Simple feedforward neural network"""
    def __init__(self, input_size, hidden_size, num_classes):
        super(SimpleNeuralNetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, num_classes)
        
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.relu(x)
        x = self.fc3(x)
        return x

def download_data_from_s3(bucket, key, local_path):
    """Download training data from S3"""
    log(f"Downloading data from s3://{bucket}/{key}")
    s3_client.download_file(bucket, key, local_path)
    log(f"Downloaded to {local_path}")

def upload_results_to_s3(local_path, s3_key):
    """Upload results to S3"""
    log(f"Uploading {local_path} to s3://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}{s3_key}")
    s3_client.upload_file(
        local_path,
        OUTPUT_BUCKET,
        f"{OUTPUT_PREFIX}{s3_key}"
    )

def train_model():
    """Main training function"""
    
    # Check GPU availability
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    log(f"Using device: {device}")
    
    if torch.cuda.is_available():
        log(f"GPU: {torch.cuda.get_device_name(0)}")
        log(f"CUDA Version: {torch.version.cuda}")
        log(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    # Create output directory
    os.makedirs('/workspace/output', exist_ok=True)
    os.makedirs('/workspace/logs', exist_ok=True)
    
    # Generate synthetic training data (replace with real data loading)
    log("Generating training data...")
    X = np.random.randn(10000, 20)
    y = np.random.randint(0, 3, 10000)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Normalize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    
    # Convert to PyTorch tensors
    X_train_tensor = torch.FloatTensor(X_train).to(device)
    y_train_tensor = torch.LongTensor(y_train).to(device)
    X_test_tensor = torch.FloatTensor(X_test).to(device)
    y_test_tensor = torch.LongTensor(y_test).to(device)
    
    # Initialize model
    input_size = X_train.shape[1]
    hidden_size = 128
    num_classes = len(np.unique(y))
    
    model = SimpleNeuralNetwork(input_size, hidden_size, num_classes).to(device)
    log(f"Model architecture:\n{model}")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training loop
    num_epochs = 100
    batch_size = 64
    training_history = []
    
    log("Starting training...")
    start_time = time.time()
    
    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0
        num_batches = len(X_train_tensor) // batch_size
        
        for i in range(0, len(X_train_tensor), batch_size):
            batch_X = X_train_tensor[i:i+batch_size]
            batch_y = y_train_tensor[i:i+batch_size]
            
            # Forward pass
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
        
        # Validation
        model.eval()
        with torch.no_grad():
            test_outputs = model(X_test_tensor)
            test_loss = criterion(test_outputs, y_test_tensor)
            _, predicted = torch.max(test_outputs.data, 1)
            accuracy = (predicted == y_test_tensor).sum().item() / len(y_test_tensor)
        
        avg_train_loss = epoch_loss / num_batches
        
        training_history.append({
            'epoch': epoch + 1,
            'train_loss': avg_train_loss,
            'test_loss': test_loss.item(),
            'accuracy': accuracy
        })
        
        if (epoch + 1) % 10 == 0:
            log(f"Epoch [{epoch+1}/{num_epochs}], "
                f"Train Loss: {avg_train_loss:.4f}, "
                f"Test Loss: {test_loss:.4f}, "
                f"Accuracy: {accuracy:.4f}")
    
    training_time = time.time() - start_time
    log(f"Training completed in {training_time:.2f} seconds")
    
    # Final evaluation
    model.eval()
    with torch.no_grad():
        test_outputs = model(X_test_tensor)
        _, predicted = torch.max(test_outputs.data, 1)
        
    final_accuracy = accuracy_score(y_test_tensor.cpu(), predicted.cpu())
    log(f"Final Test Accuracy: {final_accuracy:.4f}")
    
    # Save model
    model_path = '/workspace/output/model.pth'
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scaler': scaler,
        'input_size': input_size,
        'hidden_size': hidden_size,
        'num_classes': num_classes,
    }, model_path)
    log(f"Model saved to {model_path}")
    
    # Save training history
    history_df = pd.DataFrame(training_history)
    history_path = '/workspace/output/training_history.csv'
    history_df.to_csv(history_path, index=False)
    log(f"Training history saved to {history_path}")
    
    # Save metrics
    metrics = {
        'final_accuracy': final_accuracy,
        'training_time_seconds': training_time,
        'num_epochs': num_epochs,
        'device': str(device),
        'timestamp': datetime.now().isoformat(),
    }
    
    if torch.cuda.is_available():
        metrics['gpu_name'] = torch.cuda.get_device_name(0)
        metrics['cuda_version'] = torch.version.cuda
    
    metrics_path = '/workspace/output/metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    log(f"Metrics saved to {metrics_path}")
    
    # Upload all results to S3
    log("Uploading results to S3...")
    upload_results_to_s3(model_path, 'model.pth')
    upload_results_to_s3(history_path, 'training_history.csv')
    upload_results_to_s3(metrics_path, 'metrics.json')
    
    log("Training job completed successfully!")
    return metrics

if __name__ == '__main__':
    try:
        log("="*60)
        log("ML Training Job Started")
        log("="*60)
        
        metrics = train_model()
        
        log("="*60)
        log("Job Summary:")
        log(f"  Accuracy: {metrics['final_accuracy']:.4f}")
        log(f"  Training Time: {metrics['training_time_seconds']:.2f}s")
        log(f"  Results: s3://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}")
        log("="*60)
        
        sys.exit(0)
        
    except Exception as e:
        log(f"ERROR: {str(e)}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
