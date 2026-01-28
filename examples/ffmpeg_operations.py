#!/usr/bin/env python3
"""
FFmpeg Operations Script for AWS Batch

Demonstrates common ffmpeg operations triggered via SNS with customizable parameters.
Supports the following operations:
  1. convert    - Convert video format (e.g., mp4 to webm)
  2. scale      - Resize/scale video resolution
  3. extract    - Extract audio from video
  4. concat     - Concatenate multiple videos
  5. compress   - Compress/adjust bitrate

Usage:
  Trigger via SNS with JSON payload containing operation and parameters
  
Example SNS Messages:
  
  1. Convert MP4 to WebM:
     {
       "trigger_type": "batch_job",
       "data": {
         "script_key": "jobs/ffmpeg_operations.py",
         "compute_type": "cpu",
         "operation": "convert",
         "input_key": "videos/input.mp4",
         "output_key": "videos/output.webm",
         "args": {
           "codec": "libvpx-vp9",
           "crf": "30"
         }
       }
     }
     
  2. Scale video to 1280x720:
     {
       "trigger_type": "batch_job",
       "data": {
         "script_key": "jobs/ffmpeg_operations.py",
         "compute_type": "cpu",
         "operation": "scale",
         "input_key": "videos/input.mp4",
         "output_key": "videos/scaled.mp4",
         "args": {
           "width": "1280",
           "height": "720",
           "scale_filter": "scale=1280:720:force_original_aspect_ratio=decrease"
         }
       }
     }
     
  3. Extract audio to MP3:
     {
       "trigger_type": "batch_job",
       "data": {
         "script_key": "jobs/ffmpeg_operations.py",
         "compute_type": "cpu",
         "operation": "extract",
         "input_key": "videos/input.mp4",
         "output_key": "audio/output.mp3",
         "args": {
           "audio_codec": "libmp3lame",
           "audio_bitrate": "192k"
         }
       }
     }
     
  4. Concatenate videos (list files in input_key path):
     {
       "trigger_type": "batch_job",
       "data": {
         "script_key": "jobs/ffmpeg_operations.py",
         "compute_type": "cpu",
         "operation": "concat",
         "input_key": "videos/concat_list.txt",
         "output_key": "videos/concatenated.mp4",
         "args": {
           "codec": "libx264",
           "preset": "medium"
         }
       }
     }
     
  5. Compress with custom bitrate:
     {
       "trigger_type": "batch_job",
       "data": {
         "script_key": "jobs/ffmpeg_operations.py",
         "compute_type": "cpu",
         "operation": "compress",
         "input_key": "videos/input.mp4",
         "output_key": "videos/compressed.mp4",
         "args": {
           "video_bitrate": "1500k",
           "audio_bitrate": "128k",
           "preset": "medium"
         }
       }
     }
"""

import json
import os
import subprocess
import sys
import logging
from pathlib import Path
import boto3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS clients
s3_client = boto3.client('s3')

# Environment variables from Batch job
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
INPUT_BUCKET = os.environ.get('ML_INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('ML_OUTPUT_BUCKET')
WORKSPACE = '/workspace'
OUTPUT_DIR = f'{WORKSPACE}/output'

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_config_from_file():
    """
    Retrieve operation config from environment or file.
    Config should be passed as environment variables or via config file.
    """
    config_file = f'{WORKSPACE}/config.json'
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get('data', {})
    
    # Fallback to environment variables
    return {}


def download_from_s3(bucket, key, local_path):
    """Download file from S3."""
    logger.info(f'Downloading s3://{bucket}/{key} to {local_path}')
    try:
        s3_client.download_file(bucket, key, local_path)
        logger.info(f'Successfully downloaded {key}')
        return True
    except Exception as e:
        logger.error(f'Failed to download {key}: {str(e)}')
        return False


def upload_to_s3(local_path, bucket, key):
    """Upload file to S3."""
    logger.info(f'Uploading {local_path} to s3://{bucket}/{key}')
    try:
        s3_client.upload_file(local_path, bucket, key)
        logger.info(f'Successfully uploaded to {key}')
        return True
    except Exception as e:
        logger.error(f'Failed to upload {key}: {str(e)}')
        return False


def run_ffmpeg_command(command):
    """Execute ffmpeg command."""
    logger.info(f'Running command: {" ".join(command)}')
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3600
        )
        if result.returncode != 0:
            logger.error(f'FFmpeg error: {result.stderr}')
            return False
        logger.info('FFmpeg command completed successfully')
        return True
    except subprocess.TimeoutExpired:
        logger.error('FFmpeg command timed out (1 hour limit)')
        return False
    except Exception as e:
        logger.error(f'Failed to run ffmpeg: {str(e)}')
        return False


