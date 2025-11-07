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
        max_output_cap=1200,
        rate_limit_24h=10
    ),
    "standard": PlanLimits(
        max_files_total=5,
        max_pdfs=3,
        max_total_mb=50,
        max_pages_total=200,
        max_input_tokens=40000,
        max_output_cap=8000,
        rate_limit_24h=50
    ),
    "premium": PlanLimits(  # also handle "pro" alias
        max_files_total=8,
        max_pdfs=5,
        max_total_mb=100,
        max_pages_total=350,
        max_input_tokens=80000,
        max_output_cap=12000,
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
CHUNK_INPUT_TARGET = 2400  # target tokens per chunk for map phase
CHUNK_OUTPUT_BUDGET = (200, 300)  # min, max output tokens per chunk summary
MERGE_OUTPUT_BUDGET = (2000, 4000)  # min, max output tokens for final merge (increased for exam-ready schema)

# OpenAI configuration
OPENAI_MODEL = "gpt-4o-mini"  # or "gpt-4o" for better quality
TEMPERATURE = 0.0
TOP_P = 1.0

# Cache TTL (in seconds)
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
