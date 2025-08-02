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
from .ai_design_analyzer import AIDesignAnalyzer

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Simplified metrics calculator using radon for cyclomatic complexity"""
    
    def __init__(self):
        """Initialize the metrics calculator"""
        self.supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h'}
        self.design_analyzer = AIDesignAnalyzer()
    
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
            basic_metrics = self._calculate_basic_metrics(files)
            complexity_metrics = self._calculate_complexity_with_radon(diff, files)
            coupling_metrics = self._calculate_coupling_metrics(diff, files)
            design_analysis = self.design_analyzer.analyze_design_principles(diff, files)
            risk_metrics = self._calculate_risk_assessment(basic_metrics, complexity_metrics, coupling_metrics, design_analysis)
            
            all_metrics = {
                **basic_metrics,
                **complexity_metrics,
                **coupling_metrics,
                **design_analysis,
                **risk_metrics,
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Calculated metrics: {all_metrics}")
            return all_metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            raise
    
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
        
        added_code_by_file = self._extract_added_code_from_diff(diff)
        
        total_complexity = 0
        total_functions = 0
        total_classes = 0
        
        for filename, code_lines in added_code_by_file.items():
            if not self._is_supported_file(filename):
                continue
            
            code_content = '\n'.join(code_lines)
            
            if not code_content.strip():
                continue
            
            try:
                if filename.endswith('.py'):
                    complexity_results = cc_visit(code_content)
                    
                    for result in complexity_results:
                        total_complexity += result.complexity
                        if hasattr(result, 'is_method') and not result.is_method:
                            total_functions += 1
                        elif result.__class__.__name__.endswith('Class'):
                            total_classes += 1
                
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
    
    def _calculate_coupling_metrics(self, diff: str, files: List[Dict]) -> Dict[str, Any]:
        """Calculate Fan-In and Fan-Out coupling metrics"""
        coupling_metrics = {
            'fan_out': 0,
            'fan_in': 0,
            'coupling_factor': 0.0,
            'imports_added': 0,
            'exports_added': 0
        }
        
        if not diff:
            return coupling_metrics
        
        # Extract added lines from diff
        added_lines = []
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:].strip())
        
        # Calculate Fan-Out (dependencies this module has on others)
        fan_out_patterns = [
            r'^\s*import\s+',           # Python imports
            r'^\s*from\s+\w+\s+import', # Python from imports
            r'^\s*#include\s+',         # C/C++ includes
            r'^\s*require\s*\(',        # JavaScript require
            r'^\s*import\s+.*\s+from',  # ES6 imports
            r'^\s*using\s+',            # C# using
            r'^\s*package\s+',          # Java package
        ]
        
        # Calculate Fan-In (how many times this module is referenced)
        fan_in_patterns = [
            r'export\s+',               # JavaScript/TypeScript exports
            r'module\.exports\s*=',     # Node.js exports
            r'public\s+class\s+',       # Java public classes
            r'public\s+interface\s+',   # Java public interfaces
            r'def\s+\w+\s*\(',         # Python function definitions
            r'class\s+\w+\s*[:\(]',    # Python class definitions
        ]
        
        for line in added_lines:
            # Count Fan-Out (outgoing dependencies)
            for pattern in fan_out_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    coupling_metrics['fan_out'] += 1
                    coupling_metrics['imports_added'] += 1
                    break
            
            # Count Fan-In indicators (potential incoming dependencies)
            for pattern in fan_in_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    coupling_metrics['fan_in'] += 1
                    coupling_metrics['exports_added'] += 1
                    break
        
        # Calculate coupling factor (Fan-Out / (Fan-In + Fan-Out))
        total_coupling = coupling_metrics['fan_in'] + coupling_metrics['fan_out']
        if total_coupling > 0:
            coupling_metrics['coupling_factor'] = coupling_metrics['fan_out'] / total_coupling
        
        return coupling_metrics
    
    def _calculate_risk_assessment(self, basic: Dict, complexity: Dict, coupling: Dict, design: Dict) -> Dict[str, Any]:
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
        
        # Coupling-based risk
        fan_out = coupling.get('fan_out', 0)
        coupling_factor = coupling.get('coupling_factor', 0.0)
        
        if fan_out > 15:
            risk_score += 3
            risk_factors.append(f'High coupling - many dependencies ({fan_out})')
        elif fan_out > 8:
            risk_score += 2
            risk_factors.append(f'Medium coupling ({fan_out} dependencies)')
        elif fan_out > 4:
            risk_score += 1
            risk_factors.append(f'Some coupling ({fan_out} dependencies)')
        
        if coupling_factor > 0.8:
            risk_score += 2
            risk_factors.append(f'High outgoing coupling factor ({coupling_factor:.2f})')
        elif coupling_factor > 0.6:
            risk_score += 1
            risk_factors.append(f'Medium outgoing coupling factor ({coupling_factor:.2f})')
        
        # Design-based risk
        design_issues = design.get('design_issues_found', 0)
        high_severity = design.get('high_severity_issues', 0)
        
        if high_severity > 0:
            risk_score += 3
            risk_factors.append(f'High severity design issues ({high_severity})')
        elif design_issues > 3:
            risk_score += 2
            risk_factors.append(f'Multiple design issues ({design_issues})')
        elif design_issues > 0:
            risk_score += 1
            risk_factors.append(f'Design issues detected ({design_issues})')
        
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
 