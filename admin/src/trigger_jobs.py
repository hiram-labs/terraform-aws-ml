#!/usr/bin/env python3
"""
Trigger jobs by publishing messages to an SNS topic.

Usage:
    python src/trigger_jobs.py --topic-arn <SNS_TOPIC_ARN> --data '{"input_key": "path/to/input.mp4"}'
    python src/trigger_jobs.py --preset extract-audio --data '{"input_key": "path/to/input.mp4"}'

Environment Variables:
    TRIGGER_EVENTS_TOPIC_ARN, AWS_PROFILE, AWS_REGION (optional)
"""
import os
import argparse
import boto3
import json
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Trigger jobs by publishing to SNS')
    parser.add_argument('--topic-arn', default=os.getenv('TRIGGER_EVENTS_TOPIC_ARN'), help='SNS topic ARN (or set TRIGGER_EVENTS_TOPIC_ARN env var)')
    parser.add_argument('--data', help='Path to JSON file or JSON string for the SNS message data field')
    parser.add_argument('--preset', choices=['extract-audio'], help='Use a preset job payload (extends --data)')
    parser.add_argument('--trigger-type', default='batch_job', help='Override trigger_type (default: batch_job)')
    parser.add_argument('--user', default='orchestrator', help='Override metadata.user')
    parser.add_argument('--project', default='ml-pipeline', help='Override metadata.project')
    parser.add_argument('--region', default=os.getenv('AWS_REGION', 'us-east-1'), help='AWS region')
    return parser.parse_args()


def build_extract_audio_payload(override=None):
    base = {
        "script_key": "jobs/video_processor.py",
        "compute_type": "cpu",
        "operation": "extract_audio",
        "args": {"sample_rate": "16000", "channels": "1", "normalize": "true"}
    }
    if override:
        base.update(override)
    if 'input_key' not in base:
        raise ValueError("input_key must be provided in --data for extract-audio preset.")
    if 'output_key' not in base:
        input_key = base['input_key']
        base['output_key'] = input_key
    return base


def load_json_arg(arg):
    if os.path.isfile(arg):
        with open(arg, 'r') as f:
            return json.load(f)
    return json.loads(arg)


def load_data(args):
    if args.preset == 'extract-audio':
        override = load_json_arg(args.data) if args.data else None
        return build_extract_audio_payload(override)
    if args.data:
        return load_json_arg(args.data)
    raise ValueError("Either --data or --preset must be provided.")


def main():
    load_dotenv()
    args = parse_arguments()
    if not args.topic_arn:
        logger.error("SNS topic ARN must be provided via --topic-arn or TRIGGER_EVENTS_TOPIC_ARN env var.")
        exit(1)
    session = boto3.Session(region_name=args.region)
    sns_client = session.client('sns')
    data = load_data(args)
    payload = {
        "trigger_type": args.trigger_type,
        "data": data,
        "metadata": {
            "user": args.user,
            "project": args.project
        }
    }
    logger.info(f"Publishing job trigger to SNS topic: {args.topic_arn}")
    logger.info(f"Payload: {json.dumps(payload)}")
    response = sns_client.publish(
        TopicArn=args.topic_arn,
        Message=json.dumps(payload)
    )
    logger.info(f"SNS publish response: {response}")

if __name__ == '__main__':
    main()
