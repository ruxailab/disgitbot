#!/usr/bin/env python3
"""
Simplified metrics calculator for PR analysis using radon for cyclomatic complexity
"""

import re
import logging
import tempfile
import os
from typing import Dict, Any, List
from datetime import datetime
from radon.complexity import cc_visit
from radon.raw import analyze

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Simplified metrics calculator using radon for cyclomatic complexity"""
    
    def __init__(self):
        """Initialize the metrics calculator"""
        self.supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h'}
    
    def calculate_pr_metrics(self, diff: str, files: List[Dict]) -> Dict[str, Any]:
        """
        Calculate PR metrics including cyclomatic complexity using radon
        
        Args:
            diff: Git diff string
            files: List of file change data from GitHub API
            
        Returns:
            Dictionary containing calculated metrics
        """
        try:
            # Basic metrics from GitHub API
            basic_metrics = self._calculate_basic_metrics(files)
            
            # Complexity metrics using radon
            complexity_metrics = self._calculate_complexity_with_radon(diff, files)
            
            # Risk assessment
            risk_metrics = self._calculate_risk_assessment(basic_metrics, complexity_metrics)
            
            # Combine all metrics
            all_metrics = {
                **basic_metrics,
                **complexity_metrics,
                **risk_metrics,
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Calculated metrics: {all_metrics}")
            return all_metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return self._get_fallback_metrics(files)
    
    def _calculate_basic_metrics(self, files: List[Dict]) -> Dict[str, Any]:
        """Calculate basic metrics from GitHub API data"""
        return {
            'lines_added': sum(file.get('additions', 0) for file in files),
            'lines_deleted': sum(file.get('deletions', 0) for file in files),
            'files_changed': len(files),
            'total_changes': sum(file.get('additions', 0) + file.get('deletions', 0) for file in files),
        }
    
    def _calculate_complexity_with_radon(self, diff: str, files: List[Dict]) -> Dict[str, Any]:
        """Calculate cyclomatic complexity using radon library"""
        complexity_metrics = {
            'cyclomatic_complexity_added': 0,
            'functions_added': 0,
            'classes_added': 0,
        }
        
        if not diff:
            return complexity_metrics
        
        # Extract added code from diff
        added_code_by_file = self._extract_added_code_from_diff(diff)
        
        total_complexity = 0
        total_functions = 0
        total_classes = 0
        
        for filename, code_lines in added_code_by_file.items():
            if not self._is_supported_file(filename):
                continue
            
            # Join code lines
            code_content = '\n'.join(code_lines)
            
            if not code_content.strip():
                continue
            
            try:
                # Use radon to calculate complexity
                if filename.endswith('.py'):
                    # For Python files, use radon's complexity analysis
                    complexity_results = cc_visit(code_content)
                    
                    for result in complexity_results:
                        total_complexity += result.complexity
                        if result.type == 'function':
                            total_functions += 1
                        elif result.type == 'class':
                            total_classes += 1
                
                # For other languages, use simple pattern matching
                else:
                    total_functions += self._count_functions_simple(code_content, filename)
                    total_classes += self._count_classes_simple(code_content, filename)
                    total_complexity += self._estimate_complexity_simple(code_content)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze {filename}: {e}")
                continue
        
        complexity_metrics.update({
            'cyclomatic_complexity_added': total_complexity,
            'functions_added': total_functions,
            'classes_added': total_classes,
        })
        
        return complexity_metrics
    
    def _extract_added_code_from_diff(self, diff: str) -> Dict[str, List[str]]:
        """Extract only the added code lines from git diff"""
        added_code = {}
        current_file = None
        
        for line in diff.split('\n'):
            # Track current file
            if line.startswith('+++'):
                if len(line) > 6:
                    current_file = line[6:].strip()
                    if current_file.startswith('b/'):
                        current_file = current_file[2:]
                    added_code[current_file] = []
                continue
            
            # Collect added lines (starting with +, but not +++)
            if current_file and line.startswith('+') and not line.startswith('+++'):
                code_line = line[1:]  # Remove the + prefix
                added_code[current_file].append(code_line)
        
        return added_code
    
    def _is_supported_file(self, filename: str) -> bool:
        """Check if file type is supported for complexity analysis"""
        if not filename:
            return False
        
        return any(filename.lower().endswith(ext) for ext in self.supported_extensions)
    
    def _count_functions_simple(self, code: str, filename: str) -> int:
        """Simple function counting for non-Python files"""
        patterns = {
            '.js': [r'function\s+\w+', r'const\s+\w+\s*=\s*\(', r'=>\s*{'],
            '.jsx': [r'function\s+\w+', r'const\s+\w+\s*=\s*\(', r'=>\s*{'],
            '.ts': [r'function\s+\w+', r'const\s+\w+\s*=\s*\(', r'=>\s*{'],
            '.tsx': [r'function\s+\w+', r'const\s+\w+\s*=\s*\(', r'=>\s*{'],
            '.java': [r'public\s+\w+\s+\w+\s*\(', r'private\s+\w+\s+\w+\s*\(', r'protected\s+\w+\s+\w+\s*\('],
        }
        
        ext = next((ext for ext in patterns.keys() if filename.endswith(ext)), None)
        if not ext:
            return 0
        
        count = 0
        for pattern in patterns[ext]:
            count += len(re.findall(pattern, code, re.MULTILINE))
        
        return count
    
    def _count_classes_simple(self, code: str, filename: str) -> int:
        """Simple class counting for non-Python files"""
        patterns = {
            '.js': [r'class\s+\w+'],
            '.jsx': [r'class\s+\w+'],
            '.ts': [r'class\s+\w+', r'interface\s+\w+'],
            '.tsx': [r'class\s+\w+', r'interface\s+\w+'],
            '.java': [r'class\s+\w+', r'interface\s+\w+'],
        }
        
        ext = next((ext for ext in patterns.keys() if filename.endswith(ext)), None)
        if not ext:
            return 0
        
        count = 0
        for pattern in patterns[ext]:
            count += len(re.findall(pattern, code, re.MULTILINE))
        
        return count
    
    def _estimate_complexity_simple(self, code: str) -> int:
        """Simple complexity estimation for non-Python files"""
        complexity_keywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'try', 'catch', '&&', '||', '?']
        
        complexity = 0
        for keyword in complexity_keywords:
            complexity += len(re.findall(r'\b' + re.escape(keyword) + r'\b', code, re.IGNORECASE))
        
        return complexity
    
    def _calculate_risk_assessment(self, basic: Dict, complexity: Dict) -> Dict[str, Any]:
        """Calculate risk level based on metrics"""
        risk_score = 0
        risk_factors = []
        
        # Size-based risk
        total_changes = basic.get('total_changes', 0)
        if total_changes > 500:
            risk_score += 3
            risk_factors.append(f'Large PR ({total_changes} lines changed)')
        elif total_changes > 100:
            risk_score += 1
            risk_factors.append(f'Medium PR ({total_changes} lines changed)')
        
        # Complexity-based risk
        complexity_added = complexity.get('cyclomatic_complexity_added', 0)
        if complexity_added > 20:
            risk_score += 3
            risk_factors.append(f'High complexity increase (+{complexity_added})')
        elif complexity_added > 10:
            risk_score += 2
            risk_factors.append(f'Medium complexity increase (+{complexity_added})')
        elif complexity_added > 5:
            risk_score += 1
            risk_factors.append(f'Low complexity increase (+{complexity_added})')
        
        # Function count risk
        functions_added = complexity.get('functions_added', 0)
        if functions_added > 10:
            risk_score += 2
            risk_factors.append(f'Many functions added ({functions_added})')
        elif functions_added > 5:
            risk_score += 1
            risk_factors.append(f'Several functions added ({functions_added})')
        
        # Determine risk level
        if risk_score >= 6:
            risk_level = 'HIGH'
        elif risk_score >= 3:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
        }
    
    def _get_fallback_metrics(self, files: List[Dict]) -> Dict[str, Any]:
        """Fallback metrics if calculation fails"""
        return {
            'lines_added': sum(file.get('additions', 0) for file in files),
            'lines_deleted': sum(file.get('deletions', 0) for file in files),
            'files_changed': len(files),
            'total_changes': sum(file.get('additions', 0) + file.get('deletions', 0) for file in files),
            'cyclomatic_complexity_added': 0,
            'functions_added': 0,
            'classes_added': 0,
            'risk_level': 'UNKNOWN',
            'risk_factors': ['Metrics calculation failed'],
            'error': 'Failed to calculate detailed metrics'
        } 