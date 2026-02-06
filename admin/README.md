# Admin Scripts

This directory contains scripts for local admin tasks and a web UI control panel for the ML pipeline.

## Setup (venv)

From this directory (run all scripts from here):

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy env example and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Environment Variables

See [.env.example](.env.example) for available variables. The scripts and UI load this file automatically.

Key variables:
- `AWS_PROFILE` / `AWS_REGION` - AWS credentials and region
- `TRIGGER_EVENTS_TOPIC_ARN` - SNS topic for job triggers
- `PROJECT_NAME` - Project name for bucket naming (default: ml-pipeline)
- `HUGGINGFACE_TOKEN` - Token for downloading models
- `HF_HUB_DISABLE_PROGRESS_BARS=1` - Keep download logs clean

## AWS Credentials

Ensure your AWS credentials are available via one of:
- `AWS_PROFILE` env var
- Default AWS config/credentials files

## Web UI Control Panel

Run the FastAPI control panel for previewing and publishing SNS job triggers:

```bash
uvicorn admin.ui.app:app --reload --port 8000
# then open http://127.0.0.1:8000
```

Features:
- Job presets (extract-audio, transcribe-audio)
- Bucket selection (all buckets available for any purpose)
- JSON overrides for custom configurations
- Preview payloads before publishing
- Timestamp output keys

## CLI Scripts

| Script              | Purpose                                      | Example Command |
|---------------------|----------------------------------------------|-----------------|
| scripts/download_models.py  | Download/upload Hugging Face models to S3     | `python scripts/download_models.py --bucket my-models --model-type whisper --model-names openai/whisper-base,guillaumekln/faster-whisper-small.en` |
| scripts/trigger_jobs.py     | Trigger jobs via SNS (supports presets: extract-audio, transcribe-audio; optional: --input-bucket, --output-bucket, --model-bucket, --container-image) | `python scripts/trigger_jobs.py --preset transcribe-audio --data '{"input_key": "audio/input.wav"}'` or `python scripts/trigger_jobs.py --preset transcribe-audio --data '{"input_key": "audio/input.wav"}' --container-image 123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-pipeline-gpu-slim:latest` |
| scripts/upload_jobs.py      | Upload all files in jobs/ to S3               | `python scripts/upload_jobs.py --bucket my-bucket --prefix jobs/` |