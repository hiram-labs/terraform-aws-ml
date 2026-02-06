#!/usr/bin/env python3
"""
Video Processor for AWS Batch

Extensible framework for FFmpeg operations on video/audio files.
Downloads inputs from S3, processes with FFmpeg, uploads outputs back.

Supported Operations:
- extract_audio: Extract audio with Whisper preprocessing (16kHz, mono, normalized)

To add new operations:
  1. Create a class inheriting from FFmpegOperation
  2. Implement build_command() method with ffmpeg args
  3. Add to OPERATIONS registry

SNS Trigger Format:
{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/video_processor.py",
    "compute_type": "cpu",
    "operation": "extract_audio",
    "input_key": "videos/input.mp4",
    "output_key": "audio/output.wav",
    "args": {
      "sample_rate": "16000",
      "channels": "1",
      "normalize": "true"
    }
  }
}
"""

import os
import sys
import json
import boto3
import subprocess
import time
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
import tempfile
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'cpu')
S3_RETRY_ATTEMPTS = 3
S3_RETRY_DELAY = 2
MAX_INPUT_SIZE_GB = 10

s3_client = boto3.client('s3')


def s3_download_with_retry(bucket: str, key: str, filepath: str, max_retries: int = S3_RETRY_ATTEMPTS):
    """Download from S3 with exponential backoff retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading s3://{bucket}/{key} (attempt {attempt+1}/{max_retries})")
            s3_client.download_file(bucket, key, filepath)
            return
        except ClientError as e:
            if attempt < max_retries - 1:
                wait_time = S3_RETRY_DELAY * (2 ** attempt)
                logger.warning(f"S3 download failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"S3 download failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            raise


class FFmpegOperation(ABC):
    """Base class for FFmpeg operations"""
    
    format: str = 'wav'  # Default format, override in subclasses
    
    def __init__(self, args: Dict):
        self.args = args
    
    @abstractmethod
    def build_command(self, input_file: str, output_file: str) -> List[str]:
        """Build ffmpeg command arguments specific to this operation"""
        pass
    
    def execute(self, input_file: str, output_file: str) -> str:
        """Execute the ffmpeg operation with timing and error handling"""
        cmd = ['ffmpeg', '-i', input_file] + self.build_command(input_file, output_file) + ['-f', self.format, '-y', output_file]
        
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")
        t0 = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1-hour timeout
            elapsed = time.time() - t0
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error (exit code {result.returncode}): {result.stderr}")
                raise RuntimeError(f"FFmpeg operation failed: {result.stderr}")
            
            logger.info(f"FFmpeg completed in {elapsed:.1f}s")
            return output_file
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg operation timed out after 3600s")
            raise RuntimeError("FFmpeg operation timed out")
        except Exception as e:
            logger.error(f"FFmpeg execution error: {e}")
            raise


class ExtractAudioOperation(FFmpegOperation):
    """Extract audio from video"""
    
    def build_command(self, input_file: str, output_file: str) -> List[str]:
        sample_rate = self.args.get('sample_rate', '16000')
        channels = self.args.get('channels', '1')
        normalize = self.args.get('normalize', 'true').lower() == 'true'
        
        cmd = [
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', sample_rate,
            '-ac', channels,
        ]
        
        if normalize:
            cmd.extend([
                '-af', 'loudnorm=I=-20:TP=-1.5:LRA=11'
            ])
        
        return cmd


# Registry of available operations
OPERATIONS: Dict[str, type] = {
    'extract_audio': ExtractAudioOperation,
}


class FFmpegProcessor:
    """Main processor for FFmpeg jobs"""
    
    def __init__(self, job_def: Dict):
        self.job_def = job_def
        self.data = job_def.get('data', {})
        self.operation_type = self.data.get('operation', 'extract_audio')
        self.input_key = self.data.get('input_key')
        self.output_key = self.data.get('output_key')
        self.args = self.data.get('args', {})
        
        # Get bucket configs from payload first, then fall back to environment variables
        self.input_bucket = job_def.get('input_bucket') or INPUT_BUCKET
        self.output_bucket = job_def.get('output_bucket') or OUTPUT_BUCKET
    
    def validate(self):
        """Validate job configuration"""
        if not self.input_key or not self.output_key:
            raise ValueError("Missing input_key or output_key in job definition")
        
        if self.operation_type not in OPERATIONS:
            raise ValueError(f"Unknown operation: {self.operation_type}")
    
    def process(self) -> Dict:
        """Execute the FFmpeg operation"""
        try:
            self.validate()
            
            logger.info(f"Job started at {datetime.now().isoformat()}")
            logger.info(f"Operation: {self.operation_type}")
            logger.info(f"Compute type: {COMPUTE_TYPE}")
            logger.info(f"Input: s3://{self.input_bucket}/{self.input_key}")
            logger.info(f"Output: s3://{self.output_bucket}/{self.output_key}")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                local_input = os.path.join(tmpdir, 'input_file')
                local_output = os.path.join(tmpdir, 'output_file')
                
                logger.info("Downloading input from S3...")
                s3_download_with_retry(self.input_bucket, self.input_key, local_input)
                logger.info("Input downloaded successfully")
                
                # Validate input file
                input_size = Path(local_input).stat().st_size
                if input_size == 0:
                    raise ValueError(f"Downloaded input file is empty (0 bytes)")
                if input_size > MAX_INPUT_SIZE_GB * 1024 * 1024 * 1024:
                    raise ValueError(f"Input file too large ({input_size/1e9:.1f}GB, max {MAX_INPUT_SIZE_GB}GB)")
                logger.info(f"Input file size: {input_size / 1024 / 1024:.1f}MB")
                
                operation_class = OPERATIONS[self.operation_type]
                operation = operation_class(self.args)
                operation.execute(local_input, local_output)
                
                # Validate output file
                output_size = Path(local_output).stat().st_size
                if output_size == 0:
                    raise ValueError(f"Output file is empty (0 bytes) - FFmpeg produced no output")
                logger.info(f"Output file size: {output_size / 1024 / 1024:.1f}MB")
                
                logger.info("Uploading output to S3...")
                for attempt in range(S3_RETRY_ATTEMPTS):
                    try:
                        s3_client.upload_file(local_output, self.output_bucket, self.output_key)
                        break
                    except ClientError as e:
                        if attempt < S3_RETRY_ATTEMPTS - 1:
                            wait_time = S3_RETRY_DELAY * (2 ** attempt)
                            logger.warning(f"S3 upload failed: {e}. Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"S3 upload failed after {S3_RETRY_ATTEMPTS} attempts: {e}")
                            raise
                logger.info("Output uploaded successfully")
                
                result = {
                    'status': 'success',
                    'operation': self.operation_type,
                    'input_key': self.input_key,
                    'output_key': self.output_key,
                    'input_size_mb': round(input_size / 1024 / 1024, 2),
                    'output_size_mb': round(output_size / 1024 / 1024, 2),
                    'timestamp': datetime.now().isoformat(),
                    'parameters': self.args
                }
                
                logger.info(json.dumps(result, indent=2))
                return result
                
        except Exception as e:
            logger.error(f"Job failed: {str(e)}", exc_info=True)
            error_result = {
                'status': 'failed',
                'operation': self.operation_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            logger.error(json.dumps(error_result, indent=2))
            raise


def main():
    """Main execution function"""
    job_def = json.loads(sys.stdin.read())
    processor = FFmpegProcessor(job_def)
    
    try:
        processor.process()
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