def operation_convert(config):
    """
    Convert video format.
    Args: codec, crf, preset
    """
    operation = 'convert'
    logger.info(f'Starting {operation} operation')
    
    input_key = config.get('input_key')
    output_key = config.get('output_key')
    args = config.get('args', {})
    
    if not input_key or not output_key:
        logger.error('Missing input_key or output_key')
        return False
    
    # Download input
    input_file = f'{WORKSPACE}/input{Path(input_key).suffix}'
    if not download_from_s3(INPUT_BUCKET, input_key, input_file):
        return False
    
    # Prepare output
    output_file = f'{OUTPUT_DIR}/output{Path(output_key).suffix}'
    
    # Build ffmpeg command
    codec = args.get('codec', 'libx264')
    crf = args.get('crf', '28')
    
    command = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', codec,
        '-crf', crf,
        '-c:a', 'aac',
        '-y',
        output_file
    ]
    
    if not run_ffmpeg_command(command):
        return False
    
    # Upload output
    return upload_to_s3(output_file, OUTPUT_BUCKET, output_key)


def operation_scale(config):
    """
    Scale/resize video.
    Args: width, height, scale_filter
    """
    operation = 'scale'
    logger.info(f'Starting {operation} operation')
    
    input_key = config.get('input_key')
    output_key = config.get('output_key')
    args = config.get('args', {})
    
    if not input_key or not output_key:
        logger.error('Missing input_key or output_key')
        return False
    
    # Download input
    input_file = f'{WORKSPACE}/input{Path(input_key).suffix}'
    if not download_from_s3(INPUT_BUCKET, input_key, input_file):
        return False
    
    # Prepare output
    output_file = f'{OUTPUT_DIR}/output{Path(output_key).suffix}'
    
    # Build scale filter
    if 'scale_filter' in args:
        scale_filter = args['scale_filter']
    else:
        width = args.get('width', '1280')
        height = args.get('height', '720')
        scale_filter = f'scale={width}:{height}:force_original_aspect_ratio=decrease'
    
    command = [
        'ffmpeg',
        '-i', input_file,
        '-vf', scale_filter,
        '-c:a', 'copy',
        '-y',
        output_file
    ]
    
    if not run_ffmpeg_command(command):
        return False
    
    # Upload output
    return upload_to_s3(output_file, OUTPUT_BUCKET, output_key)


def operation_extract(config):
    """
    Extract audio from video.
    Args: audio_codec, audio_bitrate
    """
    operation = 'extract'
    logger.info(f'Starting {operation} operation')
    
    input_key = config.get('input_key')
    output_key = config.get('output_key')
    args = config.get('args', {})
    
    if not input_key or not output_key:
        logger.error('Missing input_key or output_key')
        return False
    
    # Download input
    input_file = f'{WORKSPACE}/input{Path(input_key).suffix}'
    if not download_from_s3(INPUT_BUCKET, input_key, input_file):
        return False
    
    # Prepare output
    output_file = f'{OUTPUT_DIR}/output{Path(output_key).suffix}'
    
    # Build ffmpeg command
    audio_codec = args.get('audio_codec', 'libmp3lame')
    audio_bitrate = args.get('audio_bitrate', '192k')
    
    command = [
        'ffmpeg',
        '-i', input_file,
        '-q:a', '0',
        '-map', 'a',
        '-c:a', audio_codec,
        '-b:a', audio_bitrate,
        '-y',
        output_file
    ]
    
    if not run_ffmpeg_command(command):
        return False
    
    # Upload output
    return upload_to_s3(output_file, OUTPUT_BUCKET, output_key)


