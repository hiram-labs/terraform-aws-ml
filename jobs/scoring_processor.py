#!/usr/bin/env python3
"""
Scoring Processor for AWS Batch

Scores transcript segments using LLM for downstream processing.
Supports pluggable LLM providers (Bedrock, OpenAI, Anthropic).

Supported Operations:
- score_virality: Score segments for viral potential
- score_trailer: Score segments for trailer/highlight suitability

To add new LLM providers:
  1. Create a class inheriting from LLMClient
  2. Implement complete() method
  3. Add to LLM_PROVIDERS registry

SNS Trigger Format:
{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/scoring_processor.py",
    "compute_type": "cpu",
    "operation": "score_virality",
    "input_key": "transcripts/input.json",
    "output_key": "scored/output.json",
    "args": {
      "llm_provider": "bedrock",
      "llm_model": "anthropic.claude-3-sonnet-20240229-v1:0"
    }
  }
}
"""

import os
import sys
import json
import boto3
import time
from botocore.exceptions import ClientError
from datetime import datetime
import tempfile
import logging
from typing import Dict, List
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
S3_RETRY_ATTEMPTS = 3
S3_RETRY_DELAY = 2

s3_client = boto3.client('s3')


def s3_download_with_retry(bucket: str, key: str, filepath: str, max_retries: int = S3_RETRY_ATTEMPTS):
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
                raise


