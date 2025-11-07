"""
Telemetry service for tracking quality metrics
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.telemetry import SummaryQuality
from datetime import datetime


def record_summary_quality(
    db: Session,
    request_hash: str,
    user_id: Optional[int],
    plan: str,
    domain: str,
    language: str,
    input_tokens: int,
    num_chunks: int,
    quality_score: float,
    num_concepts: int,
    num_formulas: int,
    num_exam_questions: int,
    num_glossary_terms: int,
    self_repair_triggered: bool,
    self_repair_improvement: Optional[float],
    total_tokens_used: int,
    generation_time_seconds: float,
    warnings: List[str]
):
    """Record quality metrics for a generated summary"""
    try:
        quality_record = SummaryQuality(
            user_id=user_id,
            request_hash=request_hash,
            plan=plan,
            domain=domain,
            language=language,
            input_tokens=input_tokens,
            num_chunks=num_chunks,
            quality_score=quality_score,
            num_concepts=num_concepts,
            num_formulas=num_formulas,
            num_exam_questions=num_exam_questions,
            num_glossary_terms=num_glossary_terms,
            self_repair_triggered=1 if self_repair_triggered else 0,
            self_repair_improvement=self_repair_improvement,
            total_tokens_used=total_tokens_used,
            generation_time_seconds=generation_time_seconds,
            warnings=warnings
        )
        
        db.add(quality_record)
        db.commit()
        
        print(f"[TELEMETRY] Recorded quality: score={quality_score:.2f}, concepts={num_concepts}, formulas={num_formulas}")
        
    except Exception as e:
        print(f"[TELEMETRY ERROR] Failed to record quality: {e}")
        db.rollback()


def get_quality_stats(db: Session, days: int = 7) -> Dict:
    """Get quality statistics for recent summaries"""
    from sqlalchemy import func
    from datetime import timedelta
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stats = db.query(
            func.count(SummaryQuality.id).label('total'),
            func.avg(SummaryQuality.quality_score).label('avg_score'),
            func.avg(SummaryQuality.num_concepts).label('avg_concepts'),
            func.avg(SummaryQuality.num_formulas).label('avg_formulas'),
            func.sum(SummaryQuality.self_repair_triggered).label('repair_count')
        ).filter(
            SummaryQuality.created_at >= cutoff_date
        ).first()
        
        # By domain breakdown
        domain_stats = db.query(
            SummaryQuality.domain,
            func.count(SummaryQuality.id).label('count'),
            func.avg(SummaryQuality.quality_score).label('avg_score')
        ).filter(
            SummaryQuality.created_at >= cutoff_date
        ).group_by(SummaryQuality.domain).all()
        
        return {
            "period_days": days,
            "total_summaries": stats.total if stats else 0,
            "avg_quality_score": round(float(stats.avg_score), 2) if stats and stats.avg_score else 0.0,
            "avg_concepts": round(float(stats.avg_concepts), 1) if stats and stats.avg_concepts else 0.0,
            "avg_formulas": round(float(stats.avg_formulas), 1) if stats and stats.avg_formulas else 0.0,
            "self_repair_rate": round(float(stats.repair_count) / stats.total * 100, 1) if stats and stats.total > 0 else 0.0,
            "by_domain": {
                row.domain: {
                    "count": row.count,
                    "avg_score": round(float(row.avg_score), 2)
                }
                for row in domain_stats
            }
        }
    
    except Exception as e:
        print(f"[TELEMETRY ERROR] Failed to get stats: {e}")
        return {"error": str(e)}


def get_low_quality_patterns(db: Session, threshold: float = 0.6, limit: int = 10) -> List[Dict]:
    """Identify patterns in low-quality summaries for improvement"""
    try:
        low_quality = db.query(SummaryQuality).filter(
            SummaryQuality.quality_score < threshold
        ).order_by(SummaryQuality.created_at.desc()).limit(limit).all()
        
        patterns = []
        for record in low_quality:
            patterns.append({
                "request_hash": record.request_hash,
                "domain": record.domain,
                "quality_score": record.quality_score,
                "num_concepts": record.num_concepts,
                "num_formulas": record.num_formulas,
                "warnings": record.warnings,
                "self_repair_triggered": bool(record.self_repair_triggered),
                "created_at": record.created_at.isoformat()
            })
        
        return patterns
    
    except Exception as e:
        print(f"[TELEMETRY ERROR] Failed to get low quality patterns: {e}")
        return []