def operation_concat(config):
    """
    Concatenate multiple videos.
    input_key should point to a concat_list.txt file in S3 with format:
    file '/path/to/file1.mp4'
    file '/path/to/file2.mp4'
    
    Args: codec, preset
    """
    operation = 'concat'
    logger.info(f'Starting {operation} operation')
    
    input_key = config.get('input_key')
    output_key = config.get('output_key')
    args = config.get('args', {})
    
    if not input_key or not output_key:
        logger.error('Missing input_key or output_key')
        return False
    
    # Download concat list
    concat_file = f'{WORKSPACE}/concat_list.txt'
    if not download_from_s3(INPUT_BUCKET, input_key, concat_file):
        return False
    
    # Prepare output
    output_file = f'{OUTPUT_DIR}/output{Path(output_key).suffix}'
    
    # Build ffmpeg command
    codec = args.get('codec', 'libx264')
    preset = args.get('preset', 'medium')
    
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c:v', codec,
        '-preset', preset,
        '-c:a', 'aac',
        '-y',
        output_file
    ]
    
    if not run_ffmpeg_command(command):
        return False
    
    # Upload output
    return upload_to_s3(output_file, OUTPUT_BUCKET, output_key)


def operation_compress(config):
    """
    Compress video with custom bitrate.
    Args: video_bitrate, audio_bitrate, preset
    """
    operation = 'compress'
    logger.info(f'Starting {operation} operation')
    
    input_key = config.get('input_key')
    output_key = config.get('output_key')
    args = config.get('args', {})
    
    if not input_key or not output_key:
        logger.error('Missing input_key or output_key')
        return False
    
    # Download input
    input_file = f'{WORKSPACE}/input{Path(input_key).suffix}'
    if not download_from_s3(INPUT_BUCKET, input_key, input_file):
        return False
    
    # Prepare output
    output_file = f'{OUTPUT_DIR}/output{Path(output_key).suffix}'
    
    # Build ffmpeg command
    video_bitrate = args.get('video_bitrate', '1500k')
    audio_bitrate = args.get('audio_bitrate', '128k')
    preset = args.get('preset', 'medium')
    
    command = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-b:v', video_bitrate,
        '-preset', preset,
        '-c:a', 'aac',
        '-b:a', audio_bitrate,
        '-y',
        output_file
    ]
    
    if not run_ffmpeg_command(command):
        return False
    
    # Upload output
    return upload_to_s3(output_file, OUTPUT_BUCKET, output_key)


def main():
    """Main entry point."""
    try:
        # Get configuration
        config = get_config_from_file()
        
        if not config:
            logger.error('No configuration found')
            return 1
        
        operation = config.get('operation')
        
        if not operation:
            logger.error('No operation specified')
            return 1
        
        logger.info(f'Processing operation: {operation}')
        logger.info(f'Configuration: {json.dumps(config, indent=2)}')
        
        # Route to appropriate operation
        operations = {
            'convert': operation_convert,
            'scale': operation_scale,
            'extract': operation_extract,
            'concat': operation_concat,
            'compress': operation_compress,
        }
        
        if operation not in operations:
            logger.error(f'Unknown operation: {operation}')
            logger.error(f'Available operations: {", ".join(operations.keys())}')
            return 1
        
        # Execute operation
        success = operations[operation](config)
        
        if success:
            logger.info(f'Operation {operation} completed successfully')
            return 0
        else:
            logger.error(f'Operation {operation} failed')
            return 1
            
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}', exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
