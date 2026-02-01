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
from abc import ABC, abstractmethod
from datetime import datetime
import tempfile
import logging
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'cpu')

s3_client = boto3.client('s3')


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
        """Execute the ffmpeg operation"""
        cmd = ['ffmpeg', '-i', input_file] + self.build_command(input_file, output_file) + ['-f', self.format, '-y', output_file]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg operation failed: {result.stderr}")
        
        logger.info("Operation completed successfully")
        return output_file


class ExtractAudioOperation(FFmpegOperation):
    """Extract audio from video with preprocessing for Whisper transcription"""
    
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
            logger.info(f"Input: s3://{INPUT_BUCKET}/{self.input_key}")
            logger.info(f"Output: s3://{OUTPUT_BUCKET}/{self.output_key}")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                local_input = os.path.join(tmpdir, 'input_file')
                local_output = os.path.join(tmpdir, 'output_file')
                
                logger.info("Downloading input from S3...")
                s3_client.download_file(INPUT_BUCKET, self.input_key, local_input)
                logger.info("Input downloaded successfully")
                
                operation_class = OPERATIONS[self.operation_type]
                operation = operation_class(self.args)
                operation.execute(local_input, local_output)
                
                logger.info("Uploading output to S3...")
                s3_client.upload_file(local_output, OUTPUT_BUCKET, self.output_key)
                logger.info("Output uploaded successfully")
                
                result = {
                    'status': 'success',
                    'operation': self.operation_type,
                    'input_key': self.input_key,
                    'output_key': self.output_key,
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
