"""
Telemetry models for quality tracking and user feedback
"""
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Text
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
    
    # Quality metrics
    quality_score = Column(Float)  # 0.0-1.0
    num_concepts = Column(Integer)
    num_formulas = Column(Integer)
    num_exam_questions = Column(Integer)
    num_glossary_terms = Column(Integer)
    
    # Generation details
    self_repair_triggered = Column(Integer, default=0)  # 0=no, 1=yes
    self_repair_improvement = Column(Float, nullable=True)  # Score delta
    total_tokens_used = Column(Integer)
    generation_time_seconds = Column(Float)
    
    # Warnings/issues
    warnings = Column(JSON)  # List of warning strings
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    """Track user feedback on summaries"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    request_hash = Column(String, index=True)
    
    # Feedback type
    feedback_type = Column(String)  # 'rating', 'report_issue', 'suggestion'
    
    # Rating (1-5 stars)
    rating = Column(Integer, nullable=True)
    
    # Specific feedback
    issue_category = Column(String, nullable=True)  # 'shallow', 'incorrect', 'incomplete', 'formatting'
    comment = Column(Text, nullable=True)
    
    # Context
    viewed_sections = Column(JSON)  # Which sections user viewed before feedback
    time_on_page_seconds = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelPerformance(Base):
    """Aggregate model performance metrics over time"""
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    
    # Aggregates for the day
    total_summaries = Column(Integer)
    avg_quality_score = Column(Float)
    avg_user_rating = Column(Float, nullable=True)
    self_repair_rate = Column(Float)  # % of summaries that triggered repair
    
    # By domain
    domain_breakdown = Column(JSON)  # {"technical": {"count": X, "avg_score": Y}, ...}
    
    # Common issues
    top_warnings = Column(JSON)  # [{"warning": "...", "count": X}, ...]
    top_user_issues = Column(JSON)  # [{"issue": "...", "count": X}, ...]
    
    created_at = Column(DateTime, default=datetime.utcnow)
