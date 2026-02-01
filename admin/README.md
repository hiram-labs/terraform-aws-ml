# Admin Scripts

This directory contains scripts intended to be run locally by admins to prepare environments or perform one-off tasks (e.g., downloading and uploading ML models to S3).

## Setup (venv)

From this directory (run all scripts from here):

1. Create and activate a virtual environment:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env example:
   - `cp .env.example .env`

## Environment Variables

See [.env.example](admin/.env.example) for available variables. The script loads this file automatically.
Set `HF_HUB_DISABLE_PROGRESS_BARS=1` to keep the download logs clean.

## AWS Credentials

Ensure your AWS credentials are available via one of:
- `AWS_PROFILE` env var
- Default AWS config/credentials files



## Scripts

| Script              | Purpose                                      | Example Command |
|---------------------|----------------------------------------------|-----------------|
| src/download_models.py  | Download/upload Hugging Face models to S3     | `python src/download_models.py --bucket my-models --model-type whisper --model-names openai/whisper-base,openai/whisper-small` |
| src/trigger_jobs.py     | Trigger jobs via SNS (supports presets: extract-audio, transcribe-audio; optional: --input-bucket, --output-bucket, --model-bucket) | `python src/trigger_jobs.py --preset transcribe-audio --data '{"input_key": "audio/input.wav"}'` |
| src/upload_jobs.py      | Upload all files in jobs/ to S3               | `python src/upload_jobs.py --bucket my-bucket --prefix jobs/` |