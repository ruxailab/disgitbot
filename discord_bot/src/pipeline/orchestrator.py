"""
Pipeline Orchestrator

Orchestrates the entire data pipeline using Strategy pattern and dependency injection.
Replaces scattered pipeline scripts with unified, testable orchestration.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os
# Ensure we can import from the src directory
if 'src' not in sys.path:
    src_path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, os.path.abspath(src_path))

from core.interfaces import IStorageService, IDiscordService, IDataProcessor, IGitHubService
from core.container import container
from pipeline.processors import ContributionProcessor, AnalyticsProcessor, MetricsProcessor

class PipelineStage:
    """Base class for pipeline stages using Template Method pattern."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the pipeline stage with comprehensive error handling."""
        print(f"========== {self.name} ==========")
        try:
            result = await self._run(context)
            print(f"{self.name} - COMPLETED")
            return result
        except Exception as e:
            print(f"{self.name} - FAILED: {e}")
            print(f"Error details: {type(e).__name__}: {str(e)}")
            
            # Try to provide helpful context
            if hasattr(e, '__cause__') and e.__cause__:
                print(f"Caused by: {type(e.__cause__).__name__}: {str(e.__cause__)}")
            
            raise PipelineStageError(f"Stage '{self.name}' failed", e) from e
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses."""
        raise NotImplementedError

class PipelineStageError(Exception):
    """Exception raised when a pipeline stage fails."""
    
    def __init__(self, message: str, original_error: Exception):
        super().__init__(message)
        self.original_error = original_error
        self.stage_message = message

class DataCollectionStage(PipelineStage):
    """Stage 1: Raw data collection from GitHub using GitHubService."""
    
    def __init__(self, github_service: IGitHubService):
        super().__init__("Stage 1: Data Collection")
        self.github = github_service
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect raw GitHub data using GitHubService."""
        print("Starting GitHub data collection...")
        
        try:
            raw_data = self.github.collect_organization_data()
            
            # Save raw data for debugging/backup
            with open("raw_github_data.json", "w") as f:
                json.dump(raw_data, f, indent=2)
            
            print(f"Collected raw data for {len(raw_data.get('repositories', {}))} repositories")
            context['raw_data'] = raw_data
            
            return context
            
        except Exception as e:
            print(f"Data collection failed: {e}")
            # Try to load from existing file as fallback
            if os.path.exists("raw_github_data.json"):
                print("Attempting to load from existing raw_github_data.json...")
                with open("raw_github_data.json", "r") as f:
                    raw_data = json.load(f)
                context['raw_data'] = raw_data
                print(f"Loaded fallback data for {len(raw_data.get('repositories', {}))} repositories")
                return context
            else:
                raise

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
        
        # Update roles across all guilds
        roles_updated = await self.discord.update_roles(user_mappings, contributions)
        if not roles_updated:
            print("Warning: Role updates failed")
        
        # Update channels across all guilds
        channels_updated = await self.discord.update_channels(repo_metrics)
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
        from core.interfaces import IStorageService, IDiscordService, IGitHubService, IRoleService
        from core.services import FirestoreService, DiscordBotService
        from core.github_service import GitHubService
        from core.role_service import RoleService
        
        # Register services with proper dependency order
        container.register_singleton(IStorageService, FirestoreService)
        container.register_singleton(IRoleService, RoleService)
        container.register_singleton(IDiscordService, DiscordBotService)
        container.register_singleton(IGitHubService, GitHubService)
    
    def add_stage(self, stage: PipelineStage) -> 'PipelineOrchestrator':
        """Add a pipeline stage."""
        self.stages.append(stage)
        return self
    
    def _setup_default_stages(self):
        """Setup default pipeline stages with dependency injection."""
        storage_service = container.resolve(IStorageService)
        discord_service = container.resolve(IDiscordService) 
        github_service = container.resolve(IGitHubService)
        
        self.stages = [
            DataCollectionStage(github_service),
            DataProcessingStage(),
            DataStorageStage(storage_service),
            DiscordUpdateStage(discord_service, storage_service)
        ]
    
    async def execute_full_pipeline(self) -> Dict[str, Any]:
        """Execute the complete pipeline with comprehensive error handling and recovery."""
        print("="*60)
        print("Starting Discord Bot Data Pipeline")
        print("="*60)
        
        context = {}
        completed_stages = []
        
        try:
            # Setup default pipeline stages if none provided
            if not self.stages:
                self._setup_default_stages()
            
            print(f"Pipeline has {len(self.stages)} stages to execute")
            
            # Execute stages sequentially with error recovery
            for i, stage in enumerate(self.stages):
                try:
                    print(f"Executing stage {i+1}/{len(self.stages)}: {stage.name}")
                    context = await stage.execute(context)
                    completed_stages.append(stage.name)
                    
                    # Provide progress updates
                    progress = ((i + 1) / len(self.stages)) * 100
                    print(f"Pipeline progress: {progress:.1f}% ({i+1}/{len(self.stages)} stages completed)")
                    
                except PipelineStageError as stage_error:
                    print(f"Stage '{stage.name}' failed, attempting recovery...")
                    
                    # Try to recover based on stage type
                    recovery_successful = await self._attempt_stage_recovery(stage, stage_error, context)
                    
                    if recovery_successful:
                        completed_stages.append(f"{stage.name} (recovered)")
                        print(f"✓ Recovery successful for stage: {stage.name}")
                    else:
                        print(f"✗ Recovery failed for stage: {stage.name}")
                        # Continue with remaining stages if possible
                        if self._is_stage_critical(stage):
                            print(f"Stage '{stage.name}' is critical, stopping pipeline")
                            raise
                        else:
                            print(f"Stage '{stage.name}' is non-critical, continuing pipeline")
                            completed_stages.append(f"{stage.name} (failed, skipped)")
            
            # Pipeline completion summary
            print("="*60)
            print("Pipeline completed")
            print(f"Completed stages: {len(completed_stages)}")
            for stage_name in completed_stages:
                print(f"  ✓ {stage_name}")
            print("="*60)
            
            return context
            
        except Exception as e:
            print("="*60)
            print("Pipeline failed with unrecoverable error")
            print(f"Error: {type(e).__name__}: {str(e)}")
            print(f"Completed stages before failure: {len(completed_stages)}")
            for stage_name in completed_stages:
                print(f"  ✓ {stage_name}")
            print("="*60)
            
            # Include diagnostic information
            context['_pipeline_error'] = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'completed_stages': completed_stages,
                'total_stages': len(self.stages)
            }
            
            raise PipelineExecutionError("Pipeline execution failed", e, completed_stages) from e
    
    async def _attempt_stage_recovery(self, stage: PipelineStage, error: PipelineStageError, context: Dict[str, Any]) -> bool:
        """Attempt to recover from stage failure."""
        print(f"Attempting recovery for stage: {stage.name}")
        
        # Recovery strategies based on stage type
        if isinstance(stage, DataCollectionStage):
            return await self._recover_data_collection(error, context)
        elif isinstance(stage, DataProcessingStage):
            return await self._recover_data_processing(error, context)
        elif isinstance(stage, DataStorageStage):
            return await self._recover_data_storage(error, context)
        elif isinstance(stage, DiscordUpdateStage):
            return await self._recover_discord_updates(error, context)
        
        return False
    
    async def _recover_data_collection(self, error: PipelineStageError, context: Dict[str, Any]) -> bool:
        """Recover from data collection failures."""
        print("Attempting data collection recovery...")
        
        # Try to load from existing backup file
        backup_file = "raw_github_data.json"
        if os.path.exists(backup_file):
            try:
                with open(backup_file, "r") as f:
                    raw_data = json.load(f)
                
                # Check if data is recent (within last 24 hours)
                from datetime import datetime, timedelta
                collection_time = raw_data.get('collection_timestamp', '')
                if collection_time:
                    data_time = datetime.fromisoformat(collection_time.replace('Z', '+00:00'))
                    if datetime.now(data_time.tzinfo) - data_time < timedelta(hours=24):
                        print("✓ Using recent backup data for recovery")
                        context['raw_data'] = raw_data
                        return True
                    else:
                        print("Backup data is too old (>24 hours)")
                else:
                    print("✓ Using backup data (no timestamp available)")
                    context['raw_data'] = raw_data
                    return True
                        
            except Exception as e:
                print(f"Failed to load backup data: {e}")
        
        return False
    
    async def _recover_data_processing(self, error: PipelineStageError, context: Dict[str, Any]) -> bool:
        """Recover from data processing failures."""
        print("Attempting data processing recovery...")
        
        # Try with minimal processing if full processing fails
        raw_data = context.get('raw_data')
        if raw_data:
            try:
                # Create minimal contribution data
                repositories = raw_data.get('repositories', {})
                minimal_contributions = {}
                
                for repo_name, repo_data in repositories.items():
                    contributors = repo_data.get('contributors', [])
                    for contributor in contributors:
                        username = contributor.get('login')
                        if username:
                            if username not in minimal_contributions:
                                minimal_contributions[username] = {
                                    'pr_count': 0,
                                    'issues_count': 0, 
                                    'commits_count': contributor.get('contributions', 0)
                                }
                            else:
                                minimal_contributions[username]['commits_count'] += contributor.get('contributions', 0)
                
                context.update({
                    'contributions': minimal_contributions,
                    'hall_of_fame': {'last_updated': datetime.now().isoformat()},
                    'analytics_data': {},
                    'repo_metrics': {'total_contributors': len(minimal_contributions)}
                })
                
                print("✓ Created minimal processed data for recovery")
                return True
                
            except Exception as e:
                print(f"Minimal processing also failed: {e}")
        
        return False
    
    async def _recover_data_storage(self, error: PipelineStageError, context: Dict[str, Any]) -> bool:
        """Recover from data storage failures."""
        print("Attempting data storage recovery...")
        
        # Storage failures are often non-critical - log the data locally
        try:
            backup_data = {
                'contributions': context.get('contributions', {}),
                'repo_metrics': context.get('repo_metrics', {}),
                'hall_of_fame': context.get('hall_of_fame', {}),
                'analytics_data': context.get('analytics_data', {}),
                'backup_timestamp': datetime.now().isoformat()
            }
            
            with open("pipeline_data_backup.json", "w") as f:
                json.dump(backup_data, f, indent=2)
            
            print("✓ Saved processed data to local backup file")
            return True
            
        except Exception as e:
            print(f"Local backup also failed: {e}")
        
        return False
    
    async def _recover_discord_updates(self, error: PipelineStageError, context: Dict[str, Any]) -> bool:
        """Recover from Discord update failures.""" 
        print("Attempting Discord update recovery...")
        
        # Discord updates are often non-critical - just log the attempt
        print("Discord updates failed but pipeline can continue")
        context['discord_update_failed'] = True
        return True
    
    def _is_stage_critical(self, stage: PipelineStage) -> bool:
        """Determine if a stage is critical for pipeline execution."""
        # Data collection is critical, others can often be recovered from
        return isinstance(stage, DataCollectionStage)

class PipelineExecutionError(Exception):
    """Exception raised when pipeline execution fails."""
    
    def __init__(self, message: str, original_error: Exception, completed_stages: List[str]):
        super().__init__(message)
        self.original_error = original_error
        self.completed_stages = completed_stages
        self.pipeline_message = message

# Factory function for easy usage
def create_pipeline_orchestrator() -> PipelineOrchestrator:
    """Create a configured pipeline orchestrator."""
    return PipelineOrchestrator()

# Entry point for GitHub Actions and external scripts
async def run_full_pipeline() -> Dict[str, Any]:
    """Run the complete data pipeline - entry point for GitHub Actions."""
    orchestrator = create_pipeline_orchestrator()
    return await orchestrator.execute_full_pipeline() 