#!/usr/bin/env python3
"""Validate dependency compatibility by attempting imports"""
import sys

print("Testing critical imports...")

try:
    import numpy as np
    print(f"✓ NumPy {np.__version__}")
except Exception as e:
    print(f"✗ NumPy failed: {e}")
    sys.exit(1)

try:
    import torch
    print(f"✓ PyTorch {torch.__version__}")
except Exception as e:
    print(f"✗ PyTorch failed: {e}")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
    print(f"✓ Faster-Whisper")
except Exception as e:
    print(f"✗ Faster-Whisper failed: {e}")
    sys.exit(1)

try:
    from pyannote.audio import Pipeline
    print(f"✓ Pyannote.audio")
except Exception as e:
    print(f"✗ Pyannote.audio failed: {e}")
    sys.exit(1)

try:
    import boto3
    print(f"✓ Boto3")
except Exception as e:
    print(f"✗ Boto3 failed: {e}")
    sys.exit(1)

print("\nAll imports successful!")
