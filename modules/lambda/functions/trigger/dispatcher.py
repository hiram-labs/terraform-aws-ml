"""
SNS Trigger Dispatcher

Receives SNS messages and routes them to appropriate trigger implementations.
Handles message parsing, validation, error handling, and dead letter queue management.
"""

import json
import os
import boto3
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import sys

# Import trigger implementations
from base import BaseTrigger, TriggerError, ValidationError, ExecutionError
from batch_job import BatchJobTrigger

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')

# Environment variables
ENABLE_NOTIFICATIONS = os.environ.get('ENABLE_NOTIFICATIONS', 'false').lower() == 'true'
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
DLQ_URL = os.environ.get('DLQ_URL', '')

# Trigger registry - add new triggers here
TRIGGER_REGISTRY: Dict[str, type] = {
    'batch_job': BatchJobTrigger,
    # Add more triggers as needed
    # 'model_evaluation': ModelEvaluationTrigger,
    # 'data_validation': DataValidationTrigger,
}


def lambda_handler(event, context):
    """
    Main Lambda handler for SNS-triggered events.
    
    Args:
        event: SNS event containing trigger messages
        context: Lambda context
    
    Returns:
        dict: Execution results with statusCode and body
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    results = []
    
    try:
        # Process SNS records
        for record in event.get('Records', []):
            try:
                result = process_sns_record(record, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing record: {str(e)}", exc_info=True)
                results.append({
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return {
            'statusCode': 200 if all(r['status'] == 'success' for r in results) else 400,
            'body': json.dumps({
                'results': results,
                'processed_count': len(results),
                'success_count': sum(1 for r in results if r['status'] == 'success'),
                'error_count': sum(1 for r in results if r['status'] == 'error')
            }),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Fatal error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Lambda error',
                'details': str(e)
            })
        }


def process_sns_record(record: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process a single SNS record.
    
    Args:
        record: SNS record from event
        context: Lambda context
    
    Returns:
        dict: Processing result
    """
    try:
        # Parse SNS message
        message_str = record['Sns']['Message']
        message = json.loads(message_str)
        
        logger.info(f"Processing message: {json.dumps(message)}")
        
        # Extract trigger type
        trigger_type = message.get('trigger_type')
        if not trigger_type:
            raise ValidationError("Message must include 'trigger_type' field")
        
        # Get trigger class
        trigger_class = TRIGGER_REGISTRY.get(trigger_type)
        if not trigger_class:
            raise ValidationError(
                f"Unknown trigger type: {trigger_type}. "
                f"Available triggers: {', '.join(TRIGGER_REGISTRY.keys())}"
            )
        
        # Initialize and execute trigger
        logger.info(f"Executing {trigger_type} trigger")
        trigger = trigger_class(message, context)
        
        # Validate message
        trigger.validate()
        
        # Execute trigger
        result = trigger.execute()
        
        # Add metadata
        result['trigger_type'] = trigger_type
        result['message_id'] = record['Sns']['MessageId']
        result['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Trigger {trigger_type} completed successfully: {result}")
        
        # Send success notification if enabled
        if ENABLE_NOTIFICATIONS and SNS_TOPIC_ARN:
            send_notification(
                subject=f"ML Trigger Success: {trigger_type}",
                message=format_notification(result),
                message_type='success'
            )
        
        return result
    
    except ValidationError as e:
        logger.warning(f"Validation error: {str(e)}")
        error_result = {
            'status': 'error',
            'error_type': 'validation',
            'error_message': str(e),
            'message_id': record['Sns'].get('MessageId', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Send error notification if enabled
        if ENABLE_NOTIFICATIONS and SNS_TOPIC_ARN:
            send_notification(
                subject="ML Trigger Validation Error",
                message=format_notification(error_result),
                message_type='error'
            )
        
        return error_result
    
    except ExecutionError as e:
        logger.error(f"Execution error: {str(e)}")
        error_result = {
            'status': 'error',
            'error_type': 'execution',
            'error_message': str(e),
            'message_id': record['Sns'].get('MessageId', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to DLQ if configured
        if DLQ_URL:
            send_to_dlq(record['Sns']['Message'], error_result)
        
        # Send error notification
        if ENABLE_NOTIFICATIONS and SNS_TOPIC_ARN:
            send_notification(
                subject="ML Trigger Execution Error",
                message=format_notification(error_result),
                message_type='error'
            )
        
        return error_result
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error_type': 'unexpected',
            'error_message': str(e),
            'message_id': record['Sns'].get('MessageId', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }


def send_notification(subject: str, message: str, message_type: str = 'info') -> None:
    """
    Send SNS notification.
    
    Args:
        subject: Email subject
        message: Email message
        message_type: 'success', 'error', or 'info'
    """
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
            MessageAttributes={
                'message_type': {
                    'StringValue': message_type,
                    'DataType': 'String'
                }
            }
        )
        logger.info(f"Notification sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")


def send_to_dlq(message: str, error_details: Dict[str, Any]) -> None:
    """
    Send failed message to SQS dead letter queue.
    
    Args:
        message: Original SNS message
        error_details: Error information
    """
    try:
        dlq_message = {
            'original_message': message,
            'error': error_details,
            'timestamp': datetime.now().isoformat()
        }
        
        sqs_client.send_message(
            QueueUrl=DLQ_URL,
            MessageBody=json.dumps(dlq_message),
            MessageAttributes={
                'error_type': {
                    'StringValue': error_details.get('error_type', 'unknown'),
                    'DataType': 'String'
                }
            }
        )
        logger.info("Message sent to DLQ")
    except Exception as e:
        logger.error(f"Failed to send message to DLQ: {str(e)}")


def format_notification(result: Dict[str, Any]) -> str:
    """
    Format result dictionary as notification message.
    
    Args:
        result: Execution result
    
    Returns:
        Formatted message string
    """
    lines = []
    
    if result['status'] == 'success':
        lines.append("✔ TRIGGER EXECUTION SUCCESSFUL\n")
        lines.append(f"Trigger Type: {result.get('trigger_type', 'unknown')}")
        
        if 'job_id' in result:
            lines.append(f"Job ID: {result['job_id']}")
        if 'job_name' in result:
            lines.append(f"Job Name: {result['job_name']}")
        
        if 'details' in result:
            lines.append("\nDetails:")
            for key, value in result['details'].items():
                if value:
                    lines.append(f"  {key}: {value}")
    else:
        lines.append("✗ TRIGGER EXECUTION FAILED\n")
        lines.append(f"Error Type: {result.get('error_type', 'unknown')}")
        lines.append(f"Error: {result.get('error_message', 'unknown error')}")
    
    lines.append(f"\nTimestamp: {result.get('timestamp', 'unknown')}")
    
    return "\n".join(lines)


def get_available_triggers() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all available triggers.
    
    Returns:
        dict: Trigger information
    """
    triggers = {}
    
    for trigger_name, trigger_class in TRIGGER_REGISTRY.items():
        # Create a dummy instance to get schema (without real message/context)
        dummy_message = {'trigger_type': trigger_name, 'data': {}, 'metadata': {}}
        try:
            trigger = trigger_class(dummy_message, None)
            triggers[trigger_name] = trigger.as_dict()
        except Exception:
            pass
    
    return triggers
