#!/usr/bin/env python3
"""
AI-based PR Labeler using Google Gemini for classification
"""

import logging
import os
from typing import List, Dict, Any
from .base_ai_analyzer import BaseAIAnalyzer

logger = logging.getLogger(__name__)

class AIPRLabeler(BaseAIAnalyzer):
    """AI-powered PR labeler using Google Gemini"""
    
    def __init__(self):
        super().__init__('gemini-1.5-flash')
        logger.info("AI PR Labeler initialized")
    
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
            response_text = self.make_ai_request(prompt)
            predicted_labels = self._parse_response(response_text, available_labels)
            
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
            github_org = repo.split('/')[0] if '/' in repo else None
            label_data = get_document('repository_labels', doc_id, github_org=github_org)
            
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