#!/usr/bin/env python3
"""
Download Processor for AWS Batch

Extensible framework for downloading media from various sources.
Downloads media to local temp, uploads to S3 for downstream processing.

Supported Operations:
- download_youtube: Download video/audio from YouTube

To add new operations:
  1. Create a class inheriting from MediaDownloadOperation
  2. Implement download() method
  3. Add to OPERATIONS registry

SNS Trigger Format:
{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/download_processor.py",
    "compute_type": "cpu",
    "operation": "download_youtube",
    "output_key": "media/output.mp4",
    "args": {
      "source_url": "https://www.youtube.com/watch?v=...",
      "output_format": "mp4",
      "quality": "best",
            "cookies_s3_key": "cookies/youtube_cookies.txt",
            "cookies_bucket": "my-private-bucket"
    }
  }
}

The cookies_s3_key field should point to a Netscape-format cookies file in S3.
Use cookies_bucket to override the bucket (defaults to OUTPUT_BUCKET).
"""

import os
import sys
import json
import boto3
import subprocess
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict
from botocore.exceptions import ClientError
import tempfile
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'cpu')
S3_RETRY_ATTEMPTS = 3
S3_RETRY_DELAY = 2
MAX_OUTPUT_SIZE_GB = 50
DOWNLOAD_TIMEOUT_SECONDS = 7200

s3_client = boto3.client('s3')


