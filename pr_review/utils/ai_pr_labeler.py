#!/usr/bin/env python3
"""
AI-based PR Labeler using Google Gemini for classification
"""

import logging
import time
import re
import random
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from config import GOOGLE_API_KEY, GEMINI_MODEL
import os

logger = logging.getLogger(__name__)


class AIRetryHandler:
    """Handles AI API retry logic with intelligent backoff and quota management"""
    
    def __init__(self, max_retries: int = 3, base_delay: int = 30):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def execute_with_retry(self, ai_request_func, prompt: str) -> Any:
        """Execute AI request with comprehensive retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Making AI request (attempt {attempt + 1}/{self.max_retries + 1})")
                return ai_request_func(prompt)
                
            except Exception as e:
                if self._should_stop_retrying(e, attempt):
                    raise
                
                retry_delay = self._calculate_retry_delay(e, attempt)
                self._wait_with_feedback(retry_delay, attempt + 1)
        
        raise Exception("Exhausted all retry attempts")
    
    def _should_stop_retrying(self, error: Exception, attempt: int) -> bool:
        """Determine if we should stop retrying based on error type and attempt"""
        error_message = str(error).lower()
        is_last_attempt = attempt == self.max_retries
        
        # Configuration errors - don't retry
        if any(keyword in error_message for keyword in [
            'invalid_argument', 'permission_denied', 'unauthenticated'
        ]):
            logger.error(f"API configuration error: {error}")
            return True
        
        # Quota/rate limit errors - retry unless last attempt
        if any(keyword in error_message for keyword in [
            'quota', 'rate limit', 'limit exceeded', 'resource_exhausted'
        ]):
            if is_last_attempt:
                logger.error(f"Quota limit reached after {self.max_retries + 1} attempts")
                return True
            logger.warning(f"Quota limit hit on attempt {attempt + 1}")
            return False
        
        # Network/temporary errors - retry unless last attempt
        if any(keyword in error_message for keyword in [
            'timeout', 'connection', 'network', 'unavailable'
        ]):
            if is_last_attempt:
                logger.error(f"Network error after {self.max_retries + 1} attempts: {error}")
                return True
            logger.warning(f"Network error on attempt {attempt + 1}: {error}")
            return False
        
        # Unknown errors - retry unless last attempt
        if is_last_attempt:
            logger.error(f"Unknown error after {self.max_retries + 1} attempts: {error}")
            return True
        
        logger.warning(f"Unknown error on attempt {attempt + 1}: {error}")
        return False
    
    def _calculate_retry_delay(self, error: Exception, attempt: int) -> int:
        """Calculate appropriate retry delay based on error and attempt"""
        error_message = str(error)
        
        # Try to extract API-provided delay
        api_delay = self._extract_api_delay(error_message)
        if api_delay:
            return api_delay + 5  # Add buffer
        
        # Use different strategies for different error types
        if any(keyword in error_message.lower() for keyword in [
            'quota', 'rate limit', 'limit exceeded', 'resource_exhausted'
        ]):
            # Longer delay for quota issues
            return self.base_delay * (2 ** attempt) + random.randint(1, 10)
        else:
            # Shorter delay for network/temporary issues
            return min(self.base_delay * (2 ** attempt), 60) + random.randint(1, 5)
    
    def _extract_api_delay(self, error_message: str) -> Optional[int]:
        """Extract retry delay from API error message if available"""
        try:
            retry_pattern = r'retry_delay\s*{\s*seconds:\s*(\d+)'
            match = re.search(retry_pattern, error_message)
            
            if match:
                delay = int(match.group(1))
                logger.info(f"API provided retry delay: {delay} seconds")
                return delay
            
            return None
        except Exception:
            return None
    
    def _wait_with_feedback(self, total_seconds: int, attempt: int):
        """Wait with progress feedback"""
        logger.info(f"Waiting {total_seconds}s before retry (attempt {attempt})")
        
        # Show progress in chunks for long waits
        if total_seconds > 10:
            chunk_size = min(10, total_seconds // 10)
            
            for i in range(0, total_seconds, chunk_size):
                remaining = total_seconds - i
                chunk_wait = min(chunk_size, remaining)
                
                progress = (i / total_seconds) * 100
                logger.info(f"Waiting... {progress:.1f}% complete - {remaining}s remaining")
                
                time.sleep(chunk_wait)
        else:
            time.sleep(total_seconds)


class AIPRLabeler:
    """AI-powered PR labeler using Google Gemini"""
    
    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required for AI labeling")
        
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.retry_handler = AIRetryHandler()
        
        logger.info("AI PR Labeler initialized with Google Gemini")
    
    def predict_labels(self, pr_data: Dict[str, Any], repo: str = None) -> List[Dict[str, Any]]:
        """
        Predict labels for a PR using AI classification
        
        Args:
            pr_data: Dictionary containing PR information
            repo: Repository name (optional, for fetching available labels)
            
        Returns:
            List of predicted labels with confidence scores
        """
        try:
            if not repo:
                raise ValueError("Repository name is required for label prediction")
            available_labels = self._get_repository_labels(repo)
            
            prompt = self._build_classification_prompt(pr_data, available_labels)
            response = self.retry_handler.execute_with_retry(self._make_ai_request, prompt)
            predicted_labels = self._parse_response(response.text, available_labels)
            
            logger.info(f"AI predicted {len(predicted_labels)} labels for PR")
            return predicted_labels
            
        except Exception as e:
            logger.error(f"Failed to predict labels with AI: {e}")
            return []
    
    def _get_repository_labels(self, repo: str) -> List[str]:
        """Get available label names for a repository from stored data"""
        try:
            import sys
            import os
            
            from shared.firestore import get_document
            
            doc_id = repo.replace('/', '_')
            label_data = get_document('repository_labels', doc_id)
            
            if label_data and 'labels' in label_data:
                label_names = [
                    label.get('name', '') 
                    for label in label_data['labels']
                    if label.get('name')
                ]
                logger.info(f"Using {len(label_names)} stored labels for repository {repo}")
                return label_names
            
            raise ValueError(f"No labels found for repository {repo}. Run Discord bot pipeline to populate labels.")
            
        except Exception as e:
            logger.error(f"Failed to fetch repository labels: {e}")
            raise
    

    
    def _make_ai_request(self, prompt: str) -> Any:
        """Make a single AI request without retry logic"""
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1000,
            )
        )
        logger.info("AI request successful")
        return response
    
    def _build_classification_prompt(self, pr_data: Dict[str, Any], available_labels: List[str]) -> str:
        """Build the prompt for AI classification"""
        title = pr_data.get('title', 'No title')
        description = pr_data.get('body', 'No description')
        diff = pr_data.get('diff', 'No diff available')
        metrics = pr_data.get('metrics', {})
        
        # Extract file changes from diff
        files_changed = []
        if diff:
            for line in diff.split('\n'):
                if line.startswith('+++') and len(line) > 6:
                    files_changed.append(line[6:])
        
        files_summary = ', '.join(files_changed[:10])
        if len(files_changed) > 10:
            files_summary += f" (and {len(files_changed) - 10} more files)"
        
        # Load prompt template from file
        prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', 'label_classification.txt')
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise Exception("AI prompt template file is missing")
        
        # Format the template with actual data
        return prompt_template.format(
            title=title,
            description=description,
            files_summary=files_summary,
            lines_added=metrics.get('lines_added', 0),
            lines_deleted=metrics.get('lines_deleted', 0),
            functions_added=metrics.get('functions_added', 0),
            risk_level=metrics.get('risk_level', 'UNKNOWN'),
            diff=diff[:2000],
            available_labels=', '.join(available_labels)
        )
    
    def _parse_response(self, response_text: str, available_labels: List[str]) -> List[Dict[str, Any]]:
        """Parse the AI response into structured label predictions"""
        predicted_labels = []
        
        try:
            lines = response_text.strip().split('\n')
            
            for line in lines:
                if 'LABEL:' in line and 'CONFIDENCE:' in line:
                    parts = line.split('|')
                    
                    if len(parts) >= 2:
                        # Extract label name
                        label_part = parts[0].strip()
                        if 'LABEL:' in label_part:
                            label_name = label_part.split('LABEL:')[1].strip()
                        
                        # Extract confidence
                        confidence = 0.5  # Default
                        if 'CONFIDENCE:' in parts[1]:
                            try:
                                confidence_str = parts[1].split('CONFIDENCE:')[1].strip()
                                confidence = float(confidence_str)
                            except (ValueError, IndexError):
                                pass
                        
                        # Extract reason if available
                        reason = ""
                        if len(parts) >= 3 and 'REASON:' in parts[2]:
                            reason = parts[2].split('REASON:')[1].strip()
                        
                        # Validate label exists and meets confidence threshold
                        if label_name in available_labels and confidence >= 0.3:
                            predicted_labels.append({
                                'name': label_name,
                                'confidence': confidence,
                                'reason': reason,
                                'source': 'ai_classification'
                            })
            
            # Sort by confidence and limit to top 5
            predicted_labels.sort(key=lambda x: x['confidence'], reverse=True)
            return predicted_labels[:5]
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return [] 