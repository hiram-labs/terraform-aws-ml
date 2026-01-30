#!/usr/bin/env python3
"""
Transcript Processor for AWS Batch

Transcribes WAV audio with speaker diarization using Faster-Whisper and pyannote.
Downloads audio from S3, loads pre-downloaded models from S3, runs transcription and 
speaker identification, saves results.

Supported Operations:
- transcribe: Convert audio to text with speaker labels (high-speed, speaker-aware)

Environment Variables:
  - INPUT_BUCKET: S3 bucket with audio files
  - OUTPUT_BUCKET: S3 bucket for transcription output
  - COMPUTE_TYPE: gpu or cpu

SNS Trigger Format:
{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/transcript_processor.py",
    "compute_type": "gpu",
    "operation": "transcribe",
    "input_key": "audio/output.wav",
    "output_key": "transcriptions/output.json",
    "args": {
      "language": "en",
      "output_format": "json",
      "whisper_model_s3_path": "s3://my-models-bucket/models/whisper-base",
      "pyannote_model_s3_path": "s3://my-models-bucket/models/pyannote-diarization"
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
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from datetime import datetime
import tempfile
import logging
from typing import Dict, List
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
COMPUTE_TYPE = os.environ.get('COMPUTE_TYPE', 'cpu')

s3_client = boto3.client('s3')


def get_device():
    """Determine compute device"""
    if torch.cuda.is_available() and COMPUTE_TYPE == 'gpu':
        device = torch.device('cuda')
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device('cpu')
    logger.info(f"Device: {device}")
    return device


def get_compute_type(device: torch.device) -> str:
    """Get compute type for faster-whisper"""
    return 'cuda' if device.type == 'cuda' else 'cpu'


def parse_s3_path(s3_path: str) -> tuple:
    """Parse S3 path into bucket and prefix"""
    if not s3_path.startswith('s3://'):
        raise ValueError(f"Invalid S3 path: {s3_path}")
    
    path = s3_path[5:]
    parts = path.split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    
    return bucket, prefix


def download_model_from_s3(tmpdir: str, s3_path: str, model_type: str) -> str:
    """Download model from S3 path to local cache directory"""
    if not s3_path:
        raise ValueError(f"{model_type} S3 path not provided in args")
    
    bucket, prefix = parse_s3_path(s3_path)
    logger.info(f"Downloading {model_type} from s3://{bucket}/{prefix}")
    
    models_cache = Path(tmpdir) / 'models_cache' / model_type
    models_cache.mkdir(parents=True, exist_ok=True)
    
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    file_count = 0
    for page in pages:
        if 'Contents' not in page:
            continue
        
        for obj in page['Contents']:
            key = obj['Key']
            relative_path = key[len(prefix):].lstrip('/')
            if not relative_path:
                continue
                
            local_path = models_cache / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"  Downloading: {key}")
            s3_client.download_file(bucket, key, str(local_path))
            file_count += 1
    
    if file_count == 0:
        raise RuntimeError(f"No {model_type} files found at s3://{bucket}/{prefix}")
    
    logger.info(f"✓ Downloaded {file_count} {model_type} files")
    return str(models_cache)


def transcribe_audio(audio_file: str, model_path: str, language: str = 'en', compute_type: str = 'cpu') -> List[Dict]:
    """Transcribe audio using Faster-Whisper with local model"""
    logger.info(f"Loading Faster-Whisper model from: {model_path}")
    model = WhisperModel(model_path, device=compute_type, local_files_only=True)
    
    logger.info(f"Transcribing audio: {audio_file}")
    segments, info = model.transcribe(audio_file, language=language)
    
    result = []
    for segment in segments:
        result.append({
            'start': segment.start,
            'end': segment.end,
            'text': segment.text.strip()
        })
    
    logger.info(f"Transcription complete: {len(result)} segments")
    return result


def diarize_audio(audio_file: str, model_path: str) -> List[Dict]:
    """Identify speakers using pyannote model from S3"""
    logger.info(f"Loading pyannote model from: {model_path}")
    
    pipeline = Pipeline.from_pretrained(model_path, use_auth_token=None)
    
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


def align_transcription_with_speakers(transcription: List[Dict], speakers: List[Dict]) -> List[Dict]:
    """Merge transcription segments with speaker labels"""
    result = []
    
    for trans_seg in transcription:
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


def main():
    """Main execution function"""
    job_def = json.loads(sys.stdin.read())
    data = job_def.get('data', {})
    
    input_key = data.get('input_key')
    output_key = data.get('output_key')
    args = data.get('args', {})
    
    if not input_key or not output_key:
        logger.error("Missing input_key or output_key")
        sys.exit(1)
    
    language = args.get('language', 'en')
    output_format = args.get('output_format', 'json')
    whisper_model_s3_path = args.get('whisper_model_s3_path')
    pyannote_model_s3_path = args.get('pyannote_model_s3_path')
    
    try:
        logger.info(f"Job started at {datetime.now().isoformat()}")
        logger.info(f"Compute type: {COMPUTE_TYPE}")
        logger.info(f"Input: s3://{INPUT_BUCKET}/{input_key}")
        logger.info(f"Output: s3://{OUTPUT_BUCKET}/{output_key}")
        
        device = get_device()
        compute_type = get_compute_type(device)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            local_input = os.path.join(tmpdir, 'input.wav')
            local_output = os.path.join(tmpdir, f'output.{output_format}')
            
            logger.info("Downloading audio from S3...")
            s3_client.download_file(INPUT_BUCKET, input_key, local_input)
            logger.info("Audio downloaded successfully")
            
            logger.info("Downloading models from S3...")
            whisper_model_path = download_model_from_s3(tmpdir, whisper_model_s3_path, 'whisper')
            pyannote_model_path = download_model_from_s3(tmpdir, pyannote_model_s3_path, 'pyannote')
            
            logger.info("Starting transcription and speaker diarization...")
            transcription = transcribe_audio(local_input, whisper_model_path, language, compute_type)
            speakers = diarize_audio(local_input, pyannote_model_path)
            
            segments = align_transcription_with_speakers(transcription, speakers)
            
            output_text = format_output(segments, output_format)
            
            with open(local_output, 'w') as f:
                f.write(output_text)
            
            logger.info("Uploading transcript to S3...")
            s3_client.upload_file(local_output, OUTPUT_BUCKET, output_key)
            logger.info("Transcript uploaded successfully")
            
            num_speakers = len(set(s['speaker'] for s in segments if s['speaker'] != 'Unknown'))
            
            success_result = {
                'status': 'success',
                'input_key': input_key,
                'output_key': output_key,
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'language': language,
                    'output_format': output_format,
                    'whisper_model': whisper_model_s3_path,
                    'pyannote_model': pyannote_model_s3_path
                },
                'summary': {
                    'segments': len(segments),
                    'speakers': num_speakers,
                    'duration': segments[-1]['end'] if segments else 0
                }
            }
            
            logger.info(json.dumps(success_result, indent=2))
            
    except Exception as e:
        logger.error(f"Job failed: {str(e)}", exc_info=True)
        error_result = {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        logger.error(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
