#!/usr/bin/env python3
"""
AI-based PR Labeler using Google Gemini for classification
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from config import GOOGLE_API_KEY, GEMINI_MODEL
from utils.github_client import GitHubClient

logger = logging.getLogger(__name__)

class AIPRLabeler:
    """AI-powered PR labeler using Google Gemini"""
    
    def __init__(self):
        """Initialize the AI PR labeler"""
        try:
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required for AI labeling")
            
            # Configure Google Generative AI
            genai.configure(api_key=GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
            
            # Initialize GitHub client for fetching repo labels
            self.github_client = GitHubClient()
            
            logger.info("AI PR Labeler initialized with Google Gemini")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI PR Labeler: {e}")
            raise
    
    def get_repository_labels(self, repo: str) -> List[str]:
        """
        Fetch all available labels from the repository
        
        Args:
            repo: Repository name in format "owner/repo"
            
        Returns:
            List of available label names
        """
        try:
            labels_data = self.github_client.get_repository_labels(repo)
            label_names = [label['name'] for label in labels_data if 'name' in label]
            
            logger.info(f"Fetched {len(label_names)} labels from repository {repo}")
            return label_names
            
        except Exception as e:
            logger.error(f"Failed to fetch repository labels: {e}")
            # Return default RUXAILAB labels as fallback
            return [
                "accessibility", "user-testing", "eye-tracking", "vr-ar", 
                "research", "figma-integration", "documentation", "feature", 
                "bug", "enhancement", "testing", "ui/ux", "backend", 
                "security", "performance", "dependencies", "ci/cd"
            ]
    
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
            # Get available labels from repository
            if repo:
                available_labels = self.get_repository_labels(repo)
            else:
                # Use default labels if repo not specified
                available_labels = [
                    "accessibility", "user-testing", "eye-tracking", "vr-ar", 
                    "research", "figma-integration", "documentation", "feature", 
                    "bug", "enhancement", "testing", "ui/ux", "backend", 
                    "security", "performance", "dependencies", "ci/cd"
                ]
            
            # Build the AI prompt
            prompt = self._build_classification_prompt(pr_data, available_labels)
            
            # Get AI classification with retry logic
            response = self._make_ai_request_with_retry(prompt)
            
            # Parse AI response
            predicted_labels = self._parse_ai_response(response.text, available_labels)
            
            logger.info(f"AI predicted {len(predicted_labels)} labels for PR")
            return predicted_labels
            
        except Exception as e:
            logger.error(f"Failed to predict labels with AI: {e}")
            return []
    
    def _build_classification_prompt(self, pr_data: Dict[str, Any], available_labels: List[str]) -> str:
        """Build the prompt for AI classification"""
        
        title = pr_data.get('title', 'No title')
        description = pr_data.get('body', 'No description')
        diff = pr_data.get('diff', 'No diff available')
        metrics = pr_data.get('metrics', {})
        
        # Get file changes summary
        files_changed = []
        if diff:
            for line in diff.split('\n'):
                if line.startswith('+++') and len(line) > 6:
                    file_path = line[6:]
                    files_changed.append(file_path)
        
        files_summary = ', '.join(files_changed[:10])  # Limit to first 10 files
        if len(files_changed) > 10:
            files_summary += f" (and {len(files_changed) - 10} more files)"
        
        prompt = f"""
You are an expert at classifying GitHub Pull Requests. Analyze this PR and select the most appropriate labels.

**PR INFORMATION:**
Title: {title}
Description: {description}

**CODE CHANGES:**
Files changed: {files_summary}
Lines added: {metrics.get('lines_added', 0)}
Lines deleted: {metrics.get('lines_deleted', 0)}
Functions added: {metrics.get('functions_added', 0)}
Risk level: {metrics.get('risk_level', 'UNKNOWN')}

**CODE DIFF (first 2000 chars):**
{diff[:2000]}

**AVAILABLE LABELS:**
{', '.join(available_labels)}

**INSTRUCTIONS:**
1. Analyze the PR title, description, and code changes
2. Select 1-5 most relevant labels from the available labels list
3. Assign confidence scores (0.0-1.0) for each selected label
4. Focus on the main purpose and impact of the PR

