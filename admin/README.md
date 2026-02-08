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

## YouTube Cookies

Export browser cookies for restricted videos:

```bash
python3 admin/scripts/export_cookies.py \
   --s3-uri s3://${PROJECT_NAME}-ml-vault/cookies-www-youtube-com
```

## Web UI Control Panel

Run the FastAPI control panel for previewing and publishing SNS job triggers:

```bash
uvicorn admin.ui.app:app --reload --port 8000
# then open http://127.0.0.1:8000
```

Features:
- Job presets (extract-audio, transcribe-audio, download-media)
- Bucket selection (all buckets available for any purpose)
- JSON overrides for custom configurations
- Preview payloads before publishing
- Timestamp output keys

## CLI Scripts

| Script              | Purpose                          |
|---------------------|----------------------------------|
| `download_models.py`  | Download Hugging Face models to S3 |
| `trigger_jobs.py`     | Trigger jobs via SNS (supports: extract-audio, transcribe-audio, download-media) |
| `upload_jobs.py`      | Upload jobs/ to S3               |
| `export_cookies.py` | Export YouTube/Google cookies from Firefox to Netscape format and upload to S3 |

See each script's `--help` for full options.