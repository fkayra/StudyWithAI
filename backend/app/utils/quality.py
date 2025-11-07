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
    
    # 5) Removed: exam_practice no longer part of schema
    
    # 6) Ensure learning objectives exist
    summary.setdefault("learning_objectives", [])
    
    return result


def validate_summary_completeness(result: Dict[str, Any]) -> Tuple[List[str], bool]:
    """
    Validate summary completeness and return (warnings, needs_repair)
    Focus on depth of explanations, NOT practice questions
    
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
    
    # Check section quality (DEPTH focus)
    total_concepts = 0
    shallow_explanations = 0
    concepts_without_examples = 0
    
    for i, section in enumerate(sections):
        if not section.get("heading"):
            warnings.append(f"Section {i+1} missing heading")
        
        concepts = section.get("concepts", [])
        total_concepts += len(concepts)
        
        if not concepts:
            warnings.append(f"Section '{section.get('heading', i+1)}' has no concepts")
        
        for j, concept in enumerate(concepts):
            if not concept.get("term"):
                warnings.append(f"Section {i+1}, Concept {j+1} missing term")
            
            # Check DEPTH: explanation should be substantial
            explanation = concept.get("explanation", "")
            if len(explanation) < 200:  # ~50 words minimum
                shallow_explanations += 1
                warnings.append(f"Concept '{concept.get('term', j+1)}' has shallow explanation ({len(explanation)} chars)")
            
            # Check for multiple examples
            examples = concept.get("examples", [])
            if isinstance(examples, list):
                if len(examples) < 2:
                    concepts_without_examples += 1
                    warnings.append(f"Concept '{concept.get('term', j+1)}' has <2 examples (need 2-3)")
            elif not concept.get("example"):
                concepts_without_examples += 1
                warnings.append(f"Concept '{concept.get('term', j+1)}' missing examples")
    
    if total_concepts < 5:
        critical_issues.append(f"Only {total_concepts} total concepts - expected at least 5")
    
    if shallow_explanations > total_concepts * 0.3:
        critical_issues.append(f"{shallow_explanations} concepts have shallow explanations (need more depth)")
    
    # Check formulas (DEPTH focus)
    formulas = summary.get("formula_sheet", [])
    formulas_without_examples = 0
    formulas_without_derivation = 0
    
    for formula in formulas:
        # Check for worked examples (multiple)
        worked_examples = formula.get("worked_examples", [])
        if isinstance(worked_examples, list):
            if len(worked_examples) < 2:
                formulas_without_examples += 1
                warnings.append(f"Formula '{formula.get('name', '?')}' has <2 worked examples")
        elif not formula.get("notes", "").lower().count("example"):
            formulas_without_examples += 1
            warnings.append(f"Formula '{formula.get('name', '?')}' missing worked examples")
        
        # Check for derivation
        if not formula.get("derivation_steps") and not formula.get("notes", "").lower().count("deriv"):
            formulas_without_derivation += 1
            warnings.append(f"Formula '{formula.get('name', '?')}' missing derivation")
    
    # Check glossary
    glossary_count = len(summary.get("glossary", []))
    if glossary_count < 10:
        critical_issues.append(f"Only {glossary_count} glossary terms - need ≥10")
    
    # Decide if self-repair needed
    needs_repair = len(critical_issues) > 0
    
    all_warnings = warnings + critical_issues
    return (all_warnings, needs_repair)


def create_self_repair_prompt(result: Dict[str, Any], warnings: List[str], language: str = "en") -> str:
    """
    Create a focused prompt for self-repair of incomplete summary
    Focus on DEPTH, not practice questions
    """
    lang_instr = "Write in TURKISH." if language == "tr" else "Write in ENGLISH."
    
    issues = "\n".join(f"- {w}" for w in warnings)
    
    return f"""Your previous study notes output has quality issues. Fix them by adding DEPTH.

{lang_instr}

ISSUES TO FIX:
{issues}

CURRENT OUTPUT:
{result}

INSTRUCTIONS:
1. Keep ALL existing good content (concepts, formulas, examples that are already complete)
2. Fix ONLY the issues listed above:
   - Add missing learning objectives
   - Expand shallow explanations to 3-4 detailed paragraphs
   - Add multiple worked examples (2-3 per concept) with step-by-step calculations
   - Add formula derivations and multiple worked examples
   - Expand glossary to at least 10 substantive terms
3. DO NOT add practice questions (MCQ, short-answer, problem-solving)
4. USE token budget for DEPTH: longer explanations, more examples, derivations
5. Every addition must be specific and derived from the source material

Output the COMPLETE improved study notes as valid JSON (NO exam_practice field).
"""
