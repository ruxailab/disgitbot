"""
Pipeline Orchestrator

Simple, clean pipeline execution without unnecessary abstractions.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

from core.services import FirestoreService, DiscordBotService
from core.github_service import GitHubService  
from core.role_service import RoleService
from pipeline.processors import ContributionProcessor, AnalyticsProcessor, MetricsProcessor

class PipelineStageError(Exception):
    """Exception raised when a pipeline stage fails."""
    
    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.original_error = original_error

class DataCollectionStage:
    """Stage 1: Raw data collection from GitHub."""
    
    def __init__(self):
        self.github_service = GitHubService()
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect raw GitHub data."""
        print("========== Stage 1: Data Collection ==========")
        
        try:
            raw_data = self.github_service.collect_organization_data()
            
            # Save raw data for debugging/backup
            with open("raw_github_data.json", "w") as f:
                json.dump(raw_data, f, indent=2)
            
            print(f"Collected raw data for {len(raw_data.get('repositories', {}))} repositories")
            context['raw_data'] = raw_data
            
            print("Stage 1: Data Collection - COMPLETED")
            return context
            
        except Exception as e:
            print(f"Stage 1: Data Collection - FAILED: {e}")
            # Try to load from existing file as fallback
            if os.path.exists("raw_github_data.json"):
                print("Attempting to load from existing raw_github_data.json...")
                with open("raw_github_data.json", "r") as f:
                    raw_data = json.load(f)
                context['raw_data'] = raw_data
                print(f"Loaded fallback data for {len(raw_data.get('repositories', {}))} repositories")
                return context
            else:
                raise PipelineStageError("Data collection failed", e)

class DataProcessingStage:
    """Stage 2: Data processing using specific processors."""
    
    def __init__(self):
        self.contribution_processor = ContributionProcessor()
        self.analytics_processor = AnalyticsProcessor()
        self.metrics_processor = MetricsProcessor()
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw data into structured analytics."""
        print("========== Stage 2: Data Processing ==========")
        
        try:
            raw_data = context.get('raw_data')
            if not raw_data:
                raise ValueError("No raw data found in context")
            
            # Process contributions
            contributions = self.contribution_processor.process_raw_data(raw_data)
            contributions = self.contribution_processor.calculate_rankings(contributions)
            contributions = self.contribution_processor.calculate_streaks_and_averages(contributions)
            
            # Generate analytics
            hall_of_fame = self.analytics_processor.create_hall_of_fame_data(contributions)
            analytics_data = self.analytics_processor.create_analytics_data(contributions)
            
            # Calculate metrics
            repo_metrics = self.metrics_processor.create_repo_metrics(raw_data, contributions)
            
            context.update({
                'contributions': contributions,
                'hall_of_fame': hall_of_fame,
                'analytics_data': analytics_data,
                'repo_metrics': repo_metrics
            })
            
            print(f"Processed data for {len(contributions)} contributors")
            print("Stage 2: Data Processing - COMPLETED")
            return context
            
        except Exception as e:
            print(f"Stage 2: Data Processing - FAILED: {e}")
            raise PipelineStageError("Data processing failed", e)

class DataStorageStage:
    """Stage 3: Data storage to Firestore."""
    
    def __init__(self):
        self.storage = FirestoreService()
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Store processed data in Firestore."""
        print("========== Stage 3: Data Storage ==========")
        
        try:
            contributions = context.get('contributions', {})
            repo_metrics = context.get('repo_metrics', {})
            hall_of_fame = context.get('hall_of_fame', {})
            analytics_data = context.get('analytics_data', {})
            
            # Store repository metrics
            if repo_metrics:
                success = self.storage.set_document('repo_stats', 'metrics', repo_metrics)
                if not success:
                    raise Exception("Failed to store repository metrics")
            
            # Store hall of fame
            if hall_of_fame:
                success = self.storage.set_document('repo_stats', 'hall_of_fame', hall_of_fame)
                if not success:
                    raise Exception("Failed to store hall of fame")
            
            # Store analytics data
            if analytics_data:
                success = self.storage.set_document('repo_stats', 'analytics', analytics_data)
                if not success:
                    raise Exception("Failed to store analytics data")
            
            # Store individual contributions
            stored_count = 0
            user_mappings = self.storage.query_collection('discord')
            
            for username, user_data in contributions.items():
                # Find Discord user mapping
                discord_id = None
                for uid, data in user_mappings.items():
                    if data.get('github_id') == username:
                        discord_id = uid
                        break
                
                if discord_id:
                    success = self.storage.update_document('discord', discord_id, user_data)
                    if success:
                        stored_count += 1
            
            print(f"Stored data for {stored_count} users")
            print("Stage 3: Data Storage - COMPLETED")
            return context
            
        except Exception as e:
            print(f"Stage 3: Data Storage - FAILED: {e}")
            raise PipelineStageError("Data storage failed", e)

