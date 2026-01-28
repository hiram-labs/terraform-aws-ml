"""
Base Trigger Class

Defines the interface for all trigger implementations.
New triggers should inherit from this class and implement execute().
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TriggerError(Exception):
    """Base exception for trigger errors"""
    pass


class ValidationError(TriggerError):
    """Raised when message validation fails"""
    pass


class ExecutionError(TriggerError):
    """Raised when trigger execution fails"""
    pass


class BaseTrigger(ABC):
    """
    Abstract base class for ML pipeline triggers.
    
    All triggers must implement the execute() method and define
    required message attributes. Triggers are invoked via SNS messages
    with the trigger name specified in the 'trigger_type' field.
    
    Example message:
    {
        "trigger_type": "batch_job",
        "data": {
            "script_key": "models/train.py",
            "vcpus": 4,
            "memory": 16384,
            "gpus": 1
        },
        "metadata": {
            "user": "data-scientist",
            "project": "model-v2"
        }
    }
    """
    
    # Trigger name (must be unique across all triggers)
    TRIGGER_NAME: str = None
    
    # Required fields in the message data
    REQUIRED_FIELDS = []
    
    # Optional fields with defaults
    OPTIONAL_FIELDS = {}
    
    def __init__(self, message: Dict[str, Any], context: Any):
        """
        Initialize trigger with message and Lambda context.
        
        Args:
            message: SNS message body (dict)
            context: Lambda context object
        """
        self.message = message
        self.context = context
        self.data = message.get('data', {})
        self.metadata = message.get('metadata', {})
        
        logger.info(f"Initializing {self.TRIGGER_NAME} trigger")
    
    def validate(self) -> None:
        """
        Validate message contains required fields.
        
        Raises:
            ValidationError: If required fields are missing
        """
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in self.data:
                missing.append(field)
        
        if missing:
            raise ValidationError(
                f"{self.TRIGGER_NAME}: Missing required fields: {', '.join(missing)}"
            )
        
        # Call subclass validation
        self._validate_custom()
    
    def _validate_custom(self) -> None:
        """
        Override in subclass for custom validation.
        Should raise ValidationError on invalid input.
        """
        pass
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Execute the trigger logic.
        
        Must be implemented by subclasses.
        
        Returns:
            dict: Execution result with at least:
                - status: 'success' or 'error'
                - details: execution-specific details
        
        Raises:
            ExecutionError: On execution failure
        """
        pass
    
    def get_optional(self, key: str, default=None) -> Any:
        """
        Get optional field from data with default.
        
        Args:
            key: Field name
            default: Default value if not present
        
        Returns:
            Field value or default
        """
        return self.data.get(key, default)
    
    def get_metadata(self, key: str, default=None) -> Any:
        """
        Get metadata field with default.
        
        Args:
            key: Field name
            default: Default value if not present
        
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
    
    def as_dict(self) -> Dict[str, Any]:
        """Serialize trigger info for responses"""
        return {
            'trigger_type': self.TRIGGER_NAME,
            'required_fields': self.REQUIRED_FIELDS,
            'optional_fields': self.OPTIONAL_FIELDS
        }
