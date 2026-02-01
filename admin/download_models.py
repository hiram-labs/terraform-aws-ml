#!/usr/bin/env python3
"""
Download and Upload HuggingFace Models to S3

Generic utility to download any HuggingFace model locally and upload to S3 for use in
AWS Batch jobs or other cloud workflows. Works with any model from the HuggingFace Hub.

Usage:
    # Whisper speech recognition models
    python download_models.py --bucket my-models \
        --model-type whisper \
        --model-names openai/whisper-tiny,openai/whisper-base,openai/whisper-small
    
    # Pyannote speaker diarization models (requires HuggingFace token)
    python download_models.py --bucket my-models \
        --model-type pyannote \
        --model-names pyannote/speaker-diarization-3.1,pyannote/segmentation-3.0 \
        --hf-token YOUR_TOKEN
    
    # Any other HuggingFace model
    python download_models.py --bucket my-models \
        --model-names bert-base-uncased,gpt2,facebook/bart-large

Environment Variables:
    AWS_PROFILE: AWS profile to use
    AWS_REGION: AWS region (default: us-east-1)
    HUGGINGFACE_TOKEN: Token for gated models (alternative to --hf-token)
"""

import os
import sys
import argparse
import boto3
import logging
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Download any HuggingFace model and upload to S3'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='S3 bucket name for model storage'
    )
    parser.add_argument(
        '--model-type',
        default='models',
        help='Model type for S3 organization (default: models). Use to categorize models (e.g., whisper, llama, bert)'
    )
    parser.add_argument(
        '--model-names',
        required=True,
        help='Comma-separated HuggingFace model IDs. Examples: bert-base-uncased,gpt2 | openai/whisper-base | meta-llama/Llama-2-7b-hf'
    )
    parser.add_argument(
        '--hf-token',
        default=os.getenv('HUGGINGFACE_TOKEN'),
        help='HuggingFace API token for gated/private models (default: HUGGINGFACE_TOKEN env var)'
    )
    parser.add_argument(
        '--region',
        default=os.getenv('AWS_REGION', 'us-east-1'),
        help='AWS region (default: AWS_REGION env var or us-east-1)'
    )
    parser.add_argument(
        '--prefix',
        default='models',
        help='S3 base prefix for all models (default: models)'
    )
    parser.add_argument(
        '--output-prefix',
        default=None,
        help='Custom S3 output path (default: {prefix}/{model-type})'
    )
    
    return parser.parse_args()


def download_models(models: list, hf_token: str = None):
    """
    Download any HuggingFace model.
    
    Works with any model on the HuggingFace Hub including:
    - Transformers models (BERT, GPT, T5, LLaMA, Mistral, etc.)
    - Whisper models (openai/whisper-*)
    - Any other HuggingFace model
    
    Args:
        models: List of HuggingFace model IDs
        hf_token: Optional HuggingFace token for gated/private models
    """
    from huggingface_hub import snapshot_download
    
    logger.info(f"Downloading HuggingFace models: {', '.join(models)}")
    
    for model_name in models:
        try:
            logger.info(f"Downloading {model_name}...")
            snapshot_download(repo_id=model_name, token=hf_token)
            logger.info(f"Downloaded {model_name}")
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {str(e)}")
            raise


def get_huggingface_cache_dir():
    """Get Hugging Face cache directory"""
    return Path(os.getenv('HF_HOME', Path.home() / '.cache' / 'huggingface'))


def upload_models_to_s3(s3_client, bucket: str, prefix: str, model_type: str, output_prefix: str = None):
    """Upload downloaded models to S3"""
    cache_dir = get_huggingface_cache_dir()
    hub_dir = cache_dir / 'hub'
    
    if not hub_dir.exists():
        logger.error(f"Cache directory not found: {hub_dir}")
        return False
    
    base_prefix = output_prefix if output_prefix else f"{prefix}/{model_type}"
    
    logger.info(f"Uploading models from {hub_dir} to s3://{bucket}/{base_prefix}")
    
    uploaded = 0
    for local_file in hub_dir.rglob('*'):
        if local_file.is_file():
            relative_path = local_file.relative_to(hub_dir)
            s3_key = f"{base_prefix}/{relative_path}"
            
            try:
                logger.debug(f"Uploading: {s3_key}")
                s3_client.upload_file(str(local_file), bucket, s3_key)
                uploaded += 1
            except Exception as e:
                logger.error(f"Failed to upload {s3_key}: {str(e)}")
                raise
    
    logger.info(f"Uploaded {uploaded} files to S3")
    return True


def main():
    load_dotenv()
    args = parse_arguments()
    
    hf_token = args.hf_token
    models = [m.strip() for m in args.model_names.split(',')]
    
    logger.info("=" * 60)
    logger.info("HuggingFace Models Download and Upload to S3")
    logger.info("=" * 60)
    logger.info(f"S3 Bucket: {args.bucket}")
    logger.info(f"S3 Prefix: {args.prefix}")
    logger.info(f"Model Type: {args.model_type}")
    logger.info(f"Models: {', '.join(models)}")
    if args.output_prefix:
        logger.info(f"Output Prefix: {args.output_prefix}")
    logger.info("=" * 60)
    
    try:
        session = boto3.Session(region_name=args.region)
        s3_client = session.client('s3')
        
        logger.info(f"Verifying S3 bucket: {args.bucket}")
        s3_client.head_bucket(Bucket=args.bucket)
        logger.info("Bucket accessible")
        
        logger.info("Downloading models...")
        download_models(models, hf_token)
        
        logger.info("Uploading models to S3...")
        upload_models_to_s3(s3_client, args.bucket, args.prefix, args.model_type, args.output_prefix)
        
        output_prefix = args.output_prefix if args.output_prefix else f"{args.prefix}/{args.model_type}"
        logger.info("Setup complete")
        logger.info(f"Models uploaded to: s3://{args.bucket}/{output_prefix}")
        logger.info("To use in your jobs, reference the S3 path:")
        logger.info(f"s3://{args.bucket}/{output_prefix}")
        
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()

# python download_models.py --bucket ml-pipeline-ml-models --model-type pyannote --model-names pyannote/speaker-diarization-3.1
# python download_models.py --bucket ml-pipeline-ml-models --model-type whisper --model-names openai/whisper-small.en
