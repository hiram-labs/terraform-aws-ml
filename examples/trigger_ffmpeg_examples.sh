#!/bin/bash
# Example SNS trigger scripts for FFmpeg operations
# These demonstrate how to trigger different ffmpeg operations via SNS

set -e

# Get SNS topic ARN from Terraform output
TOPIC_ARN=$(terraform output -raw sns_topic_arn)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "SNS Topic ARN: $TOPIC_ARN"
echo ""

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 1. CONVERT: MP4 to WebM with VP9 codec
# ============================================================================
echo -e "${BLUE}1. Convert MP4 to WebM${NC}"
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --region "$AWS_REGION" \
  --message '{
    "trigger_type": "batch_job",
    "data": {
      "script_key": "jobs/ffmpeg_operations.py",
      "compute_type": "cpu",
      "operation": "convert",
      "input_key": "videos/input.mp4",
      "output_key": "videos/converted.webm",
      "args": {
        "codec": "libvpx-vp9",
        "crf": "30"
      }
    },
    "metadata": {
      "user": "ml-engineer",
      "project": "video-pipeline"
    }
  }'
echo -e "${GREEN}✓ Convert job submitted${NC}\n"

# ============================================================================
# 2. SCALE: Resize video to 1280x720
# ============================================================================
echo -e "${BLUE}2. Scale video to 1280x720${NC}"
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --region "$AWS_REGION" \
  --message '{
    "trigger_type": "batch_job",
    "data": {
      "script_key": "jobs/ffmpeg_operations.py",
      "compute_type": "cpu",
      "operation": "scale",
      "input_key": "videos/input.mp4",
      "output_key": "videos/scaled_1280x720.mp4",
      "args": {
        "width": "1280",
        "height": "720",
        "scale_filter": "scale=1280:720:force_original_aspect_ratio=decrease"
      }
    },
    "metadata": {
      "user": "ml-engineer",
      "project": "video-pipeline"
    }
  }'
echo -e "${GREEN}✓ Scale job submitted${NC}\n"

# ============================================================================
# 3. EXTRACT: Extract audio to MP3
# ============================================================================
echo -e "${BLUE}3. Extract audio to MP3${NC}"
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --region "$AWS_REGION" \
  --message '{
    "trigger_type": "batch_job",
    "data": {
      "script_key": "jobs/ffmpeg_operations.py",
      "compute_type": "cpu",
      "operation": "extract",
      "input_key": "videos/input.mp4",
      "output_key": "audio/extracted.mp3",
      "args": {
        "audio_codec": "libmp3lame",
        "audio_bitrate": "192k"
      }
    },
    "metadata": {
      "user": "ml-engineer",
      "project": "audio-extraction"
    }
  }'
echo -e "${GREEN}✓ Extract job submitted${NC}\n"

# ============================================================================
# 4. CONCAT: Concatenate multiple videos
# ============================================================================
echo -e "${BLUE}4. Concatenate videos${NC}"
echo "Note: First upload a concat_list.txt to S3 with format:"
echo "  file '/workspace/video1.mp4'"
echo "  file '/workspace/video2.mp4'"
echo ""
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --region "$AWS_REGION" \
  --message '{
    "trigger_type": "batch_job",
    "data": {
      "script_key": "jobs/ffmpeg_operations.py",
      "compute_type": "cpu",
      "operation": "concat",
      "input_key": "videos/concat_list.txt",
      "output_key": "videos/concatenated.mp4",
      "args": {
        "codec": "libx264",
        "preset": "medium"
      }
    },
    "metadata": {
      "user": "ml-engineer",
      "project": "video-concat"
    }
  }'
echo -e "${GREEN}✓ Concat job submitted${NC}\n"

# ============================================================================
# 5. COMPRESS: Compress with custom bitrate
# ============================================================================
echo -e "${BLUE}5. Compress video${NC}"
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --region "$AWS_REGION" \
  --message '{
    "trigger_type": "batch_job",
    "data": {
      "script_key": "jobs/ffmpeg_operations.py",
      "compute_type": "cpu",
      "operation": "compress",
      "input_key": "videos/input.mp4",
      "output_key": "videos/compressed.mp4",
      "args": {
        "video_bitrate": "1500k",
        "audio_bitrate": "128k",
        "preset": "medium"
      }
    },
    "metadata": {
      "user": "ml-engineer",
      "project": "video-compression"
    }
  }'
echo -e "${GREEN}✓ Compress job submitted${NC}\n"

echo -e "${GREEN}All example jobs submitted!${NC}"
echo ""
echo "Monitor jobs with:"
echo "  aws batch describe-jobs --jobs <JOB_ID> --region $AWS_REGION"
echo ""
echo "Check CloudWatch logs with:"
echo "  aws logs tail /aws/batch/<PROJECT>-ml-jobs --follow --region $AWS_REGION"
