"""
AWS Batch Job Trigger Lambda Function

Automatically submits AWS Batch jobs when ML scripts or Jupyter notebooks
are uploaded to S3 input bucket.

Features:
- Automatic job type detection (Python script vs Jupyter notebook)
- Custom job parameter overrides via S3 object metadata
- Error handling and optional SNS notifications
- Support for batch processing multiple files
"""

import json
import os
import boto3
import urllib.parse
from datetime import datetime

# Initialize AWS clients
batch_client = boto3.client('batch')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns') if os.environ.get('ENABLE_NOTIFICATIONS') == 'true' else None

# Environment variables
JOB_QUEUE = os.environ['BATCH_JOB_QUEUE']
PYTHON_JOB_DEF = os.environ['ML_PYTHON_JOB_DEFINITION']
NOTEBOOK_JOB_DEF = os.environ['ML_NOTEBOOK_JOB_DEFINITION']
OUTPUT_BUCKET = os.environ['ML_OUTPUT_BUCKET']
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
DEFAULT_VCPUS = int(os.environ.get('DEFAULT_VCPUS', '4'))
DEFAULT_MEMORY = int(os.environ.get('DEFAULT_MEMORY', '16384'))
DEFAULT_GPUS = int(os.environ.get('DEFAULT_GPUS', '1'))


def lambda_handler(event, context):
    """
    Main Lambda handler for S3 event processing
    """
    print(f"Received event: {json.dumps(event)}")
    
    results = []
    
    for record in event['Records']:
        try:
            # Parse S3 event
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            size = record['s3']['object']['size']
            
            print(f"Processing file: s3://{bucket}/{key} ({size} bytes)")
            
            # Get object metadata for custom job parameters
            metadata = get_object_metadata(bucket, key)
            
            # Determine job type based on file extension
            job_definition = determine_job_definition(key)
            
            # Generate job name
            job_name = generate_job_name(key)
            
            # Prepare job parameters
            job_params = {
                'INPUT_BUCKET': bucket,
                'INPUT_KEY': key,
                'OUTPUT_BUCKET': OUTPUT_BUCKET,
                'OUTPUT_PREFIX': f"results/{datetime.now().strftime('%Y-%m-%d')}/{job_name}/",
                'TIMESTAMP': datetime.now().isoformat()
            }
            
            # Merge custom parameters from metadata
            if metadata:
                custom_params = {k.upper(): v for k, v in metadata.items() if k.startswith('job-')}
                job_params.update(custom_params)
            
            # Build resource requirements with overrides
            container_overrides = build_container_overrides(metadata, job_params)
            
            # Submit Batch job
            response = batch_client.submit_job(
                jobName=job_name,
                jobQueue=JOB_QUEUE,
                jobDefinition=job_definition,
                containerOverrides=container_overrides
            )
            
            job_id = response['jobId']
            print(f"Submitted job: {job_name} (ID: {job_id})")
            
            results.append({
                'status': 'success',
                'file': key,
                'job_id': job_id,
                'job_name': job_name
            })
            
            # Send SNS notification
            if sns_client and SNS_TOPIC_ARN:
                send_notification(
                    subject=f"ML Job Submitted: {job_name}",
                    message=f"Job ID: {job_id}\nFile: s3://{bucket}/{key}\nJob Definition: {job_definition}"
                )
                
        except Exception as e:
            print(f"Error processing {key}: {str(e)}")
            results.append({
                'status': 'error',
                'file': key,
                'error': str(e)
            })
            
            if sns_client and SNS_TOPIC_ARN:
                send_notification(
                    subject=f"ML Job Submission Failed",
                    message=f"File: s3://{bucket}/{key}\nError: {str(e)}"
                )
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }


def get_object_metadata(bucket, key):
    """
    Retrieve S3 object metadata for custom job parameters
    """
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return response.get('Metadata', {})
    except Exception as e:
        print(f"Error getting metadata: {str(e)}")
        return {}


def determine_job_definition(key):
    """
    Determine job definition based on file extension
    """
    if key.endswith('.ipynb'):
        return NOTEBOOK_JOB_DEF
    elif key.endswith('.py'):
        return PYTHON_JOB_DEF
    else:
        # Default to Python job for other files
        return PYTHON_JOB_DEF


def generate_job_name(key):
    """
    Generate a valid Batch job name from S3 key
    """
    # Extract filename without extension
    filename = key.split('/')[-1].rsplit('.', 1)[0]
    
    # Replace invalid characters
    job_name = ''.join(c if c.isalnum() or c in '-_' else '-' for c in filename)
    
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    # Batch job names can be up to 128 characters
    max_name_length = 128 - len(timestamp) - 1
    job_name = job_name[:max_name_length]
    
    return f"{job_name}-{timestamp}"


def build_container_overrides(metadata, job_params):
    """
    Build container overrides with resource requirements and environment variables
    """
    overrides = {
        'environment': [
            {'name': k, 'value': v} for k, v in job_params.items()
        ]
    }
    
    # Resource overrides from metadata
    resource_requirements = []
    
    vcpus = metadata.get('job-vcpus', str(DEFAULT_VCPUS))
    memory = metadata.get('job-memory', str(DEFAULT_MEMORY))
    gpus = metadata.get('job-gpus', str(DEFAULT_GPUS))
    
    resource_requirements.append({'type': 'VCPU', 'value': vcpus})
    resource_requirements.append({'type': 'MEMORY', 'value': memory})
    resource_requirements.append({'type': 'GPU', 'value': gpus})
    
    overrides['resourceRequirements'] = resource_requirements
    
    # Command override from metadata
    if 'job-command' in metadata:
        overrides['command'] = metadata['job-command'].split()
    
    return overrides


def send_notification(subject, message):
    """
    Send SNS notification
    """
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except Exception as e:
        print(f"Error sending SNS notification: {str(e)}")