def s3_upload_with_retry(filepath: str, bucket: str, key: str, max_retries: int = S3_RETRY_ATTEMPTS):
    for attempt in range(max_retries):
        try:
            logger.info(f"Uploading to s3://{bucket}/{key} (attempt {attempt+1}/{max_retries})")
            s3_client.upload_file(filepath, bucket, key)
            return
        except ClientError as e:
            if attempt < max_retries - 1:
                wait_time = S3_RETRY_DELAY * (2 ** attempt)
                logger.warning(f"S3 upload failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise


# =============================================================================
# LLM Client Abstraction
# =============================================================================

class LLMClient(ABC):
    """
    Base class for LLM providers
    
    Implement this interface for any LLM provider (Bedrock, OpenAI, Anthropic, self-hosted).
    
    Then register in LLM_PROVIDERS:
        LLM_PROVIDERS['my_provider'] = MyLLMClient
    """
    
    def __init__(self, model: str, **kwargs):
        self.model = model
    
    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Send prompt to LLM and return completion text.
        
        Args:
            prompt: Input prompt for the LLM
            max_tokens: Maximum tokens in response
            
        Returns:
            Completion text from LLM
        """
        pass


# Registry for LLM providers - add your implementations here
LLM_PROVIDERS: Dict[str, type] = {}


def get_llm_client(provider: str, model: str, **kwargs) -> LLMClient:
    """
    Factory function to get LLM client instance.
    
    Args:
        provider: Provider name (must be in LLM_PROVIDERS)
        model: Model identifier
        **kwargs: Additional arguments passed to provider constructor
        
    Returns:
        LLMClient instance
    """
    if provider not in LLM_PROVIDERS:
        raise ValueError(
            f"LLM provider '{provider}' not implemented. "
            f"Available providers: {list(LLM_PROVIDERS.keys()) or 'none'}. "
            f"Implement LLMClient and register in LLM_PROVIDERS."
        )
    return LLM_PROVIDERS[provider](model, **kwargs)


# =============================================================================
# Scoring Operations
# =============================================================================

class ScoringOperation(ABC):
    """Base class for scoring operations"""
    
    def __init__(self, args: Dict, llm_client: LLMClient):
        self.args = args
        self.llm = llm_client
    
    @abstractmethod
    def process(self, segments: List[Dict]) -> List[Dict]:
        """Score segments and return with added scores"""
        pass
    
    def _build_transcript_context(self, segments: List[Dict]) -> str:
        lines = []
        for i, seg in enumerate(segments):
            speaker = seg.get('speaker', 'Unknown')
            text = seg.get('text', '')
            lines.append(f"[{i}] [{speaker}] {text}")
        return "\n".join(lines)


class ViralityScoringOperation(ScoringOperation):
    """Score segments for viral potential"""
    
    PROMPT_TEMPLATE = """You are analyzing a transcript to score each segment for viral potential on social media.

First, infer the content type (podcast, interview, tutorial, speech, debate, etc.) from the transcript.

Then score each segment (0-100) based on:
- Standalone impact: Can this segment work out of context?
- Quotability: Is this memorable/shareable?
- Emotional punch: Does it evoke strong emotion?
- Surprise/controversy: Does it contain unexpected or provocative content?

Transcript:
{transcript}

Respond with valid JSON only, no other text:
{{
  "content_type": "<inferred type>",
  "scores": [
    {{"index": 0, "score": 85, "tags": ["quotable", "emotional"]}},
    ...
  ]
}}

Include ALL segments by index. Tags should be from: quotable, emotional, surprising, controversial, insightful, funny, dramatic, actionable."""

    def process(self, segments: List[Dict]) -> List[Dict]:
        if not segments:
            return segments
        
        transcript_context = self._build_transcript_context(segments)
        prompt = self.PROMPT_TEMPLATE.format(transcript=transcript_context)
        
        logger.info(f"Scoring {len(segments)} segments for virality")
        response = self.llm.complete(prompt)
        
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
            else:
                raise ValueError(f"Failed to parse LLM response as JSON: {response[:200]}")
        
        content_type = result.get('content_type', 'unknown')
        logger.info(f"Inferred content type: {content_type}")
        
        score_map = {s['index']: s for s in result.get('scores', [])}
        
        scored_segments = []
        for i, seg in enumerate(segments):
            scored_seg = seg.copy()
            if i in score_map:
                scored_seg['virality_score'] = score_map[i].get('score', 0)
                scored_seg['virality_tags'] = score_map[i].get('tags', [])
            else:
                scored_seg['virality_score'] = 0
                scored_seg['virality_tags'] = []
            scored_segments.append(scored_seg)
        
        return scored_segments, content_type


class TrailerScoringOperation(ScoringOperation):
    """Score segments for trailer/highlight suitability"""
    
    PROMPT_TEMPLATE = """You are analyzing a transcript to score each segment for use in a trailer or highlight reel.

First, infer the content type (podcast, interview, tutorial, speech, debate, etc.) from the transcript.

Then score each segment (0-100) based on:
- Context-setting: Does it establish premise or introduce key ideas?
- Tension-building: Does it create anticipation or suspense?
- Payoff moment: Is it a climax, punchline, or key revelation?
- Representative: Does it capture the essence of the content?

Transcript:
{transcript}

Respond with valid JSON only, no other text:
{{
  "content_type": "<inferred type>",
  "scores": [
    {{"index": 0, "score": 70, "tags": ["context", "representative"]}},
    ...
  ]
}}

Include ALL segments by index. Tags should be from: context, tension, payoff, climax, introduction, conclusion, representative, hook."""

    def process(self, segments: List[Dict]) -> List[Dict]:
        if not segments:
            return segments
        
        transcript_context = self._build_transcript_context(segments)
        prompt = self.PROMPT_TEMPLATE.format(transcript=transcript_context)
        
        logger.info(f"Scoring {len(segments)} segments for trailer suitability")
        response = self.llm.complete(prompt)
        
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
            else:
                raise ValueError(f"Failed to parse LLM response as JSON: {response[:200]}")
        
        content_type = result.get('content_type', 'unknown')
        logger.info(f"Inferred content type: {content_type}")
        
        score_map = {s['index']: s for s in result.get('scores', [])}
        
        scored_segments = []
        for i, seg in enumerate(segments):
            scored_seg = seg.copy()
            if i in score_map:
                scored_seg['trailer_score'] = score_map[i].get('score', 0)
                scored_seg['trailer_tags'] = score_map[i].get('tags', [])
            else:
                scored_seg['trailer_score'] = 0
                scored_seg['trailer_tags'] = []
            scored_segments.append(scored_seg)
        
        return scored_segments, content_type


OPERATIONS: Dict[str, type] = {
    'score_virality': ViralityScoringOperation,
    'score_trailer': TrailerScoringOperation,
}


# =============================================================================
# Main Processor
# =============================================================================

class SegmentScorerProcessor:
    """Main processor for segment scoring jobs"""
    
    def __init__(self, job_def: Dict):
        self.job_def = job_def
        self.data = job_def.get('data', {})
        self.operation_type = self.data.get('operation', 'score_virality')
        self.input_key = self.data.get('input_key')
        self.output_key = self.data.get('output_key')
        self.args = self.data.get('args', {})
        
        self.input_bucket = job_def.get('input_bucket') or INPUT_BUCKET
        self.output_bucket = job_def.get('output_bucket') or OUTPUT_BUCKET
    
    def validate(self):
        if not self.input_key or not self.output_key:
            raise ValueError("Missing input_key or output_key in job definition")
        
        if self.operation_type not in OPERATIONS:
            raise ValueError(f"Unknown operation: {self.operation_type}")
        
        llm_provider = self.args['llm_provider']
        llm_model = self.args['llm_model']
        if llm_provider not in LLM_PROVIDERS:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")
    
    def process(self) -> Dict:
        try:
            self.validate()
            
            logger.info(f"Job started at {datetime.now().isoformat()}")
            logger.info(f"Operation: {self.operation_type}")
            logger.info(f"Input: s3://{self.input_bucket}/{self.input_key}")
            logger.info(f"Output: s3://{self.output_bucket}/{self.output_key}")
            
            llm_provider = self.args['llm_provider']
            llm_model = self.args['llm_model']
            logger.info(f"LLM: {llm_provider}/{llm_model}")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                local_input = os.path.join(tmpdir, 'input.json')
                local_output = os.path.join(tmpdir, 'output.json')
                
                s3_download_with_retry(self.input_bucket, self.input_key, local_input)
                
                with open(local_input, 'r') as f:
                    input_data = json.load(f)
                
                if isinstance(input_data, list):
                    segments = input_data
                elif isinstance(input_data, dict) and 'segments' in input_data:
                    segments = input_data['segments']
                else:
                    segments = input_data.get('segments', [])
                
                logger.info(f"Loaded {len(segments)} segments")
                
                llm_client = get_llm_client(llm_provider, llm_model)
                operation_class = OPERATIONS[self.operation_type]
                operation = operation_class(self.args, llm_client)
                
                scored_segments, content_type = operation.process(segments)
                
                output_data = {
                    'segments': scored_segments,
                    'metadata': {
                        'operation': self.operation_type,
                        'content_type': content_type,
                        'segment_count': len(scored_segments),
                        'llm_provider': llm_provider,
                        'llm_model': llm_model,
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                with open(local_output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                
                s3_upload_with_retry(local_output, self.output_bucket, self.output_key)
                
                success_result = {
                    'status': 'success',
                    'operation': self.operation_type,
                    'input_key': self.input_key,
                    'output_key': self.output_key,
                    'content_type': content_type,
                    'segments_scored': len(scored_segments),
                    'timestamp': datetime.now().isoformat()
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
    job_def = json.loads(sys.stdin.read())
    processor = SegmentScorerProcessor(job_def)
    
    try:
        processor.process()
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
