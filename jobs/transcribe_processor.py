#!/usr/bin/env python3
"""
Transcribe Processor for AWS Batch

Extensible framework for audio transcribe with speaker diarization.
Downloads audio from S3, loads pre-downloaded models from S3, runs transcribe and 
speaker identification, saves results.

Supported Operations:
- transcribe_audio: Convert audio to text with speaker labels (high-speed, speaker-aware)

To add new operations:
  1. Create a class inheriting from TranscribeOperation
  2. Implement process() method
  3. Add to OPERATIONS registry

SNS Trigger Format:
{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/transcribe_processor.py",
    "compute_type": "gpu",
    "operation": "transcribe_audio",
    "input_key": "audio/input.wav",
    "output_key": "transcribe/output.json",
    "args": {
      "language": "en",
      "output_format": "json",
      "whisper_model": "guillaumekln/faster-whisper-small.en",
      "pyannote_model": "pyannote/speaker-diarization-community-1"
    }
  }
}

Output formats: json, txt, vtt, srt
"""

import os
import sys
import json
import boto3
import torch
import zipfile
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from datetime import datetime
import tempfile
import logging
from typing import Dict, List
from pathlib import Path
from abc import ABC, abstractmethod

# Disable HuggingFace Hub online access - use only local models
os.environ['HF_HUB_OFFLINE'] = '1'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
MODELS_BUCKET = os.environ.get('MODELS_BUCKET')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'cpu')

s3_client = boto3.client('s3')


class TranscribeOperation(ABC):
    """Base class for transcribe operations"""
    
    def __init__(self, args: Dict, models_bucket: str = None):
        self.args = args
        self.models_bucket = models_bucket or MODELS_BUCKET
    
    @abstractmethod
    def process(self, audio_file: str, tmpdir: str) -> Dict:
        """Process audio file and return transcribe results"""
        pass


class TranscribeWithDiarizationOperation(TranscribeOperation):
    """Transcribe audio with speaker diarization using Faster-Whisper and pyannote"""
    
    def process(self, audio_file: str, tmpdir: str) -> Dict:
        language = self.args.get('language', 'en')
        output_format = self.args.get('output_format', 'json')
        whisper_model_name = self.args.get('whisper_model', 'guillaumekln/faster-whisper-small.en')
        pyannote_model_name = self.args.get('pyannote_model', 'pyannote/speaker-diarization-community-1')
        
        device = self._get_device()
        compute_type = self._get_compute_type(device)
        
        logger.info("Downloading models from S3...")
        whisper_model_path = self._download_model_from_s3(tmpdir, whisper_model_name, 'whisper')
        pyannote_model_path = self._download_model_from_s3(tmpdir, pyannote_model_name, 'pyannote')
        
        logger.info("Starting transcribe and speaker diarization...")
        transcribe_result = self._transcribe_audio(audio_file, whisper_model_path, language, compute_type)
        speakers = self._diarize_audio(audio_file, pyannote_model_path)
        
        segments = self._align_transcribe_with_speakers(transcribe_result, speakers)
        
        num_speakers = len(set(s['speaker'] for s in segments if s['speaker'] != 'Unknown'))
        
        return {
            'segments': segments,
            'summary': {
                'segments': len(segments),
                'speakers': num_speakers,
                'duration': segments[-1]['end'] if segments else 0,
                'language': language,
                'output_format': output_format
            }
        }
    
    def _get_device(self):
        """Determine compute device"""
        if torch.cuda.is_available() and COMPUTE_TYPE == 'gpu':
            device = torch.device('cuda')
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            device = torch.device('cpu')
        logger.info(f"Device: {device}")
        return device
    
    def _get_compute_type(self, device: torch.device) -> str:
        """Get compute type for faster-whisper"""
        return 'cuda' if device.type == 'cuda' else 'cpu'
    
    def _download_model_from_s3(self, tmpdir: str, model_name: str, model_type: str) -> str:
        """Download and extract model from S3 zip to EFS cache"""
        bucket = self.models_bucket
        if not bucket:
            raise ValueError("MODELS_BUCKET environment variable is not set")
        model_key = model_name.replace('/', '-')
        zip_key = f"models/{model_type}/{model_key}.zip"
        efs_model_path = Path('/opt/models') / model_type / model_key
        
        if efs_model_path.exists():
            logger.info(f"Model {model_name} already cached at {efs_model_path}")
        else:
            logger.info(f"Downloading {model_type} model '{model_name}' from s3://{bucket}/{zip_key}")
            
            # Download zip
            zip_local = Path(tmpdir) / f"{model_type}_{model_key}.zip"
            s3_client.download_file(bucket, zip_key, str(zip_local))
            
            # Extract to EFS
            efs_model_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_local, 'r') as zip_ref:
                zip_ref.extractall(efs_model_path)
            
            zip_local.unlink()
            logger.info(f"Extracted model to {efs_model_path}")

        snapshots_dir = efs_model_path / 'snapshots'
        if snapshots_dir.exists():
            snapshot_dirs = list(snapshots_dir.iterdir())
            if snapshot_dirs:
                return str(snapshot_dirs[0])
        raise RuntimeError(f"No snapshot directory found for whisper model {model_name}")
    
    def _transcribe_audio(self, audio_file: str, model_path: str, language: str = 'en', compute_type: str = 'cpu') -> List[Dict]:
        """Transcribe audio using Faster-Whisper with local model"""
        logger.info(f"Loading Faster-Whisper model from: {model_path}")
        model = WhisperModel(model_path, device=compute_type)
        
        logger.info(f"Transcribing audio: {audio_file}")
        segments, info = model.transcribe(audio_file, language=language)
        
        result = []
        for segment in segments:
            result.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip()
            })
        
        logger.info(f"Transcribe complete: {len(result)} segments")
        return result
    
    def _diarize_audio(self, audio_file: str, model_path: str) -> List[Dict]:
        logger.info(f"Loading pyannote model from: {model_path}")
        
        pipeline = Pipeline.from_pretrained(model_path, use_auth_token=False)
        
        if torch.cuda.is_available() and COMPUTE_TYPE == 'gpu':
            pipeline = pipeline.to(torch.device('cuda'))
        
        logger.info("Running speaker diarization")
        diarization = pipeline(audio_file)
        
        speakers = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        logger.info(f"Diarization complete: {len(set(s['speaker'] for s in speakers))} speakers detected")
        return speakers
    
    def _align_transcribe_with_speakers(self, transcribe_result: List[Dict], speakers: List[Dict]) -> List[Dict]:
        """Merge transcribe segments with speaker labels"""
        result = []
        
        for trans_seg in transcribe_result:
            trans_start = trans_seg['start']
            trans_end = trans_seg['end']
            
            speaker_labels = set()
            for speaker_seg in speakers:
                spk_start = speaker_seg['start']
                spk_end = speaker_seg['end']
                
                if spk_start < trans_end and spk_end > trans_start:
                    speaker_labels.add(speaker_seg['speaker'])
            
            speaker = ', '.join(sorted(speaker_labels)) if speaker_labels else 'Unknown'
            
            result.append({
                'start': trans_start,
                'end': trans_end,
                'speaker': speaker,
                'text': trans_seg['text']
            })
        
        return result


