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


def validate_and_enhance_quality(result: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Post-processing validator to enforce domain-agnostic quality rules.
    
    Returns:
        (enhanced_result, repair_prompts): Enhanced JSON and list of repair prompts if needed
    """
    # Vague example patterns to detect
    VAGUE_EXAMPLE_PATTERNS = [
        r'consider\s+a\s+simple\s+case',
        r'imagine\s+a\s+scenario',
        r'suppose\s+we\s+have',
        r'let\'?s\s+say',
        r'for\s+example\s*:?\s*$',  # "For example:" with nothing after
        r'e\.?g\.?,?\s*$',  # "e.g." or "e.g.," with nothing after
    ]
    
    # Control flow keywords for algorithm detection
    CONTROL_FLOW_KEYWORDS = ['if', 'for', 'while', 'return', 'else', 'loop', 'repeat']
    
    # Hype number patterns to detect
    HYPE_PATTERNS = [
        r'\d+\^\d+\s+to\s+\d+',  # e.g., "35^100 to 5"
        r'from\s+\d+\^\d+',  # e.g., "from 35^100"
        r'exponential.*manageable',
        r'astronomical.*practical',
    ]
    
    repair_prompts = []
    
    if "summary" not in result:
        return result, repair_prompts
    
    summary = result["summary"]
    sections = summary.get("sections", [])
    
    # 1. Validate examples (reject vague ones)
    vague_examples = []
    for i, section in enumerate(sections):
        for j, concept in enumerate(section.get("concepts", [])):
            example = concept.get("example", "")
            if example:
                # Check if example is vague
                is_vague = any(re.search(pattern, example.lower()) for pattern in VAGUE_EXAMPLE_PATTERNS)
                # Check if example is too short (likely incomplete)
                is_too_short = len(example.split()) < 10
                
                if is_vague or is_too_short:
                    vague_examples.append(f"Section '{section.get('heading', i+1)}', Concept '{concept.get('term', j+1)}'")
    
    if vague_examples:
        repair_prompts.append(
            f"The following concepts have vague or incomplete examples:\n" +
            "\n".join(f"- {ex}" for ex in vague_examples) +
            "\n\nFor EACH listed concept, append a concrete, step-wise worked example:\n" +
            "- If STEM/Economics/CS: include numeric values with calculations\n" +
            "- If Law/Literature: provide realistic scenario with clear steps\n" +
            "Do NOT rewrite existing content. ONLY add the concrete examples."
        )
    
    # 2. Check algorithms for pseudo-code
    missing_pseudocode = []
    for i, section in enumerate(sections):
        heading_lower = section.get("heading", "").lower()
        # Check if this is likely an algorithm section
        is_algorithm = any(word in heading_lower for word in ['algorithm', 'search', 'sort', 'tree', 'graph', 'dynamic'])
        
        if is_algorithm:
            for j, concept in enumerate(section.get("concepts", [])):
                explanation = concept.get("explanation", "")
                # Check if pseudo-code is present
                has_control_flow = any(keyword in explanation.lower() for keyword in CONTROL_FLOW_KEYWORDS)
                has_code_structure = any(char in explanation for char in ['{', '}', '←', '→'])
                
                if not (has_control_flow or has_code_structure):
                    missing_pseudocode.append(f"Section '{section.get('heading', i+1)}', Concept '{concept.get('term', j+1)}'")
    
    if missing_pseudocode:
        repair_prompts.append(
            f"The following algorithm concepts lack pseudo-code:\n" +
            "\n".join(f"- {alg}" for alg in missing_pseudocode) +
            "\n\nFor EACH listed algorithm, append a 6-8 line pseudo-code block in plain text.\n" +
            "Include control flow (if/for/while/return) and state time/space complexity.\n" +
            "Do NOT rewrite existing content. ONLY add the pseudo-code."
        )
    
    # 3. Validate formulas
    formula_issues = []
    formulas = summary.get("formula_sheet", [])
    for i, formula in enumerate(formulas):
        expression = formula.get("expression", "")
        worked_example = formula.get("worked_example", "")
        
        # Check if expression is actually control flow (should be in worked_example instead)
        has_control_in_expr = any(keyword in expression.lower() for keyword in CONTROL_FLOW_KEYWORDS)
        if has_control_in_expr and len(expression) > 100:  # Long control flow text
            formula_issues.append(f"Formula '{formula.get('name', i+1)}' has control flow in expression (move to worked_example)")
        
        # Check if worked example is missing or vague
        if not worked_example or len(worked_example.split()) < 10:
            formula_issues.append(f"Formula '{formula.get('name', i+1)}' lacks concrete worked example")
    
    if formula_issues:
        repair_prompts.append(
            f"Formula sheet issues:\n" +
            "\n".join(f"- {issue}" for issue in formula_issues) +
            "\n\nFix by:\n" +
            "1. Moving control flow from 'expression' to 'worked_example' or 'notes'\n" +
            "2. Adding concrete worked examples with actual numbers and step-by-step calculations\n" +
            "Do NOT rewrite existing content. ONLY fix the listed issues."
        )
    
    # 4. Enhance citations (add headings if missing)
    citations = result.get("citations", [])
    enhanced_citations = []
    for citation in citations:
        if "section" not in citation or not citation.get("section"):
            # Try to extract heading from evidence
            evidence = citation.get("evidence", "")
            # Best-effort: use first sentence or truncate
            heading = evidence.split('.')[0][:50] if evidence else "Source"
            citation["section"] = heading
        
        # Truncate evidence to ≤30 words if too long
        evidence = citation.get("evidence", "")
        words = evidence.split()
        if len(words) > 30:
            citation["evidence"] = ' '.join(words[:30]) + "..."
        
        enhanced_citations.append(citation)
    
    result["citations"] = enhanced_citations
    
    # 5. Remove hype numbers from explanations
    for section in sections:
        for concept in section.get("concepts", []):
            explanation = concept.get("explanation", "")
            for pattern in HYPE_PATTERNS:
                if re.search(pattern, explanation, re.IGNORECASE):
                    # Replace with generic "asymptotically better" or similar
                    explanation = re.sub(pattern, "asymptotically better", explanation, flags=re.IGNORECASE)
                    concept["explanation"] = explanation
    
    # 6. Check glossary size
    glossary = summary.get("glossary", [])
    if len(glossary) < 12:
        repair_prompts.append(
            f"Glossary has only {len(glossary)} terms (target: 12-15).\n" +
            f"Add {12 - len(glossary)} more key technical terms with single-sentence definitions.\n" +
            "Do NOT rewrite existing content. ONLY add the missing glossary terms."
        )
    
    return result, repair_prompts


def has_concrete_example(example: str) -> bool:
    """Check if an example is concrete (has numbers or specific details)"""
    if not example or len(example.split()) < 10:
        return False
    
    # Check for vague patterns
    is_vague = any(re.search(pattern, example.lower()) for pattern in VAGUE_EXAMPLE_PATTERNS)
    if is_vague:
        return False
    
    # Check for concrete indicators (numbers, specific terms, steps)
    has_numbers = bool(re.search(r'\d+', example))
    has_steps = any(word in example.lower() for word in ['step', 'first', 'then', 'finally', 'given', 'result'])
    
    return has_numbers or has_steps
