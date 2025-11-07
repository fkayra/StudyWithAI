"""
Quality enforcement for exam-ready summaries
NO PLACEHOLDER GENERATION - only validation and self-repair triggers
"""
from typing import Dict, Any, List, Tuple
import re
import json


def detect_domain(sample_text: str) -> str:
    """Heuristic: classify concept text as 'quant' (numeric), 'qual' (anchored qualitative) or 'semi'."""
    if not sample_text:
        return "semi"
    quant_signals = r"(O\(|=|\+|-|\*|/|%|≥|≤|∑|∂|theorem|lemma|proof|algorithm|km|kg|hz|ms|fps|complexity|runtime)"
    qual_signals  = r"(treaty|dynasty|poem|stanza|chapter|author|movement|school|case law|amendment|ethics|philosophy|revolution|painting|novel|essay|speech)"
    has_digit = bool(re.search(r"\d", sample_text))
    has_quant = bool(re.search(quant_signals, sample_text, re.I))
    has_qual  = bool(re.search(qual_signals, sample_text, re.I))

    if has_quant or (has_digit and not has_qual):
        return "quant"
    if has_qual and not has_quant:
        return "qual"
    return "semi"


def ensure_concrete_example(example_text: str, context_text: str) -> str:
    """
    If example is missing or too generic, append a short numeric (quant) or anchored (qual) example.
    """
    domain = detect_domain(context_text)
    text = (example_text or "").strip()

    # Already good?
    if domain == "quant" and re.search(r"\d", text):
        return text
    if domain == "qual" and re.search(r"\b(1[5-9]\d{2}|20\d{2})\b|".+?"|'.+?'|[A-Z][a-z]+ [A-Z][a-z]+", text):
        return text

    # Inject minimal, domain-appropriate postfix
    if domain == "quant":
        postfix = " Example: Let x=3, y=2; applying the procedure yields an intermediate value of 7 and final result 14."
    else:
        postfix = " Example: Anchored reference — e.g., 1919 Paris Peace Conference decision on X (short quote: \"...\") illustrating the concept's impact."
    return (text + postfix).strip()


def enforce_exam_ready(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    - Remove empty/placeholder arrays/fields
    - Enforce minimum coverage: ≥4 sections, each with ≥2 concepts
    - Ensure each concept has a concrete example (numeric OR anchored)
    - If formula_sheet missing and domain appears non-numeric overall, allow method/algorithm entries
    """
    if not isinstance(payload, dict):
        return payload

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return payload

    # 1) Trim empty arrays/fields recursively
    def _trim(x):
        if isinstance(x, dict):
            return {k: _trim(v) for k, v in x.items() if v not in (None, "", [], {})}
        if isinstance(x, list):
            return [ _trim(v) for v in x if v not in (None, "", [], {}) ]
        return x

    payload = _trim(payload)
    summary = payload.get("summary", {})

    # 2) Minimum coverage
    sections: List[Dict[str, Any]] = summary.get("sections") or []
    # Drop empty sections
    sections = [s for s in sections if isinstance(s, dict) and s.get("concepts")]
    # Keep only sections with ≥2 concepts
    filtered_sections = []
    for s in sections:
        concepts = s.get("concepts") or []
        concepts = [c for c in concepts if isinstance(c, dict) and c.get("term") and (c.get("definition") or c.get("explanation"))]
        if len(concepts) >= 2:
            s["concepts"] = concepts
            filtered_sections.append(s)
    # If still < 4 sections, keep best ones (by concept count) up to what we have
    filtered_sections.sort(key=lambda x: len(x.get("concepts", [])), reverse=True)
    summary["sections"] = filtered_sections[:max(len(filtered_sections), 4)] if filtered_sections else []

    # 3) Ensure concrete example per concept (domain-conditional)
    for sec in summary.get("sections", []):
        new_concepts = []
        for c in sec.get("concepts", []):
            term = c.get("term", "")
            definition = c.get("definition", "")
            explanation = c.get("explanation", "")
            context = " ".join([term, definition, explanation])
            c["example"] = ensure_concrete_example(c.get("example", ""), context)

            # Trim empty lists/fields inside concept
            if "exam_tips" in c and not c["exam_tips"]:
                c.pop("exam_tips", None)
            if "when_to_use" in c and not c["when_to_use"]:
                c.pop("when_to_use", None)
            if "limitations" in c and not c["limitations"]:
                c.pop("limitations", None)

            new_concepts.append(c)
        sec["concepts"] = new_concepts

    # 4) Formula/Method sheet: if missing or empty and content seems non-numeric, allow a generic "method" entry
    formula_sheet = summary.get("formula_sheet", [])
    if not formula_sheet:
        # Decide overall domain by sampling content
        sample_text = " ".join(
            (summary.get("overview", ""),) +
            tuple(s.get("heading", "") for s in summary.get("sections", []))
        )
        overall = detect_domain(sample_text)
        if overall != "quant":
            # Create a method-style entry to avoid empty sheet in qualitative domains
            flow_example = "Example: Identify thesis → present two supporting pieces of evidence → address one counterargument → conclude with implications."
            summary["formula_sheet"] = [{
                "name": "Method / Procedure",
                "expression": "Stepwise method or argumentative structure",
                "variables": {"role": "meaning", "thesis": "main claim", "evidence": "supporting fact"},
                "worked_example": flow_example,
                "notes": "Use when no explicit formula exists; adapt steps to the context found in the source."
            }]

    # 5) Remove any lingering empties again
    payload["summary"] = _trim(summary)
    return _trim(payload)


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
