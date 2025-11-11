"""
Telemetry models for quality tracking
"""
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class SummaryQuality(Base):
    """Track quality metrics for each generated summary"""
    __tablename__ = "summary_quality"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # Null for anonymous
    request_hash = Column(String, index=True)  # Same as cache key
    
    # Input characteristics
    plan = Column(String)  # free/standard/pro
    domain = Column(String)  # technical/social/procedural/general
    language = Column(String)
    input_tokens = Column(Integer)
    num_chunks = Column(Integer)
    
    # Quality metrics (legacy + comprehensive)
    quality_score = Column(Float)  # 0.0-1.0 (overall final-ready score)
    num_concepts = Column(Integer)
    num_formulas = Column(Integer)
    num_exam_questions = Column(Integer)
    num_glossary_terms = Column(Integer)
    
    # Comprehensive quality metrics (evrensel, domain-agnostic)
    # TODO: coverage_score needs migration - temporarily commented out
    # coverage_score = Column(Float, nullable=True)  # Theme coverage ratio
    numeric_density = Column(Float, nullable=True)  # % examples with numbers (domain-aware)
    formula_completeness = Column(Float, nullable=True)  # % formulas with variables + examples
    citation_depth = Column(Float, nullable=True)  # % citations with page/section details
    readability_score = Column(Float, nullable=True)  # Sentence density score (18-28 tokens/sentence)
    is_final_ready = Column(Integer, nullable=True)  # 1=yes (≥0.90), 0=no
    
    # Generation details
    self_repair_triggered = Column(Integer, default=0)  # 0=no, 1=yes
    self_repair_improvement = Column(Float, nullable=True)  # Score delta
    total_tokens_used = Column(Integer)
    generation_time_seconds = Column(Float)
    
    # Warnings/issues
    warnings = Column(JSON)  # List of warning strings
    
    created_at = Column(DateTime, default=datetime.utcnow)
