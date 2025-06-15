#!/usr/bin/env python3
"""
AI-based PR Labeler using Google Gemini for classification
"""

import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
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
            
            # Get AI classification
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                )
            )
            
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
        
        formatted = "## 🤖 AI-Predicted Labels\n\n"
        
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