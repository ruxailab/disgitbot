#!/usr/bin/env python3
"""
Configuration settings for PR Automation System
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path) 

# GitHub Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

# Repository Configuration
REPO_OWNER = os.getenv('REPO_OWNER', 'ruxailab')
REPO_NAME = os.getenv('REPO_NAME', 'RUXAILAB')

# Vertex AI Configuration
VERTEX_AI_PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')
VERTEX_AI_LOCATION = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# PR Automation Configuration
AUTO_APPLY_LABELS = os.getenv('AUTO_APPLY_LABELS', 'true').lower() == 'true'
AUTO_ASSIGN_REVIEWERS = os.getenv('AUTO_ASSIGN_REVIEWERS', 'true').lower() == 'true'
POST_METRICS_COMMENT = os.getenv('POST_METRICS_COMMENT', 'true').lower() == 'true'

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
LOGS_DIR = BASE_DIR / 'logs'
OUTPUT_DIR = BASE_DIR / 'output'

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Validation
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is required")

if not VERTEX_AI_PROJECT_ID:
    print("⚠️  Warning: VERTEX_AI_PROJECT_ID not set. AI-powered reviews will be disabled.")

if not GOOGLE_API_KEY:
    print("⚠️  Warning: GOOGLE_API_KEY not set. AI-powered reviews will be disabled.")

print(f"✅ Configuration loaded for repository: {REPO_OWNER}/{REPO_NAME}")

# Model configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))

# Application configuration
MAX_PR_HISTORY = int(os.getenv("MAX_PR_HISTORY", 100))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.7))

# GitHub review configuration
REVIEW_COMMENT_TEMPLATE = """
{confidence_prefix} **{suggestion}**

{explanation}

{reference_info}
"""

CONFIDENCE_LEVELS = {
    "high": "🔍",
    "medium": "💭",
    "low": "⚠️"
}

# Developer experience levels for personalized reviews
EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"] 