"""
Pipeline Functions

Simple, direct functions for the Discord bot data pipeline.
No unnecessary class wrappers.
"""

import json
import os
from typing import Dict, Any

from core.services import FirestoreService, DiscordBotService
from core.github_service import GitHubService  
from core.role_service import RoleService
from pipeline.processors import ContributionProcessor, AnalyticsProcessor, MetricsProcessor

async def collect_data() -> Dict[str, Any]:
    """Stage 1: Raw data collection from GitHub."""
    print("========== Stage 1: Data Collection ==========")
    
    try:
        github_service = GitHubService()
        raw_data = github_service.collect_organization_data()
        
        # Save raw data for debugging/backup
        with open("raw_github_data.json", "w") as f:
            json.dump(raw_data, f, indent=2)
        
        print(f"Collected raw data for {len(raw_data.get('repositories', {}))} repositories")
        print("Stage 1: Data Collection - COMPLETED")
        
        return {'raw_data': raw_data}
        
    except Exception as e:
        print(f"Stage 1: Data Collection - FAILED: {e}")
        # Try to load from existing file as fallback
        if os.path.exists("raw_github_data.json"):
            print("Attempting to load from existing raw_github_data.json...")
            with open("raw_github_data.json", "r") as f:
                raw_data = json.load(f)
            print(f"Loaded fallback data for {len(raw_data.get('repositories', {}))} repositories")
            return {'raw_data': raw_data}
        else:
            raise

async def process_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 2: Data processing using specific processors."""
    print("========== Stage 2: Data Processing ==========")
    
    raw_data = context.get('raw_data')
    if not raw_data:
        raise ValueError("No raw data found in context")
    
    # Process contributions
    contribution_processor = ContributionProcessor()
    contributions = contribution_processor.process_raw_data(raw_data)
    contributions = contribution_processor.calculate_rankings(contributions)
    contributions = contribution_processor.calculate_streaks_and_averages(contributions)
    
    # Generate analytics
    analytics_processor = AnalyticsProcessor()
    hall_of_fame = analytics_processor.create_hall_of_fame_data(contributions)
    analytics_data = analytics_processor.create_analytics_data(contributions)
    
    # Calculate metrics
    metrics_processor = MetricsProcessor()
    repo_metrics = metrics_processor.create_repo_metrics(raw_data, contributions)
    
    context.update({
        'contributions': contributions,
        'hall_of_fame': hall_of_fame,
        'analytics_data': analytics_data,
        'repo_metrics': repo_metrics
    })
    
    print(f"Processed data for {len(contributions)} contributors")
    print("Stage 2: Data Processing - COMPLETED")
    return context

async def store_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 3: Data storage to Firestore."""
    print("========== Stage 3: Data Storage ==========")
    
    storage = FirestoreService()
    contributions = context.get('contributions', {})
    repo_metrics = context.get('repo_metrics', {})
    hall_of_fame = context.get('hall_of_fame', {})
    analytics_data = context.get('analytics_data', {})
    
    # Store repository metrics
    if repo_metrics:
        success = storage.set_document('repo_stats', 'metrics', repo_metrics)
        if not success:
            raise Exception("Failed to store repository metrics")
    
    # Store hall of fame
    if hall_of_fame:
        success = storage.set_document('repo_stats', 'hall_of_fame', hall_of_fame)
        if not success:
            raise Exception("Failed to store hall of fame")
    
    # Store analytics data
    if analytics_data:
        success = storage.set_document('repo_stats', 'analytics', analytics_data)
        if not success:
            raise Exception("Failed to store analytics data")
    
    # Store individual contributions
    stored_count = 0
    user_mappings = storage.query_collection('discord')
    
    for username, user_data in contributions.items():
        # Find Discord user mapping
        discord_id = None
        for uid, data in user_mappings.items():
            if data.get('github_id') == username:
                discord_id = uid
                break
        
        if discord_id:
            success = storage.update_document('discord', discord_id, user_data)
            if success:
                stored_count += 1
    
    print(f"Stored data for {stored_count} users")
    print("Stage 3: Data Storage - COMPLETED")
    return context

async def update_discord(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 4: Discord role and channel updates."""
    print("========== Stage 4: Discord Updates ==========")
    
    # Initialize services with logging
    print("Initializing Discord bot services...")
    storage = FirestoreService()
    role_service = RoleService(storage)
    discord_service = DiscordBotService(role_service)
    
    # Extract data from context with logging
    contributions = context.get('contributions', {})
    repo_metrics = context.get('repo_metrics', {})
    
    print(f"Found {len(contributions)} contributors in context")
    print(f"Repository metrics available: {bool(repo_metrics)}")
    
    # Get user mappings from storage with logging
    print("Querying Discord user mappings from Firestore...")
    user_mappings_data = storage.query_collection('discord')
    user_mappings = {}
    
    for discord_id, data in user_mappings_data.items():
        github_id = data.get('github_id')
        if github_id:
            user_mappings[discord_id] = github_id
    
    print(f"Found {len(user_mappings)} Discord-to-GitHub user mappings")
    
    if not user_mappings:
        print("WARNING: No user mappings found. Discord updates will be limited.")
    
    # Update roles across all guilds with detailed logging
    print("Starting Discord role updates...")
    roles_updated = await discord_service.update_roles(user_mappings, contributions)
    if roles_updated:
        print("✓ Role updates completed successfully")
    else:
        print("✗ Role updates failed")
    
    # Update channels across all guilds with detailed logging
    print("Starting Discord channel updates...")
    channels_updated = await discord_service.update_channels(repo_metrics)
    if channels_updated:
        print("✓ Channel updates completed successfully")
    else:
        print("✗ Channel updates failed")
    
    print("Stage 4: Discord Updates - COMPLETED")
    return context

async def run_full_pipeline() -> Dict[str, Any]:
    """Run the complete data pipeline."""
    print("="*60)
    print("Starting Discord Bot Data Pipeline")
    print("="*60)
    
    try:
        # Stage 1: Data Collection
        context = await collect_data()
        
        # Stage 2: Data Processing  
        context = await process_data(context)
        
        # Stage 3: Data Storage
        context = await store_data(context)
        
        # Stage 4: Discord Updates
        context = await update_discord(context)
        
        print("="*60)
        print("Pipeline completed successfully")
        print("="*60)
        
        return context
        
    except Exception as e:
        print("="*60)
        print("Pipeline failed")
        print(f"Error: {e}")
        print("="*60)
        raise 