def s3_upload_with_retry(bucket: str, key: str, filepath: str, max_retries: int = S3_RETRY_ATTEMPTS):
    """Upload to S3 with exponential backoff retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Uploading s3://{bucket}/{key} (attempt {attempt+1}/{max_retries})")
            s3_client.upload_file(filepath, bucket, key)
            return
        except ClientError as e:
            if attempt < max_retries - 1:
                wait_time = S3_RETRY_DELAY * (2 ** attempt)
                logger.warning(f"S3 upload failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"S3 upload failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            raise


class MediaDownloadOperation(ABC):
    """Base class for media download operations"""
    
    def __init__(self, args: Dict):
        self.args = args
        self.source_url = args.get('source_url')
    
    @abstractmethod
    def download(self, output_file: str) -> str:
        """Download media and return output file path"""
        pass


class YouTubeDownloadOperation(MediaDownloadOperation):
    """Download video/audio from YouTube using yt-dlp"""
    
    def download(self, output_file: str) -> str:
        """Download from YouTube"""
        quality = self.args.get('quality', 'best')
        output_format = self.args.get('output_format', 'mp4')
        cookies_s3_key = self.args.get('cookies_s3_key')
        cookies_bucket = self.args.get('cookies_bucket')
        
        if cookies_s3_key and not cookies_bucket:
            raise ValueError("cookies_bucket is required when cookies_s3_key is provided")
        
        if not self.source_url:
            raise ValueError("source_url is required for YouTube download")
        
        logger.info(f"Downloading from YouTube: {self.source_url}")
        logger.info(f"Quality: {quality}, Format: {output_format}")
        
        cookies_file = None
        if cookies_s3_key:
            try:
                efs_cookies_path = Path('/opt/cookies') / cookies_s3_key.replace('/', '_')
                efs_cookies_path.parent.mkdir(parents=True, exist_ok=True)
                
                if efs_cookies_path.exists():
                    logger.info(f"Using cached cookies from {efs_cookies_path}")
                    cookies_file = str(efs_cookies_path)
                else:
                    efs_cookies_path.parent.mkdir(parents=True, exist_ok=True)
                    s3_client.download_file(cookies_bucket, cookies_s3_key, str(efs_cookies_path))
                    logger.info(f"Downloaded and cached cookies from s3://{cookies_bucket}/{cookies_s3_key} to {efs_cookies_path}")
                    cookies_file = str(efs_cookies_path)
            except Exception as e:
                logger.warning(f"Failed to download cookies from S3: {e}")
                cookies_file = None
        
        format_spec = self._get_format_spec(quality, output_format)
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--progress',
            '-f', format_spec,
            '-o', output_file,
            '--no-playlist',
            '--socket-timeout', '30',
            '--retries', '3',
            '--fragment-retries', '3',
        ]
        
        if cookies_file:
            cmd.extend(['--cookies', cookies_file])
        
        cmd.append(self.source_url)
        
        logger.info(f"Running: {' '.join(cmd)}")
        t0 = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            elapsed = time.time() - t0
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error (exit code {result.returncode}): {result.stderr}")
                raise RuntimeError(f"YouTube download failed: {result.stderr}")
            
            output_path = Path(output_file)
            if not output_path.exists():
                parent_dir = output_path.parent if output_path.parent.exists() else Path('.')
                base_name = output_path.stem
                matches = list(parent_dir.glob(f"{base_name}.*"))
                if matches:
                    matches[0].rename(output_file)
                    logger.info(f"Renamed {matches[0]} to {output_file}")
                else:
                    raise RuntimeError("Download completed but output file not found")
            
            logger.info(f"Download completed in {elapsed:.1f}s")
            return output_file
            
        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out after {DOWNLOAD_TIMEOUT_SECONDS}s")
            raise RuntimeError("YouTube download timed out")
        except Exception as e:
            logger.error(f"Download error: {e}")
            raise
    
    def _get_format_spec(self, quality: str, output_format: str) -> str:
        """Build yt-dlp format specification"""
        if output_format == 'mp4':
            if quality == 'best':
                return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
            elif quality == 'high':
                return 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best'
            elif quality == 'medium':
                return 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/bestvideo+bestaudio/best'
            else:
                return 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/bestvideo+bestaudio/best'
        elif output_format == 'webm':
            if quality == 'best':
                return 'bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo+bestaudio/best'
            else:
                return 'bestvideo+bestaudio/best'
        elif output_format == 'audio':
            return 'bestaudio/best'
        else:
            return 'bestvideo+bestaudio/best'


# Registry of available operations
OPERATIONS: Dict[str, type] = {
    'download_youtube': YouTubeDownloadOperation,
}


class MediaDownloader:
    """Main processor for media download jobs"""
    
    def __init__(self, job_def: Dict):
        self.job_def = job_def
        self.data = job_def.get('data', {})
        self.operation_type = self.data.get('operation', 'download_youtube')
        self.output_key = self.data.get('output_key')
        self.args = self.data.get('args', {})
        
        self.output_bucket = job_def.get('output_bucket') or OUTPUT_BUCKET
    
    def validate(self):
        """Validate job configuration"""
        if not self.output_key:
            raise ValueError("Missing output_key in job definition")
        
        if self.operation_type not in OPERATIONS:
            raise ValueError(f"Unknown operation: {self.operation_type}")
        
        if not self.args.get('source_url'):
            raise ValueError("Missing source_url in args")
    
    def process(self) -> Dict:
        """Execute the media download operation"""
        try:
            self.validate()
            
            logger.info(f"Job started at {datetime.now().isoformat()}")
            logger.info(f"Operation: {self.operation_type}")
            logger.info(f"Compute type: {COMPUTE_TYPE}")
            logger.info(f"Output: s3://{self.output_bucket}/{self.output_key}")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                local_output = os.path.join(tmpdir, 'media_file')
                
                operation_class = OPERATIONS[self.operation_type]
                operation = operation_class(self.args)
                
                logger.info("Starting media download...")
                t0 = time.time()
                operation.download(local_output)
                download_time = time.time() - t0
                
                output_size = Path(local_output).stat().st_size
                if output_size == 0:
                    raise ValueError(f"Downloaded file is empty (0 bytes)")
                if output_size > MAX_OUTPUT_SIZE_GB * 1024 * 1024 * 1024:
                    raise ValueError(f"Downloaded file too large ({output_size/1e9:.1f}GB, max {MAX_OUTPUT_SIZE_GB}GB)")
                
                logger.info(f"Output file size: {output_size / 1024 / 1024:.1f}MB")
                
                logger.info("Uploading to S3...")
                s3_upload_with_retry(self.output_bucket, self.output_key, local_output)
                logger.info("Upload completed successfully")
                
                result = {
                    'status': 'success',
                    'operation': self.operation_type,
                    'output_key': self.output_key,
                    'source_url': self.args.get('source_url'),
                    'file_size_mb': round(output_size / 1024 / 1024, 2),
                    'download_time_sec': round(download_time, 2),
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
    downloader = MediaDownloader(job_def)
    
    try:
        downloader.process()
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