# Registry of available operations
OPERATIONS: Dict[str, type] = {
    'transcribe_audio': TranscribeWithDiarizationOperation,
}


def format_output(segments: List[Dict], output_format: str = 'json') -> str:
    """Format output in requested format"""
    if output_format == 'json':
        return json.dumps(segments, indent=2)
    elif output_format == 'txt':
        lines = []
        for seg in segments:
            lines.append(f"[{seg['speaker']}] {seg['text']}")
        return '\n'.join(lines)
    elif output_format == 'vtt':
        lines = ['WEBVTT\n']
        for seg in segments:
            start = format_timestamp(seg['start'])
            end = format_timestamp(seg['end'])
            speaker = seg['speaker']
            text = seg['text']
            lines.append(f"{start} --> {end}")
            lines.append(f"{speaker}\n{text}\n")
        return '\n'.join(lines)
    elif output_format == 'srt':
        lines = []
        for i, seg in enumerate(segments, 1):
            start = format_timestamp_srt(seg['start'])
            end = format_timestamp_srt(seg['end'])
            speaker = seg['speaker']
            text = seg['text']
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(f"[{speaker}]\n{text}\n")
        return '\n'.join(lines)
    else:
        return json.dumps(segments, indent=2)


def format_timestamp(seconds: float) -> str:
    """Format timestamp for VTT (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_timestamp_srt(seconds: float) -> str:
    """Format timestamp for SRT (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class TranscribeProcessor:
    """Main processor for transcribe jobs"""
    
    def __init__(self, job_def: Dict):
        self.job_def = job_def
        self.data = job_def.get('data', {})
        self.operation_type = self.data.get('operation', 'transcribe_audio')
        self.input_key = self.data.get('input_key')
        self.output_key = self.data.get('output_key')
        self.args = self.data.get('args', {})
        
        # Get bucket configs from payload first, then fall back to environment variables
        self.input_bucket = job_def.get('input_bucket') or INPUT_BUCKET
        self.output_bucket = job_def.get('output_bucket') or OUTPUT_BUCKET
        self.models_bucket = job_def.get('models_bucket') or MODELS_BUCKET
    
    def validate(self):
        """Validate job configuration"""
        if not self.input_key or not self.output_key:
            raise ValueError("Missing input_key or output_key in job definition")
        
        if self.operation_type not in OPERATIONS:
            raise ValueError(f"Unknown operation: {self.operation_type}")
    
    def process(self) -> Dict:
        """Execute the transcribe operation"""
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
                
                logger.info("Downloading audio from S3...")
                s3_client.download_file(self.input_bucket, self.input_key, local_input)
                logger.info("Audio downloaded successfully")
                
                operation_class = OPERATIONS[self.operation_type]
                operation = operation_class(self.args, self.models_bucket)
                result = operation.process(local_input, tmpdir)
                
                output_format = self.args.get('output_format', 'json')
                output_text = format_output(result['segments'], output_format)
                
                with open(local_output, 'w') as f:
                    f.write(output_text)
                
                logger.info("Uploading transcript to S3...")
                s3_client.upload_file(local_output, self.output_bucket, self.output_key)
                logger.info("Transcript uploaded successfully")
                
                success_result = {
                    'status': 'success',
                    'operation': self.operation_type,
                    'input_key': self.input_key,
                    'output_key': self.output_key,
                    'timestamp': datetime.now().isoformat(),
                    'parameters': self.args,
                    'summary': result['summary']
                }
                
                logger.info(json.dumps(success_result, indent=2))
                return success_result
                
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
    processor = TranscribeProcessor(job_def)
    
    try:
        processor.process()
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
