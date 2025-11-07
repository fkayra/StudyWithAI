"""
Quality enforcement for exam-ready summaries
NO PLACEHOLDER GENERATION - only validation and self-repair triggers
"""
from typing import Dict, Any, List, Tuple


def enforce_exam_ready(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process summary to ensure basic structure exists
    
    IMPORTANT: NO longer adds generic placeholders like "Review this concept"
    Only ensures empty arrays exist for required fields
    """
    if "summary" not in result:
        return result
    
    summary = result["summary"]
    
    # 1) Ensure sections exist
    summary.setdefault("sections", [])
    
    # 2) Ensure each section has proper structure (but don't add fake content)
    for section in summary.get("sections", []):
        section.setdefault("concepts", [])
        
        # Ensure each concept has required fields (but leave them empty if missing)
        for concept in section.get("concepts", []):
            concept.setdefault("term", "")
            concept.setdefault("definition", "")
            concept.setdefault("explanation", "")
            concept.setdefault("key_points", [])
            concept.setdefault("exam_tips", [])
    
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


def validate_summary_completeness(result: Dict[str, Any]) -> Tuple[List[str], bool]:
    """
    Validate summary completeness and return (warnings, needs_repair)
    
    Returns:
        (warnings: List[str], needs_repair: bool)
        - warnings: Human-readable issues
        - needs_repair: True if critical issues exist (should trigger self-repair)
    """
    warnings = []
    critical_issues = []
    
    if "summary" not in result:
        return (["Missing 'summary' key"], True)
    
    summary = result["summary"]
    
    # Check critical fields
    if not summary.get("title"):
        warnings.append("Missing title")
    
    if not summary.get("overview"):
        warnings.append("Missing overview")
    
    if not summary.get("learning_objectives") or len(summary.get("learning_objectives", [])) < 2:
        critical_issues.append("Missing learning objectives (need ≥2)")
    
    sections = summary.get("sections", [])
    if len(sections) < 2:
        critical_issues.append(f"Only {len(sections)} section(s) - expected at least 2")
    
    # Check section quality
    total_concepts = 0
    sections_without_concepts = 0
    
    for i, section in enumerate(sections):
        if not section.get("heading"):
            warnings.append(f"Section {i+1} missing heading")
        
        concepts = section.get("concepts", [])
        total_concepts += len(concepts)
        
        if not concepts:
            sections_without_concepts += 1
            warnings.append(f"Section '{section.get('heading', i+1)}' has no concepts")
        
        for j, concept in enumerate(concepts):
            if not concept.get("term"):
                warnings.append(f"Section {i+1}, Concept {j+1} missing term")
            if not concept.get("explanation") or len(concept.get("explanation", "")) < 50:
                warnings.append(f"Concept '{concept.get('term', j+1)}' has shallow/missing explanation")
            if not concept.get("example"):
                warnings.append(f"Concept '{concept.get('term', j+1)}' missing example")
            if concept.get("exam_tips") == ["Review this concept thoroughly for exams"]:
                # Detect generic placeholder (old system artifact)
                warnings.append(f"Concept '{concept.get('term', j+1)}' has generic exam tip (should be specific)")
    
    if total_concepts < 5:
        critical_issues.append(f"Only {total_concepts} total concepts - expected at least 5")
    
    # Check formulas
    formulas = summary.get("formula_sheet", [])
    formulas_without_examples = 0
    
    for formula in formulas:
        if not formula.get("worked_example") and not formula.get("notes", "").count("example"):
            formulas_without_examples += 1
            warnings.append(f"Formula '{formula.get('name', '?')}' missing worked example")
    
    # Check exam practice
    exam = summary.get("exam_practice", {})
    mcq_count = len(exam.get("multiple_choice", []))
    sa_count = len(exam.get("short_answer", []))
    prob_count = len(exam.get("problem_solving", []))
    
    if mcq_count < 4:
        critical_issues.append(f"Only {mcq_count} MCQ - need ≥4")
    if sa_count < 3:
        critical_issues.append(f"Only {sa_count} short-answer - need ≥3")
    if prob_count < 2:
        critical_issues.append(f"Only {prob_count} problem-solving - need ≥2")
    
    # Check glossary
    glossary_count = len(summary.get("glossary", []))
    if glossary_count < 8:
        critical_issues.append(f"Only {glossary_count} glossary terms - need ≥8")
    
    # Decide if self-repair needed
    needs_repair = len(critical_issues) > 0
    
    all_warnings = warnings + critical_issues
    return (all_warnings, needs_repair)


def create_self_repair_prompt(result: Dict[str, Any], warnings: List[str], language: str = "en") -> str:
    """
    Create a focused prompt for self-repair of incomplete summary
    """
    lang_instr = "Write in TURKISH." if language == "tr" else "Write in ENGLISH."
    
    issues = "\n".join(f"- {w}" for w in warnings)
    
    return f"""Your previous summary output has critical quality issues. Fix them now.

{lang_instr}

ISSUES TO FIX:
{issues}

CURRENT OUTPUT:
{result}

INSTRUCTIONS:
1. Keep ALL existing good content (concepts, formulas, examples that are already complete)
2. Fix ONLY the issues listed above:
   - Add missing learning objectives
   - Expand sections with no concepts
   - Add worked examples to formulas missing them
   - Add MCQ/short-answer/problem-solving questions to reach minimums
   - Expand glossary to at least 8 terms
3. DO NOT add generic content like "Review carefully" or "Important for exams"
4. Every addition must be specific and derived from the source material

Output the COMPLETE corrected summary as valid JSON (same schema as before).
"""
