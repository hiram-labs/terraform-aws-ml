#!/usr/bin/env python3
"""
Cleanup Processor for AWS Batch

Extensible framework for cache cleanup operations.
Clears the EFS model cache to stop storage charges while keeping the cache ready for reuse.
Models will be automatically re-downloaded on the next job that uses them.

Supported Operations:
- cleanup-cache: Remove all cached models from /opt/models

To add new operations:
  1. Create a class inheriting from CleanupOperation
  2. Implement process() method
  3. Add to OPERATIONS registry

SNS Trigger Format:
{
  "trigger_type": "batch_job",
  "data": {
    "script_key": "jobs/cleanup_processor.py",
    "compute_type": "cpu",
    "operation": "cleanup-cache"
  }
}
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanupOperation(ABC):
    """Base class for cleanup operations"""
    
    def __init__(self, args: Dict = None):
        self.args = args or {}
    
    @abstractmethod
    def process(self) -> Dict:
        """Execute the cleanup operation and return results"""
        pass


class ClearModelCacheOperation(CleanupOperation):
    """Clear the /opt/models cache directory"""
    
    def process(self) -> Dict:
        """Clear the model cache and return statistics"""
        cache_dir = Path('/opt/models')
        
        if not cache_dir.exists():
            logger.info(f"Cache directory {cache_dir} does not exist - nothing to clean")
            return {
                'status': 'success',
                'message': 'Cache directory not found',
                'size_freed_mb': 0.0
            }
        
        logger.info(f"Clearing cache directory: {cache_dir}")
        
        # Calculate total size before deletion
        total_size = 0
        file_count = 0
        for item in cache_dir.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
        
        size_mb = total_size / (1024 * 1024)
        logger.info(f"Total cache size: {size_mb:.2f} MB ({file_count} files)")
        
        # Remove all contents
        try:
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Successfully cleared cache - freed {size_mb:.2f} MB")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            raise
        
        return {
            'status': 'success',
            'cache_directory': str(cache_dir),
            'size_freed_mb': round(size_mb, 2),
            'files_deleted': file_count,
            'message': f'Cleared {size_mb:.2f} MB from model cache'
        }


# Registry of available operations
OPERATIONS: Dict[str, type] = {
    'cleanup-cache': ClearModelCacheOperation,
}


class CleanupProcessor:
    """Main processor for cleanup jobs"""
    
    def __init__(self, job_def: Dict):
        self.job_def = job_def
        self.data = job_def.get('data', {})
        self.operation_type = self.data.get('operation', 'cleanup-cache')
        self.args = self.data.get('args', {})
    
    def validate(self):
        """Validate job configuration"""
        if self.operation_type not in OPERATIONS:
            raise ValueError(f"Unknown operation: {self.operation_type}")
    
    def process(self) -> Dict:
        """Execute the cleanup operation"""
        try:
            self.validate()
            
            logger.info(f"Job started at {datetime.now().isoformat()}")
            logger.info(f"Operation: {self.operation_type}")
            
            operation_class = OPERATIONS[self.operation_type]
            operation = operation_class(self.args)
            result = operation.process()
            
            success_result = {
                'status': 'success',
                'operation': self.operation_type,
                'timestamp': datetime.now().isoformat(),
                'details': result
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
    """Main execution function"""
    job_def = json.loads(sys.stdin.read())
    processor = CleanupProcessor(job_def)
    
    try:
        processor.process()
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
