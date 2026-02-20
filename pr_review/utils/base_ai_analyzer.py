#!/usr/bin/env python3
"""
Base AI Analyzer - Shared AI functionality for PR analysis
"""

import logging
import json
from typing import Dict, Any, List
import google.generativeai as genai

try:
    from pr_review.config import GOOGLE_API_KEY
except ImportError:
    from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

class BaseAIAnalyzer:
    """Base class for AI-powered analysis using Gemini"""
    
    def __init__(self, model_name: str = 'gemini-1.5-flash'):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required for AI analysis")
        
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"AI Analyzer initialized with {model_name}")
    
    def make_ai_request(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Make AI request with standard configuration"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"AI request failed: {e}")
            raise
    
    def parse_json_response(self, response_text: str, fallback_result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON from AI response with fallback"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON found in AI response")
                return fallback_result
            
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return fallback_result
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return fallback_result
    
    def extract_added_code_from_diff(self, diff: str) -> Dict[str, List[str]]:
        """Extract only the added code lines from git diff"""
        added_code = {}
        current_file = None
        
        for line in diff.split('\n'):
            if line.startswith('+++'):
                if len(line) > 6:
                    current_file = line[6:].strip()
                    if current_file.startswith('b/'):
                        current_file = current_file[2:]
                    added_code[current_file] = []
                continue
            
            if current_file and line.startswith('+') and not line.startswith('+++'):
                code_line = line[1:]
                added_code[current_file].append(code_line)
        
        return added_code
    
    def is_analyzable_file(self, filename: str) -> bool:
        """Check if file should be analyzed"""
        analyzable_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.cs'}
        return any(filename.lower().endswith(ext) for ext in analyzable_extensions)