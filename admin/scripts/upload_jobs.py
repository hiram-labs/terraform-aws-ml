#!/usr/bin/env python3
"""
Upload all files in the jobs directory to a specified S3 bucket/prefix.

Usage:
    python scripts/upload_jobs.py --bucket my-bucket --prefix jobs/

Environment Variables:
    AWS_PROFILE, AWS_REGION (optional)
"""
import os
import argparse
import boto3
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload all files in jobs/ to S3')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--prefix', default='jobs/', help='S3 prefix (default: jobs/)')
    parser.add_argument('--region', default=os.getenv('AWS_REGION', 'us-east-1'), help='AWS region')
    return parser.parse_args()


def upload_files(s3_client, bucket, prefix, local_dir):
    local_dir = Path(local_dir)
    if not local_dir.exists() or not local_dir.is_dir():
        logger.error(f"Local directory not found: {local_dir}")
        return False
    uploaded = 0
    for file in local_dir.iterdir():
        if file.is_file():
            s3_key = f"{prefix}{file.name}"
            try:
                logger.info(f"Uploading {file} to s3://{bucket}/{s3_key}")
                s3_client.upload_file(str(file), bucket, s3_key)
                uploaded += 1
            except Exception as e:
                logger.error(f"Failed to upload {file}: {str(e)}")
                raise
    logger.info(f"Uploaded {uploaded} files to s3://{bucket}/{prefix}")
    return True


def main():
    load_dotenv()
    args = parse_arguments()
    session = boto3.Session(region_name=args.region)
    s3_client = session.client('s3')
    logger.info(f"Uploading all files in jobs/ to s3://{args.bucket}/{args.prefix}")
    upload_files(s3_client, args.bucket, args.prefix, os.path.join(os.path.dirname(__file__), '..', '..', 'jobs'))

if __name__ == '__main__':
    main()
