"""
Configuration for StudyWithAI - Plan Limits and Constants
"""
from dataclasses import dataclass
from typing import Set

@dataclass
class PlanLimits:
    """Resource limits for different subscription plans"""
    max_files_total: int
    max_pdfs: int
    max_total_mb: int
    max_pages_total: int
    max_input_tokens: int
    max_output_cap: int  # adaptive ceiling for output tokens
    rate_limit_24h: int  # requests per 24 hours

# Plan-based limits
PLAN_LIMITS = {
    "free": PlanLimits(
        max_files_total=3,
        max_pdfs=2,
        max_total_mb=20,
        max_pages_total=80,
        max_input_tokens=12000,
        max_output_cap=16000,  # Increased for deeper explanations
        rate_limit_24h=10
    ),
    "standard": PlanLimits(
        max_files_total=5,
        max_pdfs=3,
        max_total_mb=50,
        max_pages_total=200,
        max_input_tokens=40000,
        max_output_cap=20000,  # Increased for deeper explanations
        rate_limit_24h=50
    ),
    "premium": PlanLimits(  # also handle "pro" alias
        max_files_total=8,
        max_pdfs=5,
        max_total_mb=100,
        max_pages_total=350,
        max_input_tokens=80000,
        max_output_cap=24000,  # Increased for maximum depth
        rate_limit_24h=200
    ),
}

# Alias pro -> premium
PLAN_LIMITS["pro"] = PLAN_LIMITS["premium"]

# File type restrictions
ALLOWED_EXTS: Set[str] = {".pdf", ".pptx", ".docx", ".txt", ".md"}

# Image restrictions (for future use)
MAX_IMAGE_COUNT = 10
MAX_IMAGE_MB = 5

# Token estimation (approximate: 4 characters ≈ 1 token)
TOKEN_PER_CHAR = 0.25

# Chunking configuration for map-reduce
CHUNK_INPUT_TARGET = 3500  # target tokens per chunk for map phase

# Adaptive chunk output budget based on content density
CHUNK_OUTPUT_BASE = 800  # Increased from 400 for deeper chunk summaries
CHUNK_OUTPUT_FORMULA_BOOST = 300  # Increased from 150 for complete derivations
CHUNK_OUTPUT_THEOREM_BOOST = 400  # Increased from 200 for full proofs

MERGE_OUTPUT_BUDGET = (5000, 24000)  # Increased from (3000, 12000) for comprehensive output

# OpenAI configuration
OPENAI_MODEL = "gpt-4o"  # Best quality model (was gpt-4o-mini)
TEMPERATURE = 0.0
TOP_P = 1.0

# Ensure we request enough tokens to complete JSON
# gpt-4o-mini can output up to 16k tokens
MAX_OUTPUT_TOKENS_ABSOLUTE = 16000

# Cache TTL (in seconds)
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

# Density Boost mode thresholds (flexible scaling)
DENSITY_BOOST_THRESHOLD = 15000  # Soft threshold: enable density boost compression
AGGRESSIVE_DENSITY_THRESHOLD = 40000  # Aggressive threshold: max compression + de-duplication
