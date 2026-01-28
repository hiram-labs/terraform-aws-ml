"""
Trigger implementations for ML pipeline.

This module provides extensible trigger implementations that can be
invoked via SNS messages. New triggers should be added to this package
and registered in the dispatcher's TRIGGER_REGISTRY.
"""

from .base import BaseTrigger, TriggerError, ValidationError, ExecutionError
from .batch_job import BatchJobTrigger

__all__ = [
    'BaseTrigger',
    'TriggerError',
    'ValidationError',
    'ExecutionError',
    'BatchJobTrigger',
]
