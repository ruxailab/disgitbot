#!/usr/bin/env python3
"""
AI-Powered Design Principles Analyzer using Gemini
Analyzes code changes against SOLID principles and design patterns
"""

import logging
from typing import Dict, Any, List
from .base_ai_analyzer import BaseAIAnalyzer

logger = logging.getLogger(__name__)

class AIDesignAnalyzer(BaseAIAnalyzer):
    """AI-powered design principles analyzer using Gemini"""
    
    def __init__(self):
        super().__init__('gemini-1.5-flash')
        
        self.analysis_prompt = """
You are a strict, professional code architecture reviewer. Analyze the provided code changes for design principle violations.

CRITICAL: UNNECESSARY ABSTRACTION IS THE BIGGEST PITFALL. Only suggest refactoring when it genuinely helps.

ANALYSIS CRITERIA - Apply patterns ONLY when these problems exist:
- God classes or God files (files/classes doing too much)
- Tight coupling / low modularity between components
- Repetitive conditional logic or type-checking across modules
- Complex object creation logic scattered in main execution code
- Violations of Open/Closed Principle (requiring modification instead of extension)

NEVER suggest patterns for:
- Single implementations that won't change
- Simple data structures or DTOs
- One-time scripts or utilities
- Abstract interfaces with only one concrete implementation
- Code that works fine as-is, even if it could be "more elegant"

RULE OF THREE: Only abstract after the third duplication.

PRAGMATIC APPROACH:
- Prefer composition over inheritance
- Keep abstractions minimal and focused
- Use concrete classes unless polymorphism is actually needed
- Focus on making code easier to understand, test, and modify
- Do NOT demonstrate pattern knowledge for its own sake

SOLID PRINCIPLES FOCUS:
- Single Responsibility Principle
- Open/Closed Principle  
- Interface Segregation Principle
- Dependency Inversion Principle

For each issue found, provide:
1. Principle name
2. Succinct description (1 sentence)
3. Relevant code snippet (truncated if long)
4. Specific refactoring suggestions (file structure, class modularization ideas)

Only flag issues that genuinely hurt scalability and maintainability. When in doubt, DO NOT suggest changes.

Return response as JSON:
{
  "design_issues_found": number,
  "design_score": "EXCELLENT|GOOD|FAIR|POOR",
  "issues": [
    {
      "principle": "principle name",
      "description": "brief description",
      "code_snippet": "relevant code",
      "suggestions": ["specific suggestion 1", "specific suggestion 2"],
      "severity": "LOW|MEDIUM|HIGH"
    }
  ]
}

CODE TO ANALYZE:
"""
    
    def analyze_design_principles(self, diff: str, files: List[Dict]) -> Dict[str, Any]:
        """
        Analyze code changes for design principle violations using AI
        
        Args:
            diff: Git diff string
            files: List of file change data from GitHub API
            
        Returns:
            AI analysis results with identified issues and suggestions
        """
        try:
            added_code_by_file = self.extract_added_code_from_diff(diff)
            
            if not added_code_by_file:
                return self._empty_analysis()
            
            code_context = self._prepare_code_context(added_code_by_file, files)
            
            if not code_context.strip():
                return self._empty_analysis()
            
            full_prompt = self.analysis_prompt + code_context
            response_text = self.make_ai_request(full_prompt)
            
            return self._parse_ai_response(response_text)
            
        except Exception as e:
            logger.error(f"Error in AI design analysis: {e}")
            return self._empty_analysis()
    
    def _prepare_code_context(self, added_code_by_file: Dict[str, List[str]], files: List[Dict]) -> str:
        """Prepare code context for AI analysis"""
        context_parts = []
        
        for filename, code_lines in added_code_by_file.items():
            if not self.is_analyzable_file(filename):
                continue
                
            code_content = '\n'.join(code_lines)
            if not code_content.strip():
                continue
            
            # Get file stats
            file_info = next((f for f in files if f.get('filename') == filename), {})
            additions = file_info.get('additions', 0)
            
            context_parts.append(f"""
FILE: {filename} (+{additions} lines)
{'-' * 50}
{code_content[:2000]}  # Truncate very long files
{'-' * 50}
""")
        
        return '\n'.join(context_parts)
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        result = self.parse_json_response(response_text, self._empty_analysis())
        
        # Validate required fields
        required_fields = ['design_issues_found', 'design_score', 'issues']
        if not all(field in result for field in required_fields):
            logger.warning("AI response missing required fields")
            return self._empty_analysis()
        
        # Add derived metrics for consistency with existing system
        issues = result.get('issues', [])
        result['high_severity_issues'] = sum(1 for issue in issues if issue.get('severity') == 'HIGH')
        result['medium_severity_issues'] = sum(1 for issue in issues if issue.get('severity') == 'MEDIUM')
        result['low_severity_issues'] = sum(1 for issue in issues if issue.get('severity') == 'LOW')
        
        return result
    

    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis result"""
        return {
            'design_issues_found': 0,
            'design_score': 'EXCELLENT',
            'high_severity_issues': 0,
            'medium_severity_issues': 0,
            'low_severity_issues': 0,
            'issues': []
        }