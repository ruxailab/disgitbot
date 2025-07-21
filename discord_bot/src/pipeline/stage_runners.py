"""
Individual Pipeline Stage Runners

Entry points for running individual pipeline stages from GitHub Actions.
Each stage runs independently and passes context via JSON files.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Ensure src is in path for imports
src_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(src_path))

from pipeline.orchestrator import collect_data, process_data, store_data, update_discord

CONTEXT_FILE = "pipeline_context.json"

def save_context(context: Dict[str, Any]) -> None:
    """Save pipeline context to JSON file."""
    try:
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(context, f, indent=2)
    except Exception as e:
        print(f"Failed to save context: {e}")

def load_context() -> Dict[str, Any]:
    """Load pipeline context from JSON file."""
    if not os.path.exists(CONTEXT_FILE):
        print(f"No context file found at {CONTEXT_FILE}", flush=True)
        return {}
    
    try:
        with open(CONTEXT_FILE, 'r') as f:
            context = json.load(f)
        print(f"✓ Context loaded from {CONTEXT_FILE}", flush=True)
        return context
    except Exception as e:
        print(f"Failed to load context: {e}", flush=True)
        return {}

async def run_data_collection_stage():
    """Run Stage 1: Data Collection"""
    print("="*60)
    print("STAGE 1: DATA COLLECTION")
    print("="*60)
    
    try:
        context = await collect_data()
        save_context(context)
        
        print("✓ Data collection stage completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Data collection stage failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_data_processing_stage():
    """Run Stage 2: Data Processing"""
    print("="*60)
    print("STAGE 2: DATA PROCESSING")
    print("="*60)
    
    try:
        context = load_context()
        result = await process_data(context)
        save_context(result)
        
        print("✓ Data processing stage completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Data processing stage failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_data_storage_stage():
    """Run Stage 3: Data Storage"""
    print("="*60)
    print("STAGE 3: DATA STORAGE")
    print("="*60)
    
    try:
        context = load_context()
        result = await store_data(context)
        save_context(result)
        
        print("✓ Data storage stage completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Data storage stage failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_discord_update_stage():
    """Run Stage 4: Discord Updates"""
    print("="*60, flush=True)
    print("STAGE 4: DISCORD UPDATES", flush=True)
    print("="*60, flush=True)
    
    try:
        print("Loading pipeline context...", flush=True)
        context = load_context()
        print("Calling Discord update function...", flush=True)
        result = await update_discord(context)
        print("Saving updated context...", flush=True)
        save_context(result)
        
        print("✓ Discord updates stage completed successfully", flush=True)
        return True
        
    except Exception as e:
        print(f"✗ Discord updates stage failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

# Command-line interface for individual stages
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python stage_runners.py <stage>")
        print("Stages: collection, processing, storage, discord")
        sys.exit(1)
    
    stage_name = sys.argv[1].lower()
    
    stage_functions = {
        'collection': run_data_collection_stage,
        'processing': run_data_processing_stage, 
        'storage': run_data_storage_stage,
        'discord': run_discord_update_stage
    }
    
    if stage_name not in stage_functions:
        print(f"Invalid stage: {stage_name}")
        print("Valid stages: collection, processing, storage, discord")
        sys.exit(1)
    
    success = asyncio.run(stage_functions[stage_name]())
    sys.exit(0 if success else 1) 