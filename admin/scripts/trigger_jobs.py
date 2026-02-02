#!/usr/bin/env python3
"""
Trigger jobs by publishing messages to an SNS topic.

Usage:
    python scripts/trigger_jobs.py --topic-arn <SNS_TOPIC_ARN> --data '{"input_key": "path/to/input.mp4"}'
    python scripts/trigger_jobs.py --preset extract_audio --data '{"input_key": "path/to/input.mp4"}'
    python scripts/trigger_jobs.py --preset transcribe_audio --data '{"input_key": "path/to/input.wav"}'
    python scripts/trigger_jobs.py --preset cleanup_cache

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
    parser.add_argument('--preset', choices=['extract_audio', 'transcribe_audio', 'cleanup_cache'], help='Use a preset job payload (extends --data)')
    parser.add_argument('--trigger-type', default='batch_job', help='Override trigger_type (default: batch_job)')
    parser.add_argument('--input-bucket', help='S3 bucket for input data')
    parser.add_argument('--output-bucket', help='S3 bucket for output results')
    parser.add_argument('--model-bucket', help='S3 bucket for ML models')
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


def build_transcribe_audio_payload(override=None):
    base = {
        "script_key": "jobs/transcribe_processor.py",
        "compute_type": "gpu",
        "operation": "transcribe_audio",
        "args": {
            "language": "en",
            "output_format": "json",
            "whisper_model": "guillaumekln/faster-whisper-small.en",
            "pyannote_model": "pyannote/speaker-diarization-3.1"
        }
    }
    if override:
        base.update(override)
    if 'input_key' not in base:
        raise ValueError("input_key must be provided in --data for transcribe-audio preset.")
    if 'output_key' not in base:
        input_key = base['input_key']
        base['output_key'] = input_key.rsplit('.', 1)[0] + '.json'
    return base


def build_cleanup_cache_payload(override=None):
    base = {
        "script_key": "jobs/cleanup_processor.py",
        "compute_type": "cpu",
        "operation": "cleanup_cache"
    }
    if override:
        base.update(override)
    return base


def load_json_arg(arg):
    if os.path.isfile(arg):
        with open(arg, 'r') as f:
            return json.load(f)
    return json.loads(arg)


def load_data(args):
    if args.preset == 'extract_audio':
        override = load_json_arg(args.data) if args.data else None
        return build_extract_audio_payload(override)
    elif args.preset == 'transcribe_audio':
        override = load_json_arg(args.data) if args.data else None
        return build_transcribe_audio_payload(override)
    elif args.preset == 'cleanup_cache':
        override = load_json_arg(args.data) if args.data else None
        return build_cleanup_cache_payload(override)
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
    # Add bucket info to payload if provided
    if args.input_bucket:
        payload["input_bucket"] = args.input_bucket
    if args.output_bucket:
        payload["output_bucket"] = args.output_bucket
    if args.model_bucket:
        payload["model_bucket"] = args.model_bucket
    logger.info(f"Publishing job trigger to SNS topic: {args.topic_arn}")
    logger.info(f"Payload: {json.dumps(payload)}")
    response = sns_client.publish(
        TopicArn=args.topic_arn,
        Message=json.dumps(payload)
    )
    logger.info(f"SNS publish response: {response}")

if __name__ == '__main__':
    main()

# python scripts/trigger_jobs.py --preset extract-audio --data '{"input_key": "media/sintel-short.mp4", "output_key": "media/sintel-short.wav"}'
# python scripts/trigger_jobs.py --preset transcribe-audio --data '{"input_key": "media/sintel-short.wav", "output_key": "data/sintel-short.json"}' --input-bucket ml-pipeline-ml-output