**OUTPUT FORMAT:**
Return your response as a JSON-like format:
```
LABEL: label_name | CONFIDENCE: 0.85 | REASON: brief explanation
LABEL: another_label | CONFIDENCE: 0.70 | REASON: brief explanation
```

Only select labels that are highly relevant. Be selective and accurate.
"""
        
        return prompt
    
    def _make_ai_request_with_retry(self, prompt: str, max_retries: int = 3, base_delay: int = 30) -> Any:
        """
        Make AI request with intelligent retry logic for quota limits
        
        Args:
            prompt: The prompt to send to the AI
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            
        Returns:
            AI response object
        """
        import random
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Making AI request (attempt {attempt + 1}/{max_retries + 1})")
                
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=1000,
                    )
                )
                
                logger.info("AI request successful!")
                return response
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Check if this is the last attempt
                is_last_attempt = attempt == max_retries
                
                # Handle quota/rate limit errors specifically
                if any(keyword in error_message for keyword in [
                    'quota', 'rate limit', 'limit exceeded', 'resource_exhausted'
                ]):
                    
                    if is_last_attempt:
                        logger.error(f"Quota limit reached after {max_retries + 1} attempts. Giving up.")
                        raise
                    
                    # Try to extract retry delay from error message
                    retry_delay = self._extract_retry_delay(str(e))
                    
                    if retry_delay is None:
                        # Use exponential backoff with jitter
                        retry_delay = base_delay * (2 ** attempt) + random.randint(1, 10)
                    
                    logger.warning(
                        f"⏳ Quota limit hit on attempt {attempt + 1}. "
                        f"Waiting {retry_delay} seconds before retry..."
                    )
                    
                    # Show progress during wait
                    self._wait_with_progress(retry_delay)
                    continue
                
                # Handle other Google API errors
                elif any(keyword in error_message for keyword in [
                    'invalid_argument', 'permission_denied', 'unauthenticated'
                ]):
                    logger.error(f"API configuration error: {e}")
                    raise  # Don't retry for configuration errors
                
                # Handle temporary/network errors
                elif any(keyword in error_message for keyword in [
                    'timeout', 'connection', 'network', 'unavailable'
                ]):
                    
                    if is_last_attempt:
                        logger.error(f"Network error after {max_retries + 1} attempts: {e}")
                        raise
                    
                    # Shorter delay for network errors
                    retry_delay = min(base_delay * (2 ** attempt), 60) + random.randint(1, 5)
                    
                    logger.warning(
                        f"🌐 Network error on attempt {attempt + 1}: {e}. "
                        f"Retrying in {retry_delay} seconds..."
                    )
                    
                    time.sleep(retry_delay)
                    continue
                
                # Unknown error - retry with backoff
                else:
                    if is_last_attempt:
                        logger.error(f"Unknown error after {max_retries + 1} attempts: {e}")
                        raise
                    
                    retry_delay = base_delay * (2 ** attempt) + random.randint(1, 5)
                    
                    logger.warning(
                        f"⚠️  Unknown error on attempt {attempt + 1}: {e}. "
                        f"Retrying in {retry_delay} seconds..."
                    )
                    
                    time.sleep(retry_delay)
                    continue
        
        # This should never be reached, but just in case
        raise Exception("Exhausted all retry attempts")
    
    def _extract_retry_delay(self, error_message: str) -> Optional[int]:
        """
        Extract retry delay from Google API error message
        
        Args:
            error_message: Error message from Google API
            
        Returns:
            Retry delay in seconds if found, None otherwise
        """
        try:
            # Look for patterns like "retry_delay { seconds: 56 }"
            retry_pattern = r'retry_delay\s*{\s*seconds:\s*(\d+)'
            match = re.search(retry_pattern, error_message)
            
            if match:
                delay = int(match.group(1))
                logger.info(f"🕒 API provided retry delay: {delay} seconds")
                return delay + 5  # Add 5 second buffer
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract retry delay: {e}")
            return None
    
    def _wait_with_progress(self, total_seconds: int):
        """
        Wait with a progress indicator
        
        Args:
            total_seconds: Total time to wait in seconds
        """
        print(f"\n⏳ Waiting for quota reset ({total_seconds}s):")
        
        # Show progress in chunks of 10 seconds or less
        chunk_size = min(10, total_seconds // 10) if total_seconds > 10 else 1
        
        for i in range(0, total_seconds, chunk_size):
            remaining = total_seconds - i
            chunk_wait = min(chunk_size, remaining)
            
            # Calculate progress
            progress = (i / total_seconds) * 100
            bar_length = 20
            filled_length = int(bar_length * progress // 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            print(f"\r[{bar}] {progress:5.1f}% - {remaining:3d}s remaining", end="", flush=True)
            
            time.sleep(chunk_wait)
        
        print(f"\r[{'█' * 20}] 100.0% - Ready to retry!           ")
        print()
    
    def _parse_ai_response(self, response_text: str, available_labels: List[str]) -> List[Dict[str, Any]]:
        """Parse the AI response into structured label predictions"""
        predicted_labels = []
        
        try:
            lines = response_text.strip().split('\n')
            
            for line in lines:
                if 'LABEL:' in line and 'CONFIDENCE:' in line:
                    # Parse the line format: LABEL: name | CONFIDENCE: 0.85 | REASON: explanation
                    parts = line.split('|')
                    
                    if len(parts) >= 2:
                        # Extract label name
                        label_part = parts[0].strip()
                        if 'LABEL:' in label_part:
                            label_name = label_part.split('LABEL:')[1].strip()
                        
                        # Extract confidence
                        confidence_part = parts[1].strip()
                        if 'CONFIDENCE:' in confidence_part:
                            try:
                                confidence_str = confidence_part.split('CONFIDENCE:')[1].strip()
                                confidence = float(confidence_str)
                            except (ValueError, IndexError):
                                confidence = 0.5  # Default confidence
                        
                        # Extract reason if available
                        reason = ""
                        if len(parts) >= 3 and 'REASON:' in parts[2]:
                            reason = parts[2].split('REASON:')[1].strip()
                        
                        # Validate label exists in available labels
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
    
    def format_label_predictions(self, predictions: List[Dict[str, Any]]) -> str:
        """Format label predictions for display"""
        if not predictions:
            return "No labels predicted by AI for this PR."
        
        formatted = "## AI-Predicted Labels\n\n"
        
        for i, label in enumerate(predictions, 1):
            confidence_bar = "█" * int(label["confidence"] * 10)
            confidence_percent = int(label["confidence"] * 100)
            
            formatted += f"{i}. **{label['name']}** "
            formatted += f"({confidence_percent}% confidence)\n"
            formatted += f"   `{confidence_bar}` {label['confidence']:.2f}\n"
            
            if label.get('reason'):
                formatted += f"   *Reason: {label['reason']}*\n"
            
            formatted += "\n"
        
        formatted += "---\n"
        formatted += "*Labels predicted by Google Gemini AI based on PR analysis*\n"
        
        return formatted
    
    def update_repository_labels_cache(self, repo: str, output_file: str = "data/repo_labels.json"):
        """
        Fetch and cache all repository labels for future use
        
        Args:
            repo: Repository name in format "owner/repo"
            output_file: File to save the labels cache
        """
        try:
            import json
            from pathlib import Path
            
            # Fetch labels from repository
            labels_data = self.github_client.get_repository_labels(repo)
            
            # Format labels data
            labels_cache = {
                'repository': repo,
                'last_updated': self._get_timestamp(),
                'labels': []
            }
            
            for label in labels_data:
                labels_cache['labels'].append({
                    'name': label.get('name', ''),
                    'description': label.get('description', ''),
                    'color': label.get('color', ''),
                })
            
            # Save to file
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(labels_cache, f, indent=2)
            
            logger.info(f"Updated repository labels cache: {len(labels_cache['labels'])} labels saved to {output_file}")
            return labels_cache['labels']
            
        except Exception as e:
            logger.error(f"Failed to update repository labels cache: {e}")
            return []
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat() 