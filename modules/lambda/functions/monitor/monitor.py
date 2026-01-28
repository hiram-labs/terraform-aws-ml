"""
AWS Batch Job Monitoring Lambda Function

Monitors Batch job state changes and sends notifications on completion or failure.
Can also trigger post-processing workflows.
"""

import json
import os
import boto3
from datetime import datetime

sns_client = boto3.client('sns')
s3_client = boto3.client('s3')
batch_client = boto3.client('batch')

SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
OUTPUT_BUCKET = os.environ['ML_OUTPUT_BUCKET']


def lambda_handler(event, context):
    """
    Handle Batch job state change events
    """
    print(f"Received event: {json.dumps(event)}")
    
    detail = event['detail']
    job_name = detail['jobName']
    job_id = detail['jobId']
    status = detail['status']
    
    print(f"Job {job_name} (ID: {job_id}) changed to status: {status}")
    
    # Get job details
    job_details = get_job_details(job_id)
    
    if status == 'SUCCEEDED':
        handle_success(job_name, job_id, job_details)
    elif status == 'FAILED':
        handle_failure(job_name, job_id, job_details)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Processed job {job_name} with status {status}'})
    }


def get_job_details(job_id):
    """
    Retrieve detailed information about the job
    """
    try:
        response = batch_client.describe_jobs(jobs=[job_id])
        if response['jobs']:
            return response['jobs'][0]
    except Exception as e:
        print(f"Error getting job details: {str(e)}")
    return {}


def handle_success(job_name, job_id, job_details):
    """
    Handle successful job completion
    """
    print(f"Job {job_name} completed successfully")
    
    # Extract job metadata
    started_at = job_details.get('startedAt', 0)
    stopped_at = job_details.get('stoppedAt', 0)
    duration = (stopped_at - started_at) / 1000 if started_at and stopped_at else 0
    
    container = job_details.get('container', {})
    exit_code = container.get('exitCode', 'Unknown')
    log_stream = container.get('logStreamName', '')
    
    # Get environment variables to find output location
    env_vars = {env['name']: env['value'] for env in container.get('environment', [])}
    output_prefix = env_vars.get('OUTPUT_PREFIX', f'results/{job_name}/')
    
    # Build notification message
    message = f"""
ML Job Completed Successfully

Job Name: {job_name}
Job ID: {job_id}
Duration: {duration:.2f} seconds
Exit Code: {exit_code}

Output Location: s3://{OUTPUT_BUCKET}/{output_prefix}

CloudWatch Logs: {log_stream}

Check the output bucket for results.
"""
    
    send_notification(
        subject=f"✅ ML Job Succeeded: {job_name}",
        message=message
    )
    
    # Optional: Create a job summary file in S3
    create_job_summary(job_name, job_id, 'SUCCEEDED', job_details)


def handle_failure(job_name, job_id, job_details):
    """
    Handle failed job
    """
    print(f"Job {job_name} failed")
    
    container = job_details.get('container', {})
    exit_code = container.get('exitCode', 'Unknown')
    reason = container.get('reason', 'Unknown')
    log_stream = container.get('logStreamName', '')
    
    status_reason = job_details.get('statusReason', 'No reason provided')
    
    message = f"""
ML Job Failed

Job Name: {job_name}
Job ID: {job_id}
Exit Code: {exit_code}
Reason: {reason}
Status Reason: {status_reason}

CloudWatch Logs: {log_stream}

Please check the logs for detailed error information.
"""
    
    send_notification(
        subject=f"❌ ML Job Failed: {job_name}",
        message=message
    )
    
    # Create failure summary
    create_job_summary(job_name, job_id, 'FAILED', job_details)


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
        print(f"Sent notification: {subject}")
    except Exception as e:
        print(f"Error sending notification: {str(e)}")


def create_job_summary(job_name, job_id, status, job_details):
    """
    Create a JSON summary file in S3
    """
    try:
        summary = {
            'job_name': job_name,
            'job_id': job_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': job_details
        }
        
        key = f"job-summaries/{datetime.now().strftime('%Y-%m-%d')}/{job_name}-{job_id}.json"
        
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=key,
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )
        
        print(f"Created job summary: s3://{OUTPUT_BUCKET}/{key}")
    except Exception as e:
        print(f"Error creating job summary: {str(e)}")
