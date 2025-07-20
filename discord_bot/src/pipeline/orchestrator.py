"""
Pipeline Orchestrator

Orchestrates the entire data pipeline using Strategy pattern and dependency injection.
Replaces scattered pipeline scripts with unified, testable orchestration.
"""

import asyncio
from typing import Dict, Any, List
from ..core.interfaces import IStorageService, IDiscordService, IDataProcessor
from ..core.container import container
from .processors import ContributionProcessor, AnalyticsProcessor, MetricsProcessor

class PipelineStage:
    """Base class for pipeline stages using Template Method pattern."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the pipeline stage."""
        print(f"========== {self.name} ==========")
        try:
            result = await self._run(context)
            print(f"{self.name} - COMPLETED")
            return result
        except Exception as e:
            print(f"{self.name} - FAILED: {e}")
            raise
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses."""
        raise NotImplementedError

class DataCollectionStage(PipelineStage):
    """Stage 1: Raw data collection from GitHub."""
    
    def __init__(self):
        super().__init__("Stage 1: Data Collection")
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect raw GitHub data."""
        # This would integrate with the existing collect_raw_data.py logic
        # For now, assume data is already collected
        import json
        import os
        
        if os.path.exists("raw_github_data.json"):
            with open("raw_github_data.json", "r") as f:
                raw_data = json.load(f)
            print(f"Loaded raw data for {len(raw_data.get('repositories', {}))} repositories")
            context['raw_data'] = raw_data
        else:
            raise FileNotFoundError("Raw data not found. Run data collection first.")
        
        return context

class DataProcessingStage(PipelineStage):
    """Stage 2: Data processing using injected processors."""
    
    def __init__(self):
        super().__init__("Stage 2: Data Processing")
        self.contribution_processor = ContributionProcessor()
        self.analytics_processor = AnalyticsProcessor()
        self.metrics_processor = MetricsProcessor()
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw data into structured analytics."""
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
        return context

class DataStorageStage(PipelineStage):
    """Stage 3: Data storage using injected storage service."""
    
    def __init__(self, storage_service: IStorageService):
        super().__init__("Stage 3: Data Storage")
        self.storage = storage_service
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Store processed data using dependency injection."""
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
        for username, user_data in contributions.items():
            # Find Discord user mapping
            user_mappings = self.storage.query_collection('discord')
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
        return context

class DiscordUpdateStage(PipelineStage):
    """Stage 4: Discord updates using injected Discord service."""
    
    def __init__(self, discord_service: IDiscordService, storage_service: IStorageService):
        super().__init__("Stage 4: Discord Updates")
        self.discord = discord_service
        self.storage = storage_service
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update Discord roles and channels."""
        contributions = context.get('contributions', {})
        repo_metrics = context.get('repo_metrics', {})
        
        # Get user mappings from storage
        user_mappings_data = self.storage.query_collection('discord')
        user_mappings = {}
        
        for discord_id, data in user_mappings_data.items():
            github_id = data.get('github_id')
            if github_id:
                user_mappings[discord_id] = github_id
        
        # Update roles (assumes single guild for now)
        guild_id = "YOUR_GUILD_ID"  # This would come from configuration
        
        roles_updated = await self.discord.update_roles(guild_id, user_mappings, contributions)
        if not roles_updated:
            print("Warning: Role updates failed")
        
        # Update channels
        channels_updated = await self.discord.update_channels(guild_id, repo_metrics)
        if not channels_updated:
            print("Warning: Channel updates failed")
        
        print("Discord updates completed")
        return context

class PipelineOrchestrator:
    """
    Main pipeline orchestrator using Strategy pattern.
    Manages pipeline execution with dependency injection.
    """
    
    def __init__(self):
        self.stages: List[PipelineStage] = []
        self._setup_dependencies()
    
    def _setup_dependencies(self):
        """Setup dependency injection container."""
        from ..core.interfaces import IStorageService, IDiscordService
        from ..core.services import FirestoreService, DiscordBotService
        
        # Register services
        container.register_singleton(IStorageService, FirestoreService)
        container.register_singleton(IDiscordService, DiscordBotService)
    
    def add_stage(self, stage: PipelineStage) -> 'PipelineOrchestrator':
        """Add a pipeline stage."""
        self.stages.append(stage)
        return self
    
    async def execute_full_pipeline(self) -> Dict[str, Any]:
        """Execute the complete pipeline."""
        print("="*60)
        print("Starting Discord Bot Data Pipeline")
        print("="*60)
        
        context = {}
        
        try:
            # Setup default pipeline stages
            if not self.stages:
                self._setup_default_stages()
            
            # Execute stages sequentially
            for stage in self.stages:
                context = await stage.execute(context)
            
            print("="*60)
            print("Pipeline completed successfully")
            print("="*60)
            return context
            
        except Exception as e:
            print(f"Pipeline failed: {e}")
            raise
    
    def _setup_default_stages(self):
        """Setup default pipeline stages with dependency injection."""
        storage_service = container.resolve(IStorageService)
        discord_service = container.resolve(IDiscordService)
        
        self.stages = [
            DataCollectionStage(),
            DataProcessingStage(),
            DataStorageStage(storage_service),
            DiscordUpdateStage(discord_service, storage_service)
        ]

# Factory function for easy usage
def create_pipeline_orchestrator() -> PipelineOrchestrator:
    """Create a configured pipeline orchestrator."""
    return PipelineOrchestrator()

async def run_full_pipeline():
    """Convenience function to run the complete pipeline."""
    orchestrator = create_pipeline_orchestrator()
    return await orchestrator.execute_full_pipeline() 