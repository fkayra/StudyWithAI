"""
Quality enforcement for exam-ready summaries
NO PLACEHOLDER GENERATION - only validation and self-repair triggers
EVRENSEL (universal) quality rules: domain-agnostic, file-independent
"""
from typing import Dict, Any, List, Tuple
import re
import json


# Vague example patterns to detect
VAGUE_EXAMPLE_PATTERNS = [
    r'consider\s+a\s+simple\s+case',
    r'imagine\s+a\s+scenario',
    r'suppose\s+we\s+have',
    r'let\'?s\s+say',
    r'for\s+example\s*:?\s*$',  # "For example:" with nothing after
    r'e\.?g\.?,?\s*$',  # "e.g." or "e.g.," with nothing after
]


def detect_domain(sample_text: str) -> str:
    """Heuristic: classify concept text as 'quant' (numeric), 'qual' (anchored qualitative) or 'semi'.
    
    Returns:
        'quant': Math, physics, CS algorithms, economics, stats, operations research
        'qual': Law, literature, history, philosophy, social sciences
        'semi': Mixed or unclear domain
    """
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
    # Check for qual anchors: dates (1500-2099), quotes, or proper names
    qual_pattern = r'''\b(1[5-9]\d{2}|20\d{2})\b|".+?"|'.+?'|[A-Z][a-z]+ [A-Z][a-z]+'''
    if domain == "qual" and re.search(qual_pattern, text):
        return text

    # Inject minimal, domain-appropriate postfix
    if domain == "quant":
        postfix = " Example: Let x=3, y=2; applying the procedure yields an intermediate value of 7 and final result 14."
    else:
        postfix = " Example: Anchored reference — e.g., 1919 Paris Peace Conference decision on X (short quote: \"...\") illustrating the concept's impact."
    return (text + postfix).strip()


def enforce_exam_ready(payload: Dict[str, Any], detected_themes: List[str] = None) -> Dict[str, Any]:
    """
    Comprehensive post-processing with evrensel quality rules + sanitization pipeline
    1. Sanitize examples (remove generic, trim to 2 sentences)
    2. Ensure numeric example only if relevant to source
    3. Fix formula vs pseudocode mixing
    4. Enforce alpha-beta trace, stochastic formulas
    5. Normalize coverage (remove duplicates)
    6. Coerce formula expressions to math
    7. Validate and enhance citations
    8. Remove filler phrases
    9. Clean empty fields
    
    Does NOT filter sections - validation handled separately
    """
    if not isinstance(payload, dict):
        return payload

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return payload

    # Detect overall domain for the document
    sample_text = str(summary)[:2000]
    overall_domain = detect_domain(sample_text)
    print(f"[ENFORCE] Detected domain: {overall_domain}")

    # Store original source for signal detection (use first section's text as proxy)
    original_source_text = ""
    for sec in summary.get("sections", []):
        for c in sec.get("concepts", [])[:1]:  # First concept
            original_source_text += c.get("definition", "") + " " + c.get("explanation", "")
            break
        if original_source_text:
            break

    # PIPELINE: Process concepts with sanitization + enforcement
    for sec in summary.get("sections", []):
        for c in sec.get("concepts", []):
            # Get current example
            example = c.get("example", "")
            
            # PIPELINE ORDER:
            # 1. Sanitize examples (remove generic, trim to 2 sentences)
            example = sanitize_examples(example)
            
            # 2. Ensure numeric example only if relevant to source
            example = ensure_numeric_example_if_relevant(example, original_source_text)
            
            # 3. Fix formula vs pseudocode mixing
            example = fix_formula_vs_pseudocode(example)
            
            # 4. Enforce alpha-beta trace if applicable
            example = enforce_alpha_beta_trace(example)
            
            # 5. Add stochastic expectation formula if needed
            example = add_stochastic_expectation_formula_if_needed(example)
            
            # 6. Normalize coverage (remove duplicates)
            example = normalize_coverage(example)
            
            c["example"] = example

    # 7) Coerce formula expressions to math (move pseudocode to separate field)
    formulas = summary.get("formula_sheet", [])
    for i, formula in enumerate(formulas):
        formulas[i] = coerce_pseudocode_fields(formula)
    
    # 8) Validate and enhance citations
    if "citations" not in payload:
        payload["citations"] = []
    
    # Enhance citation structure
    for citation in payload["citations"]:
        # Ensure section_or_heading field (rename 'section' if needed)
        if "section" in citation and "section_or_heading" not in citation:
            citation["section_or_heading"] = citation["section"]
        
        # Truncate evidence to max 200 chars
        if "evidence" in citation:
            evidence = citation["evidence"]
            if len(evidence) > 200:
                citation["evidence"] = evidence[:197] + "..."
    
    # 9) Remove filler phrases from text content
    from app.utils.json_helpers import defill
    
    if summary.get("overview"):
        summary["overview"] = defill(summary["overview"])
    
    for sec in summary.get("sections", []):
        for c in sec.get("concepts", []):
            if c.get("explanation"):
                c["explanation"] = defill(c["explanation"])
    
    # 10) Light cleanup - only remove None and empty strings (preserve structure)
    def _clean(x):
        if isinstance(x, dict):
            cleaned = {}
            for k, v in x.items():
                if v is None or v == "":
                    continue  # Skip None and empty strings
                if isinstance(v, list) and len(v) == 0:
                    continue  # Skip empty arrays
                if isinstance(v, dict) and len(v) == 0:
                    continue  # Skip empty dicts
                cleaned[k] = _clean(v)
            return cleaned
        if isinstance(x, list):
            return [_clean(item) for item in x if item is not None and item != "" and item != {} and item != []]
        return x
    
    cleaned = _clean(payload)
    
    # 11) Log quality validation issues (non-blocking)
    citation_issues = validate_citations_depth(cleaned)
    if citation_issues:
        print(f"[QUALITY WARNING] Citation issues: {citation_issues}")
    
    if detected_themes:
        additional_topics_issues = enforce_additional_topics_presence(summary, detected_themes)
        if additional_topics_issues:
            print(f"[QUALITY WARNING] Coverage issues: {additional_topics_issues}")
    
    return cleaned


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


