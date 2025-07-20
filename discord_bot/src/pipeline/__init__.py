"""
Discord Bot Data Pipeline

Clean 4-stage modular pipeline for GitHub data processing and Discord integration.

Pipeline Stages:
1. collect_raw_data.py - Fetch raw GitHub data via API calls
2. process_data.py - Process raw data into structured analytics and metrics
3. store_data.py - Store processed data in Firestore collections
4. update_discord.py - Update Discord roles and channels from Firestore

Data Flow:
Raw GitHub API → Raw JSON → Processed JSON → Firestore → Discord Updates

Each stage has a single responsibility and clean input/output contracts.
"""

__version__ = "2.0.0" 