"""
Batch Job Trigger

Submits AWS Batch jobs based on SNS messages.
Supports GPU acceleration, CPU-only compute, custom resource allocation, and parameter passing.
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, Any

from base import BaseTrigger, ExecutionError, ValidationError

logger = logging.getLogger(__name__)

batch_client = boto3.client('batch')


class BatchJobTrigger(BaseTrigger):
    """
    Submits jobs to AWS Batch.
    
    Trigger Type: batch_job
    
    Required Fields:
    - script_key: S3 path to Python script (e.g., "jobs/train.py")
    
    Optional Fields:
    - compute_type: "gpu" (default) or "cpu" for CPU-only workloads
    - vcpus: CPU cores (default: 4 for GPU, 2 for CPU)
    - memory: Memory in MB (default: 16384 for GPU, 4096 for CPU)
    - gpus: Number of GPUs (default: 1, only for GPU compute_type)
    - timeout: Job timeout in seconds (default: 3600)
    - additional_env: Dict of additional environment variables
    - job_name: Custom job name (auto-generated if not provided)
    
    Metadata Fields:
    - user: User/service submitting the job (for tracking)
    - project: Project name (for organization)
    - experiment: Experiment ID (optional)
    
    Example (GPU Job with defaults):
    {
        "trigger_type": "batch_job",
        "data": {
            "script_key": "jobs/train_model.py"
        }
    }
    
    Example (GPU Job with custom resources):
    {
        "trigger_type": "batch_job",
        "data": {
            "script_key": "jobs/train_large_model.py",
            "vcpus": 16,
            "memory": 65536,
            "gpus": 4,
            "timeout": 7200
        }
    }
    
    Example (CPU Job with defaults):
    {
        "trigger_type": "batch_job",
        "data": {
            "script_key": "jobs/process_data.py",
            "compute_type": "cpu"
        }
    }
    
    Example (CPU Job with custom resources):
    {
        "trigger_type": "batch_job",
        "data": {
            "script_key": "jobs/heavy_processing.py",
            "compute_type": "cpu",
            "vcpus": 8,
            "memory": 16384
        }
    }
    """
    
    TRIGGER_NAME = "batch_job"
    
    REQUIRED_FIELDS = [
        "script_key"  # S3 key to the Python script
    ]
    
    OPTIONAL_FIELDS = {
        "compute_type": "gpu",  # "gpu" or "cpu"
        "vcpus": None,  # Determined by compute_type
        "memory": None,  # Determined by compute_type
        "gpus": None,  # Determined by compute_type (1 for GPU, 0 for CPU)
        "timeout": 3600,
        "additional_env": {},
        "job_name": None
    }
    
    def __init__(self, message: Dict[str, Any], context: Any):
        super().__init__(message, context)
        
        # Environment variables from Lambda
        self.gpu_job_queue = os.environ['BATCH_JOB_QUEUE']
        self.gpu_job_definition = os.environ['ML_PYTHON_JOB_DEFINITION']
        self.cpu_job_queue = os.environ.get('CPU_JOB_QUEUE', '')
        self.cpu_job_definition = os.environ.get('ML_PYTHON_CPU_JOB_DEFINITION', '')
        self.output_bucket = os.environ['ML_OUTPUT_BUCKET']
        self.input_bucket = os.environ.get('ML_INPUT_BUCKET', '')
        
        # Default resource allocations from Terraform
        self.default_gpu_vcpus = int(os.environ.get('DEFAULT_GPU_VCPUS', '4'))
        self.default_gpu_memory = int(os.environ.get('DEFAULT_GPU_MEMORY', '16384'))
        self.default_gpu_gpus = int(os.environ.get('DEFAULT_GPU_GPUS', '1'))
        self.default_cpu_vcpus = int(os.environ.get('DEFAULT_CPU_VCPUS', '2'))
        self.default_cpu_memory = int(os.environ.get('DEFAULT_CPU_MEMORY', '4096'))
    
    def _validate_custom(self) -> None:
        """Validate batch job specific requirements"""
        script_key = self.data['script_key']
        
        # Must be a Python script
        if not script_key.endswith('.py'):
            raise ValidationError(
                f"batch_job: script_key must be a .py file, got: {script_key}"
            )
        
        compute_type = self.get_optional('compute_type', 'gpu')
        if compute_type not in ['gpu', 'cpu']:
            raise ValidationError(
                f"batch_job: compute_type must be 'gpu' or 'cpu', got: {compute_type}"
            )
        
        # Validate resource constraints
        vcpus = self.get_optional('vcpus')
        memory = self.get_optional('memory')
        gpus = self.get_optional('gpus')
        
        # Set defaults based on compute_type if not provided
        if vcpus is None:
            vcpus = self.default_gpu_vcpus if compute_type == 'gpu' else self.default_cpu_vcpus
        if memory is None:
            memory = self.default_gpu_memory if compute_type == 'gpu' else self.default_cpu_memory
        if gpus is None:
            gpus = self.default_gpu_gpus if compute_type == 'gpu' else 0
        
        if not isinstance(vcpus, int) or vcpus < 1:
            raise ValidationError("batch_job: vcpus must be a positive integer")
        
        if not isinstance(memory, int) or memory < 256:
            raise ValidationError("batch_job: memory must be >= 256 MB")
        
        if compute_type == 'gpu':
            if not isinstance(gpus, int) or gpus < 1:
                raise ValidationError("batch_job: gpus must be >= 1 for GPU compute")
        else:
            if not isinstance(gpus, int) or gpus != 0:
                # CPU jobs should not request GPUs
                logger.warning("batch_job: gpus requested for CPU compute, ignoring")
    
    def execute(self) -> Dict[str, Any]:
        """
        Submit job to AWS Batch (GPU or CPU).
        
        Returns:
            dict: Execution result with job_id, job_name, and submission details
        
        Raises:
            ExecutionError: On submission failure
        """
        try:
            # Extract parameters
            script_key = self.data['script_key']
            compute_type = self.get_optional('compute_type', 'gpu')
            vcpus = self.get_optional('vcpus')
            memory = self.get_optional('memory')
            gpus = self.get_optional('gpus')
            timeout = self.get_optional('timeout', self.OPTIONAL_FIELDS['timeout'])
            additional_env = self.get_optional('additional_env', {})
            
            # Set defaults based on compute_type if not provided
            if vcpus is None:
                vcpus = self.default_gpu_vcpus if compute_type == 'gpu' else self.default_cpu_vcpus
            if memory is None:
                memory = self.default_gpu_memory if compute_type == 'gpu' else self.default_cpu_memory
            if gpus is None:
                gpus = self.default_gpu_gpus if compute_type == 'gpu' else 0
            
            # Select queue and definition based on compute type
            if compute_type == 'cpu':
                job_queue = self.cpu_job_queue
                job_definition = self.cpu_job_definition
            else:
                job_queue = self.gpu_job_queue
                job_definition = self.gpu_job_definition
            
            # Generate or use provided job name
            job_name = self.get_optional('job_name')
            if not job_name:
                job_name = self._generate_job_name(script_key)
            
            logger.info(f"Submitting Batch job: {job_name}")
            logger.info(f"  Compute Type: {compute_type}")
            logger.info(f"  Script: {script_key}")
            logger.info(f"  Resources: {vcpus} vCPU, {memory} MB, {gpus} GPU")
            
            # Prepare environment variables
            job_env = {
                'INPUT_BUCKET': self.input_bucket,
                'INPUT_KEY': script_key,
                'OUTPUT_BUCKET': self.output_bucket,
                'OUTPUT_PREFIX': self._generate_output_prefix(job_name),
                'TIMESTAMP': datetime.now().isoformat(),
                'TRIGGER_USER': self.get_metadata('user', 'unknown'),
                'TRIGGER_PROJECT': self.get_metadata('project', 'unknown'),
                'TRIGGER_EXPERIMENT': self.get_metadata('experiment', ''),
                'COMPUTE_TYPE': compute_type,
            }
            
            # Merge additional environment variables
            job_env.update(additional_env)
            
            # Build resource requirements
            resource_requirements = [
                {'type': 'VCPU', 'value': str(vcpus)},
                {'type': 'MEMORY', 'value': str(memory)},
            ]
            
            # Add GPU requirement only for GPU compute type
            if compute_type == 'gpu':
                resource_requirements.append({'type': 'GPU', 'value': str(gpus)})
            
            # Build Batch job submission
            submit_params = {
                'jobName': job_name,
                'jobQueue': job_queue,
                'jobDefinition': job_definition,
                'containerOverrides': {
                    'resourceRequirements': resource_requirements,
                    'environment': [
                        {'name': k, 'value': str(v)}
                        for k, v in job_env.items() if v
                    ]
                }
            }
            
            # Set job timeout if specified
            if timeout and timeout > 0:
                submit_params['timeout'] = {'attemptDurationSeconds': timeout}
            
            # Submit job
            response = batch_client.submit_job(**submit_params)
            job_id = response['jobId']
            
            logger.info(f"Successfully submitted job {job_name} with ID {job_id}")
            
            return {
                'status': 'success',
                'job_id': job_id,
                'job_name': job_name,
                'script_key': script_key,
                'compute_type': compute_type,
                'resources': {
                    'vcpus': vcpus,
                    'memory': memory,
                    'gpus': gpus if compute_type == 'gpu' else 0
                },
                'output_prefix': job_env['OUTPUT_PREFIX'],
                'submission_time': datetime.now().isoformat(),
                'details': {
                    'user': job_env['TRIGGER_USER'],
                    'project': job_env['TRIGGER_PROJECT'],
                    'experiment': job_env['TRIGGER_EXPERIMENT'],
                }
            }
        
        except self.validate.__class__.__bases__[0] as e:
            # Validation errors
            logger.error(f"Validation error: {str(e)}")
            raise ExecutionError(f"Batch job validation failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error submitting Batch job: {str(e)}", exc_info=True)
            raise ExecutionError(f"Failed to submit Batch job: {str(e)}")
    
    @staticmethod
    def _generate_job_name(script_key: str) -> str:
        """
        Generate a valid Batch job name from script key.
        
        Args:
            script_key: S3 key to script
        
        Returns:
            Valid job name with timestamp
        """
        # Extract filename without extension and path
        filename = script_key.split('/')[-1].rsplit('.', 1)[0]
        
        # Replace invalid characters with hyphens
        job_name = ''.join(
            c if c.isalnum() or c in '-_' else '-'
            for c in filename
        )
        
        # Add timestamp for uniqueness (max 128 chars total)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        max_name_length = 128 - len(timestamp) - 1
        job_name = job_name[:max_name_length]
        
        return f"{job_name}-{timestamp}"
    
    @staticmethod
    def _generate_output_prefix(job_name: str) -> str:
        """
        Generate S3 output prefix for job results.
        
        Args:
            job_name: Job name
        
        Returns:
            S3 prefix path
        """
        date = datetime.now().strftime('%Y-%m-%d')
        return f"results/{date}/{job_name}/"
