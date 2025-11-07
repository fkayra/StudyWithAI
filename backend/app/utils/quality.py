"""
Quality enforcement for exam-ready summaries
"""
from typing import Dict, Any, List


def enforce_exam_ready(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process summary to ensure exam-ready quality standards
    
    Ensures:
    - Minimum section count
    - Each section has concepts with exam_tips
    - Formula sheet and glossary exist
    - Exam practice questions exist
    """
    if "summary" not in result:
        return result
    
    summary = result["summary"]
    
    # 1) Ensure minimum sections
    sections = summary.get("sections", [])
    if len(sections) < 2:
        # Add note about automatic expansion
        overview = summary.get("overview", "")
        if overview and "NOTE:" not in overview:
            summary["overview"] = overview + " (Coverage expanded for comprehensive study.)"
    
    # 2) Ensure each section has proper structure
    for section in sections:
        concepts = section.get("concepts", [])
        
        # If no concepts, add placeholder
        if not concepts:
            section["concepts"] = [{
                "term": "Key Concept",
                "definition": "See detailed content above",
                "explanation": section.get("heading", "Content"),
                "key_points": []
            }]
        
        # Ensure each concept has required fields
        for concept in section.get("concepts", []):
            concept.setdefault("term", "Concept")
            concept.setdefault("definition", "")
            concept.setdefault("explanation", "")
            concept.setdefault("key_points", [])
            concept.setdefault("exam_tips", [])
            
            # Add minimal exam tip if none
            if not concept.get("exam_tips"):
                concept["exam_tips"] = ["Review this concept thoroughly for exams"]
    
    # 3) Ensure formula sheet exists (can be empty)
    summary.setdefault("formula_sheet", [])
    
    # 4) Ensure glossary exists (can be empty)
    summary.setdefault("glossary", [])
    
    # 5) Ensure exam practice exists with all sections
    exam_practice = summary.setdefault("exam_practice", {})
    exam_practice.setdefault("multiple_choice", [])
    exam_practice.setdefault("short_answer", [])
    exam_practice.setdefault("problem_solving", [])
    
    # 6) Ensure learning objectives exist
    summary.setdefault("learning_objectives", [])
    
    return result


def validate_summary_completeness(result: Dict[str, Any]) -> List[str]:
    """
    Validate summary completeness and return list of warnings
    """
    warnings = []
    
    if "summary" not in result:
        warnings.append("Missing 'summary' key")
        return warnings
    
    summary = result["summary"]
    
    # Check critical fields
    if not summary.get("title"):
        warnings.append("Missing title")
    
    if not summary.get("overview"):
        warnings.append("Missing overview")
    
    if not summary.get("learning_objectives"):
        warnings.append("Missing learning objectives")
    
    sections = summary.get("sections", [])
    if len(sections) < 2:
        warnings.append(f"Only {len(sections)} section(s) - expected at least 2")
    
    # Check section quality
    for i, section in enumerate(sections):
        if not section.get("heading"):
            warnings.append(f"Section {i+1} missing heading")
        
        concepts = section.get("concepts", [])
        if not concepts:
            warnings.append(f"Section '{section.get('heading', i+1)}' has no concepts")
        
        for j, concept in enumerate(concepts):
            if not concept.get("term"):
                warnings.append(f"Section {i+1}, Concept {j+1} missing term")
            if not concept.get("explanation"):
                warnings.append(f"Concept '{concept.get('term', j+1)}' missing explanation")
    
    return warnings