def detect_numeric_signals(text: str) -> list:
    """Detect numeric/quantitative signals in text (Big-O, Sigma, numbers, Greek letters)"""
    pattern = r"(O\(|Θ\(|Σ|∑|\b\d+(?:\.\d+)?\b|\b(alpha|beta|α|β)\b|V\(|P\(|E\[)"
    return re.findall(pattern, text, re.IGNORECASE)


def remove_numeric_fillers(text: str) -> str:
    """Remove generic numeric examples if source has no numeric signals"""
    # Drop patterns like "Example: Let x=3, y=2..."
    patterns = [
        r"Example: Let x=\d+.*?[.!]",
        r"Example calculation:.*?\d+.*?[.!]",
        r"Let x=\d+, y=\d+.*?[.!]",
        r"Step 1: Initial value = \d+.*?[.!]",
        r"Applying the procedure:.*?\d+.*?[.!]"
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text.strip()


def sanitize_examples(text: str) -> str:
    """Trim examples to ≤2 sentences, remove generic fillers"""
    # Find example sections
    example_pattern = r'(Example:|For example:|e\.g\.,)(.*?)(?=\n|$|Example:|For example:)'
    
    def trim_example(match):
        prefix = match.group(1)
        content = match.group(2)
        sentences = re.split(r'[.!?]+', content)
        # Keep only first 2 non-empty sentences
        kept = [s.strip() for s in sentences if s.strip()][:2]
        if kept:
            return prefix + ' ' + '. '.join(kept) + '.'
        return ''
    
    text = re.sub(example_pattern, trim_example, text, flags=re.IGNORECASE)
    return text.strip()


def ensure_numeric_example_if_relevant(text: str, source_text: str) -> str:
    """Add numeric example only if source has numeric signals"""
    signals = detect_numeric_signals(source_text)
    
    if not signals:
        # No numeric signals in source → remove generic numeric fillers
        text = remove_numeric_fillers(text)
    elif not re.search(r'\d', text):
        # Has signals but no numbers in text → keep existing (don't add generic)
        pass
    
    return text


def fix_formula_vs_pseudocode(text: str) -> str:
    """Ensure formulas use math notation, not pseudocode keywords"""
    # If text has control flow keywords, it's likely pseudocode mixed with math
    control_keywords = r'\b(function|return|for each|if|while|loop)\b'
    if re.search(control_keywords, text, re.IGNORECASE):
        # Replace with math-friendly notation
        text = text.replace('function', 'f')
        text = text.replace('Function', 'f')
        text = text.replace('return', '→')
        text = text.replace('Return', '→')
    return text


def enforce_alpha_beta_trace(text: str) -> str:
    """Ensure alpha-beta pruning examples show trace steps"""
    if 'alpha' in text.lower() or 'beta' in text.lower() or 'α' in text or 'β' in text:
        # Check if trace exists
        if not re.search(r'(step|trace|α\s*=|β\s*=)', text, re.IGNORECASE):
            # Add minimal trace hint
            text += " (Trace: α=−∞, β=+∞ initially; update at each node.)"
    return text


def add_stochastic_expectation_formula_if_needed(text: str) -> str:
    """Add expectation formula if stochastic games mentioned but formula missing"""
    if 'stochastic' in text.lower() or 'expectation' in text.lower():
        if not re.search(r'E\[|𝔼\[|expected value', text, re.IGNORECASE):
            text += " Formula: E[V] = Σ P(s') × V(s')"
    return text


def normalize_coverage(text: str) -> str:
    """Ensure text is concise and avoids repetition"""
    # Remove duplicate sentences (simple check)
    sentences = re.split(r'[.!?]+', text)
    seen = set()
    unique = []
    for s in sentences:
        normalized = s.strip().lower()
        if normalized and normalized not in seen and len(normalized) > 5:  # Skip very short
            seen.add(normalized)
            unique.append(s.strip())
    return '. '.join(unique) + '.' if unique else text


def ensure_numeric_example_if_applicable(concept_text: str, example: str, domain: str) -> str:
    """Ensure numeric example for quantitative domains, textual example for qualitative.
    
    Args:
        concept_text: The concept's context (term + definition + explanation)
        example: Current example text
        domain: Domain classification ('quant', 'qual', 'semi')
    
    Returns:
        Enhanced example with numeric or anchored details if needed
    """
    if not example:
        example = ""
    
    # Domain-specific requirements
    if domain == "quant":
        # Quantitative domains NEED numbers
        if not re.search(r'\d', example):
            # Add minimal numeric example
            return (example + " Example calculation: Let x=3, y=2. Applying the procedure: " +
                    "Step 1: Initial value = 3×2 = 6. Step 2: Adjusted result = 6+1 = 7.").strip()
    
    elif domain == "qual":
        # Qualitative domains need anchored references (dates, names, quotes)
        qual_pattern = r'\b(1[5-9]\d{2}|20\d{2})\b|".+?"|\'.+?\'|[A-Z][a-z]+ [A-Z][a-z]+'
        if not re.search(qual_pattern, example):
            # Add anchored example
            return (example + " Historical anchor: Consider the 1919 case where this principle " +
                    "was applied (Treaty context: \"provisions affecting X\"), demonstrating the concept's practical impact.").strip()
    
    # For 'semi' domain or if already has appropriate content, return as-is
    return example


def coerce_pseudocode_fields(formula: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure expression contains math, not pseudocode. Move control flow to pseudocode field.
    
    Args:
        formula: Formula dict with 'expression' field
    
    Returns:
        Corrected formula dict with separated expression and pseudocode
    """
    expression = formula.get("expression", "")
    
    # Control flow keywords that indicate pseudocode
    control_keywords = ["function", "return", "for each", "if", "while", "loop", "procedure", "step"]
    
    # Check if expression contains control flow
    has_control = any(keyword in expression.lower() for keyword in control_keywords)
    
    if has_control and len(expression) > 80:  # Long control flow
        # Move to pseudocode field if not already there
        if not formula.get("pseudocode"):
            formula["pseudocode"] = expression
        
        # Create compact mathematical expression (placeholder for self-repair)
        # Extract any mathematical notation
        math_pattern = r'[=+\-*/^∑∫∂≤≥<>]+|\b[a-z]\s*=\s*[^,;]+'
        math_parts = re.findall(math_pattern, expression)
        
        if math_parts:
            formula["expression"] = " ".join(math_parts[:3])  # Keep first 3 math expressions
        else:
            # Mark for self-repair
            formula["expression"] = "[NEEDS_MATH_EXPRESSION]"
            formula["_repair_needed"] = "expression_not_mathematical"
    
    return formula


def validate_citations_depth(result: Dict[str, Any]) -> List[str]:
    """Validate citation depth and return issues.
    
    Checks:
    - Each section has ≥1 citation
    - Formula sheet has ≥1 citation
    - Citations have page_range or section_or_heading
    
    Returns:
        List of validation issues
    """
    issues = []
    
    citations = result.get("citations", [])
    summary = result.get("summary", {})
    sections = summary.get("sections", [])
    formulas = summary.get("formula_sheet", [])
    
    # Check citation structure
    shallow_citations = 0
    for citation in citations:
        has_detail = citation.get("page_range") or citation.get("section_or_heading") or citation.get("section")
        if not has_detail:
            shallow_citations += 1
    
    if shallow_citations > len(citations) * 0.5:
        issues.append(f"{shallow_citations}/{len(citations)} citations lack page_range or section_or_heading details")
    
    # Check section coverage (at least some citations should cover sections)
    if len(sections) >= 3 and len(citations) < 2:
        issues.append(f"Only {len(citations)} citations for {len(sections)} sections (need ≥2)")
    
    # Check formula sheet coverage
    if len(formulas) >= 3 and len(citations) < 1:
        issues.append("Formula sheet needs at least 1 citation for traceability")
    
    return issues


def enforce_additional_topics_presence(summary: Dict[str, Any], detected_themes: List[str]) -> List[str]:
    """Ensure overflow themes are captured in Additional Topics section.
    
    Args:
        summary: Summary dict with sections
        detected_themes: All themes detected in material
    
    Returns:
        List of issues if Additional Topics is needed but missing
    """
    issues = []
    sections = summary.get("sections", [])
    
    # Count primary sections (excluding Additional Topics)
    primary_sections = [s for s in sections if "additional" not in s.get("heading", "").lower()]
    
    # If detected themes exceed primary sections, Additional Topics should exist
    if len(detected_themes) > len(primary_sections):
        has_additional = any("additional" in s.get("heading", "").lower() for s in sections)
        
        if not has_additional:
            overflow_count = len(detected_themes) - len(primary_sections)
            issues.append(
                f"Detected {len(detected_themes)} themes but only {len(primary_sections)} primary sections. "
                f"Need 'Additional Topics (Condensed)' section with {overflow_count} compact entries."
            )
    
    return issues


def calculate_comprehensive_quality_score(result: Dict[str, Any], detected_themes: List[str] = None) -> Dict[str, float]:
    """Calculate comprehensive quality metrics for final-ready assessment.
    
    Returns:
        Dict with individual scores and overall final_ready_score (0.0-1.0)
        Target: ≥0.90 for final-ready status
    """
    try:
        summary = result.get("summary", {})
        sections = summary.get("sections", [])
        formulas = summary.get("formula_sheet", [])
        glossary = summary.get("glossary", [])
        citations = result.get("citations", [])
        
        # 1. Coverage Score: Section count vs detected themes
        if detected_themes:
            coverage_score = min(len(sections) / len(detected_themes), 1.0)
        else:
            coverage_score = 1.0 if len(sections) >= 4 else len(sections) / 4
        
        # 2. Numeric Density: % of examples with numbers (domain-aware)
        total_examples = 0
        numeric_examples = 0
        
        for section in sections:
            for concept in section.get("concepts", []):
                example = concept.get("example", "")
                if example:
                    total_examples += 1
                    if re.search(r'\d', example):
                        numeric_examples += 1
        
        # Domain-aware target: quant domains need high numeric density
        sample_text = str(summary)[:2000]
        domain = detect_domain(sample_text)
        
        if domain == "quant":
            target_numeric_ratio = 0.7  # 70% for quantitative domains
        elif domain == "qual":
            target_numeric_ratio = 0.2  # 20% for qualitative domains
        else:
            target_numeric_ratio = 0.5  # 50% for mixed
        
        numeric_density = (numeric_examples / max(total_examples, 1)) if total_examples > 0 else 0.5
        # Normalize against target
        numeric_density_score = min(numeric_density / target_numeric_ratio, 1.0)
        
        # 3. Formula Completeness: % with variables defined + worked examples
        formula_completeness = 0.0
        if formulas:
            complete_formulas = 0
            for formula in formulas:
                has_variables = bool(formula.get("variables"))
                has_example = bool(formula.get("worked_example") or formula.get("worked_examples"))
                has_expression = bool(formula.get("expression"))
                
                if has_variables and has_example and has_expression:
                    complete_formulas += 1
            
            formula_completeness = complete_formulas / len(formulas)
        else:
            formula_completeness = 1.0  # No formulas expected
        
        # 4. Citation Depth: % with page_range or section_or_heading
        citation_depth = 0.0
        if citations:
            detailed_citations = 0
            for citation in citations:
                has_detail = bool(citation.get("page_range") or citation.get("section_or_heading") or citation.get("section"))
                if has_detail:
                    detailed_citations += 1
            
            citation_depth = detailed_citations / len(citations)
        else:
            citation_depth = 0.5  # Neutral if no citations
        
        # 5. Readability: Average sentence length (target: 18-28 tokens/sentence)
        all_text = ""
        for section in sections:
            for concept in section.get("concepts", []):
                all_text += concept.get("explanation", "") + " "
        
        sentences = re.split(r'[.!?]+', all_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if sentences:
            avg_tokens_per_sentence = sum(len(s.split()) for s in sentences) / len(sentences)
            # Target: 18-28 tokens/sentence for density
            if 18 <= avg_tokens_per_sentence <= 28:
                readability_score = 1.0
            elif avg_tokens_per_sentence < 18:
                readability_score = avg_tokens_per_sentence / 18
            else:  # > 28
                readability_score = max(0.6, 28 / avg_tokens_per_sentence)
        else:
            readability_score = 0.5
        
        # 6. Glossary Score: Target ≥10 terms
        glossary_score = min(len(glossary) / 10, 1.0)
        
        # Overall Final-Ready Score (weighted average)
        final_ready_score = (
            coverage_score * 0.20 +          # 20% coverage
            numeric_density_score * 0.15 +    # 15% numeric density
            formula_completeness * 0.20 +     # 20% formula completeness
            citation_depth * 0.15 +           # 15% citation depth
            readability_score * 0.15 +        # 15% readability
            glossary_score * 0.15             # 15% glossary
        )
        
        return {
            "coverage_score": round(coverage_score, 2),
            "numeric_density": round(numeric_density, 2),
            "numeric_density_score": round(numeric_density_score, 2),
            "formula_completeness": round(formula_completeness, 2),
            "citation_depth": round(citation_depth, 2),
            "readability_score": round(readability_score, 2),
            "avg_tokens_per_sentence": round(avg_tokens_per_sentence, 1) if sentences else 0,
            "glossary_score": round(glossary_score, 2),
            "final_ready_score": round(final_ready_score, 2),
            "is_final_ready": final_ready_score >= 0.90,
            "domain": domain,
            "target_numeric_ratio": target_numeric_ratio
        }
    
    except Exception as e:
        print(f"[QUALITY METRICS] Error calculating: {e}")
        return {
            "final_ready_score": 0.5,
            "is_final_ready": False,
            "error": str(e)
        }
