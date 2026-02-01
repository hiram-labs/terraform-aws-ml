from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import json
import boto3
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime
from pathlib import Path

load_dotenv()

app = FastAPI(title="ML Pipeline Control Panel")
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# History log file
HISTORY_FILE = static_dir / "history.json"

def load_history():
    """Load job history from file"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    """Save job history to file"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, default=str)

# Default topic ARN (optional) -- can be provided via UI
DEFAULT_TOPIC_ARN = os.getenv("TRIGGER_EVENTS_TOPIC_ARN")

# Project name for bucket naming
PROJECT_NAME = os.getenv("PROJECT_NAME")

# Hard-coded buckets based on project name
BUCKETS = {
    "input": f"{PROJECT_NAME}-ml-input",
    "output": f"{PROJECT_NAME}-ml-output",
    "model": f"{PROJECT_NAME}-ml-models"
}

PRESETS = {
    "extract-audio": {
        "script_key": "jobs/video_processor.py",
        "compute_type": "cpu",
        "operation": "extract_audio",
        "args": {"sample_rate": "16000", "channels": "1", "normalize": "true"}
    },
    "transcribe-audio": {
        "script_key": "jobs/transcribe_processor.py",
        "compute_type": "gpu",
        "operation": "transcribe_audio",
        "args": {"language": "en", "output_format": "json", "whisper_model": "openai/whisper-small", "pyannote_model": "pyannote/speaker-diarization-3.1"}
    }
}

class PreviewResponse(BaseModel):
    payload: dict


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "presets": PRESETS.keys(), "default_topic": DEFAULT_TOPIC_ARN, "buckets": BUCKETS})


@app.post("/preview", response_class=JSONResponse)
async def preview(preset: Optional[str] = Form(None), data: Optional[str] = Form(None),
                  input_key: Optional[str] = Form(None), output_key: Optional[str] = Form(None),
                  input_bucket: Optional[str] = Form(None), output_bucket: Optional[str] = Form(None), model_bucket: Optional[str] = Form(None)):
    # Build base data
    if preset:
        base = PRESETS.get(preset, {}).copy()
    else:
        base = {}

    override = None
    if data:
        try:
            override = json.loads(data)
        except Exception as e:
            return JSONResponse({"error": f"Invalid JSON in data: {str(e)}"}, status_code=400)

    if override:
        base.update(override)

    if input_key:
        base["input_key"] = input_key
    if output_key:
        base["output_key"] = output_key

    # Always append timestamp to output_key if present
    if 'output_key' in base:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = base['output_key'].rsplit('.', 1)
        if len(parts) == 2:
            base['output_key'] = f"{parts[0]}_{ts}.{parts[1]}"
        else:
            base['output_key'] = f"{base['output_key']}_{ts}"

    payload = {
        "trigger_type": "batch_job",
        "data": base
    }

    if input_bucket:
        payload['input_bucket'] = input_bucket
    if output_bucket:
        payload['output_bucket'] = output_bucket
    if model_bucket:
        payload['model_bucket'] = model_bucket

    return PreviewResponse(payload=payload)


@app.post("/publish", response_class=JSONResponse)
async def publish(topic_arn: Optional[str] = Form(None), preset: Optional[str] = Form(None), data: Optional[str] = Form(None),
                  input_key: Optional[str] = Form(None), output_key: Optional[str] = Form(None),
                  input_bucket: Optional[str] = Form(None), output_bucket: Optional[str] = Form(None), model_bucket: Optional[str] = Form(None)):
    # Determine topic
    topic = topic_arn or DEFAULT_TOPIC_ARN
    if not topic:
        return JSONResponse({"error": "No SNS topic ARN provided. Set TRIGGER_EVENTS_TOPIC_ARN or provide it in the UI."}, status_code=400)

    # Reuse preview builder
    preview_resp = await preview(preset=preset, data=data, input_key=input_key, output_key=output_key,
                                 input_bucket=input_bucket, output_bucket=output_bucket, model_bucket=model_bucket)
    if isinstance(preview_resp, JSONResponse) and preview_resp.status_code != 200:
        return preview_resp
    payload = preview_resp.payload if hasattr(preview_resp, 'payload') else preview_resp.dict().get('payload')

    # Publish to SNS
    session = boto3.Session()
    sns = session.client('sns')
    try:
        resp = sns.publish(TopicArn=topic, Message=json.dumps(payload))
        
        # Log successful job submission
        history = load_history()
        job_entry = {
            "timestamp": datetime.now().isoformat(),
            "topic_arn": topic,
            "status": "success",
            "sns_message_id": resp.get('MessageId'),
            "form_data": {
                "operation": payload.get('data', {}).get('operation') or (preset or 'custom'),
                "compute_type": payload.get('data', {}).get('compute_type', 'unknown'),
                "script_key": payload.get('data', {}).get('script_key', 'unknown'),
                "input_key": input_key,
                "output_key": output_key,
                "input_bucket": input_bucket,
                "output_bucket": output_bucket,
                "model_bucket": model_bucket
            },
            "sns_response": resp,
            "payload": payload
        }
        history.append(job_entry)
        # Keep only last 100 entries
        if len(history) > 100:
            history = history[-100:]
        save_history(history)
        
    except Exception as e:
        # Log failed SNS publish
        history = load_history()
        job_entry = {
            "timestamp": datetime.now().isoformat(),
            "topic_arn": topic,
            "status": "failed",
            "error": str(e),
            "form_data": {
                "operation": payload.get('data', {}).get('operation') or (preset or 'custom'),
                "compute_type": payload.get('data', {}).get('compute_type', 'unknown'),
                "script_key": payload.get('data', {}).get('script_key', 'unknown'),
                "input_key": input_key,
                "output_key": output_key,
                "input_bucket": input_bucket,
                "output_bucket": output_bucket,
                "model_bucket": model_bucket
            },
            "payload": payload
        }
        history.append(job_entry)
        if len(history) > 100:
            history = history[-100:]
        save_history(history)
        
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({"sns_response": resp, "payload": payload})


@app.get("/history", response_class=JSONResponse)
async def get_history():
    """Get job history"""
    history = load_history()
    return JSONResponse({"history": history})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
