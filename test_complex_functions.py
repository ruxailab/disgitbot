#!/usr/bin/env python3
"""
Complex Test Functions Module
This module contains various complex functions for testing purposes.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import base64
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Data class for storing test results."""
    test_name: str
    status: str
    duration: float
    timestamp: datetime
    metadata: Dict[str, Union[str, int, float]]
    error_message: Optional[str] = None

class ComplexTestProcessor:
    """A complex class for processing various types of tests."""
    
    def __init__(self, config: Dict[str, any]):
        self.config = config
        self.results: List[TestResult] = []
        self.start_time = datetime.now()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the configuration parameters."""
        required_keys = ['max_iterations', 'timeout_seconds', 'retry_count']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
    
    def generate_test_data(self, size: int = 1000) -> List[Dict[str, any]]:
        """Generate synthetic test data."""
        import random
        import string
        
        data = []
        for i in range(size):
            item = {
                'id': i,
                'name': ''.join(random.choices(string.ascii_letters, k=10)),
                'value': random.uniform(0, 1000),
                'category': random.choice(['A', 'B', 'C', 'D']),
                'timestamp': datetime.now().isoformat(),
                'hash': hashlib.md5(f"test_item_{i}".encode()).hexdigest()
            }
            data.append(item)
        return data
    
    def process_data_batch(self, data: List[Dict[str, any]]) -> Dict[str, any]:
        """Process a batch of data with complex transformations."""
        start_time = time.time()
        
        # Complex data processing
        processed = {
            'total_items': len(data),
            'categories': {},
            'statistics': {
                'sum': 0,
                'average': 0,
                'min': float('inf'),
                'max': float('-inf')
            },
            'hashes': [],
            'metadata': {}
        }
        
        for item in data:
            # Update statistics
            processed['statistics']['sum'] += item['value']
            processed['statistics']['min'] = min(processed['statistics']['min'], item['value'])
            processed['statistics']['max'] = max(processed['statistics']['max'], item['value'])
            
            # Categorize items
            category = item['category']
            if category not in processed['categories']:
                processed['categories'][category] = []
            processed['categories'][category].append(item['id'])
            
            # Collect hashes
            processed['hashes'].append(item['hash'])
        
        # Calculate averages
        if processed['total_items'] > 0:
            processed['statistics']['average'] = processed['statistics']['sum'] / processed['total_items']
        
        # Add metadata
        processed['metadata'] = {
            'processing_time': time.time() - start_time,
            'memory_usage': self._get_memory_usage(),
            'timestamp': datetime.now().isoformat()
        }
        
        return processed
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def run_comprehensive_test(self) -> TestResult:
        """Run a comprehensive test suite."""
        test_name = "comprehensive_data_processing_test"
        start_time = time.time()
        
        try:
            logger.info(f"Starting {test_name}")
            
            # Generate test data
            test_data = self.generate_test_data(500)
            logger.info(f"Generated {len(test_data)} test items")
            
            # Process data
            result = self.process_data_batch(test_data)
            logger.info(f"Processed data with {result['total_items']} items")
            
            # Validate results
            self._validate_results(result)
            
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status="PASSED",
                duration=duration,
                timestamp=datetime.now(),
                metadata={
                    'items_processed': result['total_items'],
                    'categories_found': len(result['categories']),
                    'processing_time_ms': round(result['metadata']['processing_time'] * 1000, 2)
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Test {test_name} failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                status="FAILED",
                duration=duration,
                timestamp=datetime.now(),
                metadata={},
                error_message=str(e)
            )
    
    def _validate_results(self, results: Dict[str, any]) -> None:
        """Validate the processing results."""
        if results['total_items'] == 0:
            raise ValueError("No items were processed")
        
        if results['statistics']['min'] > results['statistics']['max']:
            raise ValueError("Invalid statistics: min > max")
        
        if len(results['hashes']) != results['total_items']:
            raise ValueError("Hash count mismatch")

def main():
    """Main function to demonstrate the complex test processor."""
    config = {
        'max_iterations': 100,
        'timeout_seconds': 30,
        'retry_count': 3
    }
    
    processor = ComplexTestProcessor(config)
    
    print("Running comprehensive test suite...")
    result = processor.run_comprehensive_test()
    
    print(f"Test Result: {result.status}")
    print(f"Duration: {result.duration:.2f} seconds")
    print(f"Metadata: {result.metadata}")
    
    if result.error_message:
        print(f"Error: {result.error_message}")
    else:
        print("Test completed successfully!")

if __name__ == "__main__":
    main()