class DiscordUpdateStage:
    """Stage 4: Discord role and channel updates."""
    
    def __init__(self):
        self.storage = FirestoreService()
        self.role_service = RoleService(self.storage)
        self.discord_service = DiscordBotService(self.role_service)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update Discord roles and channels."""
        print("========== Stage 4: Discord Updates ==========")
        
        try:
            contributions = context.get('contributions', {})
            repo_metrics = context.get('repo_metrics', {})
            
            # Get user mappings from storage
            user_mappings_data = self.storage.query_collection('discord')
            user_mappings = {}
            
            for discord_id, data in user_mappings_data.items():
                github_id = data.get('github_id')
                if github_id:
                    user_mappings[discord_id] = github_id
            
            # Update roles across all guilds
            roles_updated = await self.discord_service.update_roles(user_mappings, contributions)
            if not roles_updated:
                print("Warning: Role updates failed")
            
            # Update channels across all guilds
            channels_updated = await self.discord_service.update_channels(repo_metrics)
            if not channels_updated:
                print("Warning: Channel updates failed")
            
            print("Stage 4: Discord Updates - COMPLETED")
            return context
            
        except Exception as e:
            print(f"Stage 4: Discord Updates - FAILED: {e}")
            raise PipelineStageError("Discord updates failed", e)

class PipelineOrchestrator:
    """Simple pipeline orchestrator without dependency injection complexity."""
    
    def __init__(self):
        self.stages = [
            DataCollectionStage(),
            DataProcessingStage(),
            DataStorageStage(),
            DiscordUpdateStage()
        ]
    
    async def execute_full_pipeline(self) -> Dict[str, Any]:
        """Execute the complete pipeline with error handling."""
        print("="*60)
        print("Starting Discord Bot Data Pipeline")
        print("="*60)
        
        context = {}
        completed_stages = []
        
        try:
            for i, stage in enumerate(self.stages):
                stage_name = stage.__class__.__name__
                print(f"Executing stage {i+1}/{len(self.stages)}: {stage_name}")
                
                context = await stage.execute(context)
                completed_stages.append(stage_name)
                
                progress = ((i + 1) / len(self.stages)) * 100
                print(f"Pipeline progress: {progress:.1f}% ({i+1}/{len(self.stages)} stages completed)")
            
            print("="*60)
            print("Pipeline completed successfully")
            print(f"Completed stages: {len(completed_stages)}")
            for stage_name in completed_stages:
                print(f"  ✓ {stage_name}")
            print("="*60)
            
            return context
            
        except PipelineStageError as e:
            print("="*60)
            print("Pipeline failed")
            print(f"Error: {e}")
            print(f"Completed stages before failure: {len(completed_stages)}")
            for stage_name in completed_stages:
                print(f"  ✓ {stage_name}")
            print("="*60)
            raise

# Entry point for external scripts
async def run_full_pipeline() -> Dict[str, Any]:
    """Run the complete data pipeline."""
    orchestrator = PipelineOrchestrator()
    return await orchestrator.execute_full_pipeline() 