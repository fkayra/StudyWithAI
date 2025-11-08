"""
AI-powered summary service with map-reduce for large documents
Includes domain detection and quality guardrails for consistent output
"""
from typing import List, Optional, Dict
import os
import requests
from app.config import (
    OPENAI_MODEL, TEMPERATURE, TOP_P,
    CHUNK_INPUT_TARGET, MERGE_OUTPUT_BUDGET
)
from app.utils.files import approx_tokens_from_text_len
from app.utils.chunking import split_text_approx_tokens, merge_texts


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ========== PROMPTS ==========

SYSTEM_PROMPT = """You are StudyWithAI, an elite academic tutor specializing in deep conceptual understanding. Your mission: transform course materials into comprehensive, deeply explanatory study notes that build mastery.

CORE PRINCIPLES (NON-NEGOTIABLE):
1. **Complete Coverage**: Cover EVERY major concept, formula, and algorithm in the material
2. **Maximum Depth**: Use all available tokens for thorough explanations, NOT practice questions
3. **Worked Examples**: Provide an example for every concept/formula.
   - In quantitative/technical domains use **numeric** examples with actual calculations,
   - In qualitative domains use **anchored** examples (dates, names, quotes, cases).
4. **Teach Directly**: Write as if teaching the student, not describing the document
5. **Quality Standards**:
   - Each concept: definition, extensive explanation (3-4 paragraphs), multiple concrete examples with calculations
   - Each formula: full variable definitions, derivation steps, multiple worked examples, edge cases
   - Each algorithm: purpose, step-by-step procedure, complexity analysis, implementation notes, common pitfalls

OUTPUT REQUIREMENTS:
- COMPREHENSIVE: Cover all major topics (minimum 3-5 sections)
- DEEPLY DETAILED: Each concept needs extensive explanation with multiple examples
- PRACTICAL: Include worked calculations, algorithm complexity, edge cases
- COMPLETE: Formula sheet and glossary REQUIRED
- NO PRACTICE QUESTIONS: Use that token budget for deeper explanations instead
- JSON ONLY: Output pure JSON (no markdown, no extra text)

EVRENSEL QUALITY RULES (UNIVERSAL, DOMAIN-AGNOSTIC):
1. **Expression vs Pseudocode**: Keep `expression` as mathematical notation (e.g., f(x) = ax² + bx + c). Put pseudocode/algorithm steps into `pseudocode` or `notes` field.
2. **Minor Themes Integration**: Do **not** create a separate "Additional Topics" section. Integrate overflow/minor themes as brief sub-concepts under the most relevant section.
3. **Domain-Aware Examples**: 
   - For quantitative domains (math, physics, CS, economics, stats): Ensure at least one numeric example per concept with actual numbers
   - For qualitative domains (law, literature, history): Use anchored examples with dates, names, quotes
   - Auto-detect domain and adapt accordingly
4. **Citation Depth**: Include specific page_range or section_or_heading in citations for traceability
5. **Tone**: Keep tone instructional, concise subheadings, avoid domain-specific verbosity unless detected

⚠️ PRE-FINALIZATION SELF-CHECK:
Before outputting, verify your work against your internal plan:
✓ Did you cover all topics from your outline?
✓ Does every formula have: expression (MATH ONLY) + variables + multiple worked examples?
✓ Did you move any pseudocode from 'expression' to 'pseudocode' field?
✓ Does every concept have at least 2-3 concrete examples (numeric for quant, anchored for qual)?
✓ Did you include algorithm complexity analysis where applicable?
✓ Does glossary have ≥10 substantive terms?
✓ Is JSON structure complete and valid (all brackets closed)?
✓ Did you use full token budget for depth (no practice questions)?
✓ Did you include 'Additional Topics (Condensed)' section if needed?
✓ Do citations have section_or_heading or page_range details?

If any check fails, revise before output."""


def get_chunk_summary_prompt(language: str = "en") -> str:
    """
    Prompt for summarizing individual chunks (MAP phase)
    Returns structured mini-JSON to preserve concept/formula/example separation
    """
    lang_instr = "Write in TURKISH." if language == "tr" else "Write in ENGLISH."
    
    return f"""Extract structured knowledge from this course excerpt.

{lang_instr}

OUTPUT AS VALID JSON (no markdown fences):

{{
  "concepts": [
    {{
      "term": "Concept name",
      "definition": "Precise definition",
      "explanation": "How it works, why it matters (2-3 sentences)",
      "example": "Concrete example with numbers if applicable"
    }}
  ],
  "formulas": [
    {{
      "name": "Formula name",
      "expression": "Mathematical notation",
      "variables": {{"x": "meaning", "y": "meaning"}},
      "worked_example": "Step-by-step calculation with actual numbers"
    }}
  ],
  "theorems": [
    {{
      "name": "Theorem/Principle name",
      "statement": "Formal statement",
      "proof_sketch": "Key proof steps or intuition",
      "application": "When/how to use it"
    }}
  ],
  "examples": [
    {{
      "context": "What problem/scenario",
      "solution": "Step-by-step solution with calculations",
      "key_insight": "Why this approach works"
    }}
  ]
}}

RULES:
- Include ALL concepts, formulas, theorems, and worked examples from the text
- NO meta-commentary ("this text discusses...") - extract direct knowledge
- If a category (formulas/theorems/examples) is absent, **omit that field** entirely (do not return empty arrays)
- Every formula MUST have worked_example with actual numbers
- Output ONLY valid JSON, no extra text"""


def detect_domain(text: str) -> str:
    """
    Automatically detect document domain from content to adjust summary style.
    Returns: 'technical', 'social', 'procedural', or 'general'
    """
    sample = text[:4000].lower()
    
    # Technical/scientific indicators
    technical_keywords = ["equation", "theorem", "proof", "algorithm", "derivative", 
                         "integral", "matrix", "function", "variable", "formula",
                         "calculate", "compute", "solve"]
    
    # Social sciences indicators
    social_keywords = ["policy", "sociology", "history", "philosophy", "ethics",
                      "society", "culture", "theory", "political", "economic",
                      "psychology", "social"]
    
    # Procedural/manual indicators
    procedural_keywords = ["step", "procedure", "manual", "instruction", "how to",
                          "guide", "process", "method", "implementation", "install"]
    
    technical_count = sum(1 for k in technical_keywords if k in sample)
    social_count = sum(1 for k in social_keywords if k in sample)
    procedural_count = sum(1 for k in procedural_keywords if k in sample)
    
    if technical_count >= 3:
        return "technical"
    elif social_count >= 3:
        return "social"
    elif procedural_count >= 3:
        return "procedural"
    return "general"


def quality_score_legacy(result: dict) -> float:
    """
    Calculate quality score (0.0-1.0) based on content depth and richness.
    Focus: concept depth, formula completeness, examples, glossary (NO practice questions)
    """
    try:
        s = result.get("summary", {})
        sections = s.get("sections", [])
        
        # Count concepts and check depth
        num_concepts = 0
        total_explanation_length = 0
        total_examples = 0
        
        for sec in sections:
            concepts = sec.get("concepts", [])
            num_concepts += len(concepts)
            
            for concept in concepts:
                explanation = concept.get("explanation", "")
                total_explanation_length += len(explanation)
                
                # Count examples (either array or single)
                examples = concept.get("examples", [])
                if isinstance(examples, list):
                    total_examples += len(examples)
                elif concept.get("example"):
                    total_examples += 1
        
        avg_explanation_length = total_explanation_length / max(num_concepts, 1)
        avg_examples_per_concept = total_examples / max(num_concepts, 1)
        
        # Count formulas and check completeness
        formulas = s.get("formula_sheet", [])
        num_formulas = len(formulas)
        formulas_with_derivation = sum(1 for f in formulas if f.get("derivation_steps") or "deriv" in f.get("notes", "").lower())
        formulas_with_examples = sum(1 for f in formulas if f.get("worked_examples") or "example" in f.get("notes", "").lower())
        
        # Count glossary terms
        num_glossary = len(s.get("glossary", []))
        
        # Calculate weighted score (depth-focused)
        concept_depth_score = min((avg_explanation_length / 400), 1.0)  # 400 chars = good depth
        example_richness_score = min(avg_examples_per_concept / 2.0, 1.0)  # 2 examples per concept = target
        formula_completeness_score = formulas_with_examples / max(num_formulas, 1) if num_formulas > 0 else 0.5
        glossary_score = min(num_glossary / 10, 1.0)  # 10 terms = target
        
        score = (
            concept_depth_score * 0.30 +        # 30% for explanation depth
            example_richness_score * 0.30 +     # 30% for example richness
            formula_completeness_score * 0.25 + # 25% for formula completeness
            glossary_score * 0.15               # 15% for glossary
        )
        
        print(f"[QUALITY SCORE] Concepts: {num_concepts}, Avg explanation: {int(avg_explanation_length)} chars, "
              f"Avg examples/concept: {avg_examples_per_concept:.1f}, Formulas: {num_formulas} "
              f"(derivation: {formulas_with_derivation}, examples: {formulas_with_examples}), "
              f"Glossary: {num_glossary}, Score: {score:.2f}")
        
        return round(score, 2)
    except Exception as e:
        print(f"[QUALITY SCORE] Error calculating: {e}")
        return 0.5  # Default to medium quality on error


def get_final_merge_prompt(language: str = "en", additional_instructions: str = "", domain: str = "general") -> str:
    """
    Soft Merge mode: covers all themes, scales sections dynamically (FULL or SHORT)
    Enhanced with evrensel quality rules
    """
    lang_instr = "Use TURKISH for ALL output." if language == "tr" else "Use ENGLISH for ALL output."
    additional = f"\n\nUSER REQUIREMENTS (FOLLOW STRICTLY):\n{additional_instructions}" if additional_instructions else ""

    # Domain-specific guidance
    domain_guidance = ""
    if domain == "technical":
        domain_guidance = "\n- NUMERIC EXAMPLES REQUIRED: Include actual numbers, calculations, and step-by-step solutions in every example."
    elif domain == "social":
        domain_guidance = "\n- ANCHORED EXAMPLES REQUIRED: Include dates, names, quotes, and specific historical/case references in examples."
    else:
        domain_guidance = "\n- CONCRETE EXAMPLES: Use numeric or anchored examples as appropriate to the domain."

    return f"""GOAL
Create a comprehensive, exam-ready study guide from the provided material. It must stand alone as the only thing a student needs before a final.

LANGUAGE
{lang_instr}

CONSTRAINTS
- Single pass, one JSON object. No markdown fences, no meta commentary.
- Do NOT include any practice questions.
- Be domain-agnostic; do NOT assume a specific book or course.
- Prefer concrete, worked examples over vague prose.
- No empty arrays: if you cannot populate a field meaningfully, **omit** that field entirely.{domain_guidance}{additional}

SILENT PLANNING (do internally before writing):
1) Identify **all** themes/topics in the material and rank by centrality.
2) Allocate depth to top themes (FULL sections) and compress minor themes (SHORT sections).
3) Do **not** drop any theme; if budget is tight, include a SHORT section (1 concise concept) instead of omitting.
4) Scale number of sections with content size. MIN ≥ 4 full sections; aim 6–12 total if material is broad.

OUTPUT REQUIREMENTS:
- Include **every discovered theme** as its own section OR as a sub-concept in a related section.
- FULL sections: 2–5 concepts with dense explanations and an anchored or numeric example.
- SHORT sections: 1 compact concept (definition + brief explanation + 1–2 key_points). Example optional if genuinely inapplicable.
- **IMPORTANT**: Integrate overflow themes as **brief sub-concepts** under the most relevant existing section (no standalone "Additional Topics" section):
  - Add as a minimal concept with term, definition (1 sentence), key_points (1-2 critical facts)
  - No example needed for these overflow sub-concepts
  - Keep them concise (50-100 words max)
- Keep wording specific to the uploaded material (no generic filler).

OUTPUT EXACTLY THIS JSON SCHEMA (no extras, no omissions):
{{
  "summary": {{
    "title": "Study Notes: <topic>",
    "overview": "<2–4 sentences on scope and importance>",
    "learning_objectives": [
      "Verb-led, outcome-focused objective 1",
      "Verb-led, outcome-focused objective 2"
    ],
    "sections": [
      {{
        "heading": "<theme>",
        "concepts": [
          {{
            "term": "<concept>",
            "definition": "<precise, syllabus-level definition>",
            "explanation": "<2–3 dense paragraphs teaching mechanism, intuition, edge cases>",
            "example": "<worked example (numeric OR anchored, as appropriate)>",
            "key_points": ["<short fact>", "<short fact>"],
            "pitfalls": ["<common error>", "<boundary condition>"]
          }},
          {{
            "term": "<overflow minor concept>",
            "definition": "<1 sentence definition>",
            "key_points": ["<critical fact for exam>"]
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "<formula / algorithm / method>",
        "expression": "<MATHEMATICAL notation ONLY - e.g., f(x) = ax² + bx + c>",
        "variables": {{"symbol": "meaning"}},
        "worked_example": "<short numeric example with actual calculations>",
        "pseudocode": "<OPTIONAL: if algorithm, put step-by-step procedure here>",
        "notes": "<when it applies, constraints, complexity>"
      }}
    ],
    "glossary": [
      {{"term": "<term>", "definition": "<one-line, testable definition>"}}
    ]
  }},
  "citations": [
    {{"file_id": "source", "section_or_heading": "<specific section/chapter>", "page_range": "<page numbers if available>", "evidence": "<max 200 chars snippet>"}}
  ]
}}

BUDGETING & COVERAGE RULES
- Guarantee coverage of **all themes** (FULL or SHORT).
- Prefer depth for core themes; compress minor ones in 'Additional Topics (Condensed)' section.
- Formula_sheet: include every formula/algorithm/method with:
  ✓ expression = MATH NOTATION (not pseudocode)
  ✓ variables = complete symbol dictionary
  ✓ worked_example = numeric calculation with actual numbers
  ✓ pseudocode = (optional) algorithm steps if needed
- Remove empty/placeholder fields; validate JSON (no trailing commas, balanced braces).

VALIDATION CHECKLIST (before output):
✓ Every primary section has ≥1 citation
✓ Formula_sheet has ≥1 citation for traceability
✓ Expression field uses MATH, not pseudocode
✓ Overflow themes integrated as brief sub-concepts in related sections (NOT separate "Additional Topics")
✓ Examples are concrete (numeric for quant domains, anchored for qual domains)
✓ Glossary has ≥10 terms

OUTPUT PURE JSON NOW (no other text):"""


def get_reduce_outline_prompt(language: str, domain: str) -> str:
    """
    First stage of two-stage REDUCE: generate topology/outline only
    """
    L = "Use TURKISH." if language == "tr" else "Use ENGLISH."
    return f"""You are planning a study-guide topology only. {L}
Output pure JSON with fields: title, sections[heading, concepts[{{
  "term": "...", "expected_example": "numeric|anchored"
}}]], formula_plan[name, expected_example], glossary_target (int).

Rules:
- Create a sufficient number of sections to cover ALL themes (outline size should scale with content depth).
- Do NOT force or assume a fixed number like 6–12. Let theme-count + output-budget decide.
- Prioritize major themes; compress minor themes as concise sub-concepts under the closest section.
- Prefer 'numeric' examples for quantitative/technical material and 'anchored' examples for qualitative material.
- Do NOT write explanations or examples, only the topology."""


def get_reduce_fill_prompt(language: str, domain: str, additional: str = "") -> str:
    """
    Second stage of two-stage REDUCE: fill outline with content
    """
    L = "Use TURKISH for ALL output." if language == "tr" else "Use ENGLISH for ALL output."
    domain_note = ""
    if domain == "technical":
        domain_note = "\n- NUMERIC EXAMPLES REQUIRED for every quantitative concept."
    elif domain == "social":
        domain_note = "\n- ANCHORED EXAMPLES REQUIRED (dates, names, cases) for qualitative concepts."
    return f"""Fill the given OUTLINE into a complete, exam-ready study guide.
{L}{domain_note}
Constraints:
- KEEP the outline section + concept order (do NOT rename or remove).
- Each concept → definition + 2–3 dense paragraphs + ONE example matching expected_example:
  • numeric → real numbers + step-by-step calculation
  • anchored → specific dates/names/cases
- Each formula → expression (MATH ONLY), variables dict, ≥1 numeric worked_example, optional pseudocode, notes.
- Glossary ≥ 15 terms.
- Provide citations for each main section and formula sheet.
- If the outline missed some themes, you MAY add concise sub-concepts, but avoid unnecessary padding.
- Output single valid JSON, no markdown.

{additional}"""


def get_no_files_prompt(topic: str, language: str = "en") -> str:
    """Prompt for generating summary without uploaded files"""
    lang_instr = "Generate in TURKISH." if language == "tr" else "Generate in ENGLISH."
    
    return f"""Create comprehensive study notes on this topic: {topic}

{lang_instr}

Use the same JSON structure as file-based summaries. Focus on depth, NOT practice questions:
- Learning objectives
- Core concepts with extensive explanations (3-4 paragraphs) and multiple worked examples
- Formula sheet with derivations and worked examples (if applicable)
- Glossary of key terms (minimum 10 terms)
- DO NOT include practice questions - use all tokens for explanations and examples

Output valid JSON only (no markdown code blocks)."""


# ========== Helper Functions for Two-Stage REDUCE ==========

def estimate_full_section_tokens(domain: str) -> int:
    """
    Estimate tokens needed for one complete section with concepts + examples
    """
    return 900 if domain == "technical" else 750


def infer_theme_heads(aggregated_knowledge: dict) -> list:
    """
    Extract top-level theme headings from aggregated chunk data
    """
    heads = []
    for c in aggregated_knowledge.get("concepts", []):
        src = c.get("_source") or {}
        hp = src.get("heading_path") or src.get("heading")
        if hp:
            heads.append(hp.split(" > ")[0])
    return list({h.strip() for h in heads if h})


def compute_outline_targets(aggregated_knowledge: dict, out_cap: int, domain: str) -> tuple:
    """
    Compute dynamic outline target ranges based on content and budget
    Returns: (target_min, target_soft_max, approx_theme_count)
    """
    theme_heads = infer_theme_heads(aggregated_knowledge)
    approx_theme_count = max(1, len(theme_heads))
    full_cost = estimate_full_section_tokens(domain)
    body_budget = int(out_cap * 0.7)
    soft_max_by_budget = max(8, body_budget // full_cost)
    target_min = max(6, min(approx_theme_count, 10))
    target_soft_max = max(target_min + 2, min(soft_max_by_budget, approx_theme_count + 4))
    return target_min, target_soft_max, approx_theme_count


def coverage_gaps(outline: dict, aggregated_knowledge: dict) -> list:
    """
    Detect missing themes: present in source but not in outline
    """
    planned = {(sec.get("heading") or "").strip() for sec in outline.get("sections", [])}
    source_tops = set(infer_theme_heads(aggregated_knowledge))
    return [h for h in source_tops if h and all(h.lower() not in p.lower() for p in planned)]


def validate_reduce_output(result: dict) -> list:
    """
    Universal validation for any domain/subject.
    Checks examples, formulas, glossary, citations with domain-agnostic rules.
    Returns list of issue strings (empty if all good)
    """
    import re
    issues = []
    summary = result.get("summary", {})
    
    # Check sections
    sections = summary.get("sections", [])
    if len(sections) < 4:
        issues.append(f"Too few sections ({len(sections)}), expected ≥4")
    
    # Check concepts and their examples
    for i, sec in enumerate(sections):
        concepts = sec.get("concepts", [])
        if not concepts:
            issues.append(f"Section {i+1} '{sec.get('heading', 'Unknown')}' has no concepts")
        
        for c in concepts:
            term = c.get("term", "Unknown")
            expected_example = c.get("expected_example", "")
            example_text = c.get("example", "")
            
            # If expected_example is set, validate it
            if expected_example == "numeric" and example_text:
                # Must have at least one digit AND one operator
                has_digit = bool(re.search(r'\d', example_text))
                has_operator = bool(re.search(r'[+\-*/=]', example_text))
                if not (has_digit and has_operator):
                    issues.append(f"Concept '{term}' expected numeric example but missing calculations (need digits + operators)")
            elif expected_example == "numeric" and not example_text:
                issues.append(f"Concept '{term}' missing numeric example")
            
            if expected_example == "anchored" and example_text:
                # Must have a capitalized word (named entity) OR a year (4-digit number)
                has_named_entity = bool(re.search(r'\b[A-Z][a-z]+', example_text))
                has_year = bool(re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', example_text))
                if not (has_named_entity or has_year):
                    issues.append(f"Concept '{term}' expected anchored example but missing specific context (need names, places, or years)")
            elif expected_example == "anchored" and not example_text:
                issues.append(f"Concept '{term}' missing anchored example")
            
            # General check: if no example and no key_points, flag it
            if not example_text and not c.get("key_points"):
                issues.append(f"Concept '{term}' missing both example and key_points")
        
        # Check citations per section
        citations = result.get("citations", [])
        section_heading = sec.get("heading", "")
        has_citation = any(
            section_heading.lower() in cite.get("section_or_heading", "").lower()
            for cite in citations
        )
        if not has_citation and i < 3:  # At least first 3 sections need citations
            issues.append(f"Section '{section_heading}' missing citation with section_or_heading")
    
    # Check formulas (if they exist)
    formulas = summary.get("formula_sheet", [])
    for f in formulas:
        fname = f.get("name", "Unknown")
        expression = f.get("expression", "")
        variables = f.get("variables", {})
        worked_example = f.get("worked_example", "")
        
        if not expression:
            issues.append(f"Formula '{fname}' missing expression")
        else:
            # Detect pseudocode in expression field (should be MATH ONLY)
            if re.search(r'\b(function|return|if|for|while|def|class|var|let|const)\b', 
                        expression, re.IGNORECASE):
                issues.append(f"Formula '{fname}' expression contains pseudocode (must be MATH ONLY, use 'pseudocode' field instead)")
        
        if not variables or (isinstance(variables, dict) and len(variables) == 0):
            issues.append(f"Formula '{fname}' missing variables dictionary")
        
        if not worked_example:
            issues.append(f"Formula '{fname}' missing worked_example")
        elif not re.search(r'\d', worked_example):  # Must contain numeric calculation
            issues.append(f"Formula '{fname}' worked_example must include numeric calculation")
    
    # Check glossary
    glossary = summary.get("glossary", [])
    if len(glossary) < 15:
        issues.append(f"Glossary too short ({len(glossary)} terms), expected ≥15")
    
    return issues


def build_self_repair_prompt(result: dict, issues: list, language: str) -> str:
    """
    Universal self-repair prompt that works for ANY domain/subject.
    Domain-agnostic validation and repair instructions.
    """
    import json
    lang = "Use TURKISH." if language == "tr" else "Use ENGLISH."
    issues_text = "\n- ".join(issues)
    
    return f"""{lang}
You are repairing a study-guide JSON. 
This must work for ANY subject (math, history, medicine, CS, economics, law, engineering, psychology, etc.).

RULES (MUST):
- Do NOT remove or rename existing sections or concepts.
- Preserve all correct content. Only repair or add what is missing.
- Return FULL valid JSON only (no markdown, no comments).

REQUIREMENTS (APPLY GENERALLY):
1) Example requirements:
   If a concept has expected_example="numeric" → add one step-by-step numeric example using real numbers.
   If a concept has expected_example="anchored" → add one real-world contextual example (specific place, year, case, dataset, experiment, historical event, etc.).

2) Formula requirements (if formula_sheet exists):
   - expression must be math notation (not prose).
   - variables must explain every symbol.
   - worked_example must include real numeric calculation steps.

3) Glossary requirement:
   - Glossary must contain at least 15 distinct terms total (expand if needed).

4) Citations requirement:
   - Each top-level section must include at least one citation with section_or_heading and page_range based on the source.
   - Evidence snippets should be concise (no truncation).

5) Consistency rule:
   - Do NOT invent topics or facts not supported by the user's uploaded document.

Issues to fix:
- {issues_text}

CURRENT JSON:
{json.dumps(result, ensure_ascii=False)}"""


# ========== Two-Stage REDUCE Orchestrator ==========

def reduce_two_stage(
    aggregated_knowledge: dict,
    language: str,
    domain: str,
    out_cap: int,
    additional_instructions: str = ""
) -> dict:
    """
    Two-stage REDUCE process:
    1. Generate outline/topology
    2. Fill outline with content
    3. Validate and self-repair if needed
    
    Returns: Final summary dict (parsed JSON)
    """
    import json
    from app.utils.json_helpers import parse_json_robust
    
    # === STAGE 1: Generate Outline ===
    print("[REDUCE] Stage 1: Generating outline/topology...")
    outline_prompt = get_reduce_outline_prompt(language, domain)
    
    # Truncate aggregated knowledge if too large (keep structure, limit content)
    agg_str = json.dumps(aggregated_knowledge, ensure_ascii=False)
    if len(agg_str) > 150000:
        print(f"[REDUCE] Truncating aggregated knowledge ({len(agg_str)} → 150k chars)")
        agg_str = agg_str[:150000] + "..."
    
    outline_user = (
        outline_prompt
        + "\n\nSTRUCTURED SOURCE KNOWLEDGE:\n"
        + agg_str
    )
    
    outline_json = call_openai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=outline_user,
        max_output_tokens=min(1200, int(out_cap * 0.15)),
        temperature=0
    )
    outline = parse_json_robust(outline_json)
    
    # Compute dynamic targets
    target_min, target_soft_max, approx_themes = compute_outline_targets(
        aggregated_knowledge=aggregated_knowledge,
        out_cap=out_cap,
        domain=domain
    )
    print(f"[REDUCE] Outline targets: min={target_min}, soft_max={target_soft_max}, themes={approx_themes}")
    
    # === SELF-REPAIR: Expand if outline too shallow ===
    if len(outline.get("sections", [])) < target_min:
        print(f"[REDUCE] Outline too shallow ({len(outline.get('sections', []))} < {target_min}), expanding...")
        outline_user += (
            f"\n\n[REPAIR] Expand sections to ensure full theme coverage "
            f"(expected ~{target_min}–{target_soft_max}, but exceeding is allowed if needed)."
        )
        outline_json = call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=outline_user,
            max_output_tokens=1200,
            temperature=0
        )
        outline = parse_json_robust(outline_json)
    
    # === SELF-REPAIR: Check coverage gaps ===
    missing = coverage_gaps(outline, aggregated_knowledge)
    if missing:
        print(f"[REDUCE] Coverage gaps detected: {missing}")
        outline_user += (
            "\n\n[REPAIR] Missing key themes: "
            + ", ".join(missing)
            + ". Add them as sections or concise sub-concepts."
        )
        outline_json = call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=outline_user,
            max_output_tokens=1200,
            temperature=0
        )
        outline = parse_json_robust(outline_json)
    
    # === STAGE 2: Fill Outline ===
    print("[REDUCE] Stage 2: Filling outline with content...")
    fill_prompt = get_reduce_fill_prompt(language, domain, additional_instructions)
    fill_user = (
        fill_prompt
        + "\n\nOUTLINE (DO NOT CHANGE ORDER):\n"
        + json.dumps(outline, ensure_ascii=False, indent=2)
        + "\n\nSTRUCTURED SOURCE KNOWLEDGE:\n"
        + agg_str
    )
    
    filled_json = call_openai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=fill_user,
        max_output_tokens=min(out_cap, MERGE_OUTPUT_BUDGET[1]),
        temperature=0
    )
    result = parse_json_robust(filled_json)
    
    # === STAGE 3: Validate & Self-Repair ===
    print("[REDUCE] Stage 3: Validating output...")
    issues = validate_reduce_output(result)
    if issues:
        print(f"[REDUCE] Quality issues detected: {issues}")
        repair_user = build_self_repair_prompt(result, issues, language)
        repaired = call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=repair_user,
            max_output_tokens=min(out_cap, 8000),
            temperature=0
        )
        result = parse_json_robust(repaired) or result
        print("[REDUCE] Self-repair complete")
    else:
        print("[REDUCE] Output validated ✓")
    
    return result


# ========== OpenAI Integration ==========

def call_openai(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
    temperature: float = TEMPERATURE,
    top_p: float = TOP_P,
    retry_on_length: bool = True
) -> str:
    """
    Call OpenAI API with given prompts and automatic retry on truncation
    Returns the response text
    """
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    attempt = 0
    current_max_tokens = max_output_tokens
    
    while attempt < 2:  # Max 2 attempts
        attempt += 1
        
        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": current_max_tokens
        }
        
        print(f"[OPENAI REQUEST] Attempt {attempt}, Model: {OPENAI_MODEL}, max_tokens: {current_max_tokens}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(f"OpenAI API call failed ({response.status_code}): {error_detail}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        finish_reason = result["choices"][0].get("finish_reason")
        
        print(f"[OPENAI RESPONSE] Returned {len(content)} chars, finish_reason: {finish_reason}")
        
        # If truncated and retry enabled, try with 20% more tokens
        if finish_reason == "length" and retry_on_length and attempt < 2:
            current_max_tokens = min(int(current_max_tokens * 1.2), 16000)
            print(f"[OPENAI RETRY] Response truncated, retrying with {current_max_tokens} tokens")
            continue
        
        return content
    
    # If still truncated after retry, return what we have
    return content


# ========== Map-Reduce Pipeline ==========

def summarize_chunk(
    chunk_text: str,
    language: str = "en",
    additional_instructions: str = "",
    out_budget: int = None
) -> str:
    """
    Summarize a single chunk of text (MAP phase)
    Returns structured mini-JSON with concepts/formulas/theorems/examples
    """
    # Adaptive budget based on chunk content
    if out_budget is None:
        from app.utils.adaptive_budget import calculate_chunk_budget
        out_budget = calculate_chunk_budget(chunk_text)
        print(f"[MAP ADAPTIVE] Allocated {out_budget} tokens for this chunk")
    
    user_prompt = get_chunk_summary_prompt(language)
    
    if additional_instructions:
        user_prompt += f"\n\nUser preferences: {additional_instructions}"
    
    user_prompt += f"\n\nTEXT TO EXTRACT FROM:\n{chunk_text}"
    
    return call_openai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_output_tokens=out_budget
    )


def merge_summaries(
    chunk_summaries: List[str],
    language: str = "en",
    additional_instructions: str = "",
    out_budget: int = 1500,
    domain: str = "general",
    chunk_citations: List[Dict] = None
) -> str:
    """
    Merge structured chunk JSONs into final exam-ready summary (REDUCE phase)
    Now receives structured mini-JSONs from MAP phase
    Returns final JSON string
    """
    import json
    
    # Parse chunk JSONs and aggregate
    all_concepts = []
    all_formulas = []
    all_theorems = []
    all_examples = []
    
    for i, chunk_json in enumerate(chunk_summaries):
        try:
            chunk_data = json.loads(chunk_json)
            all_concepts.extend(chunk_data.get("concepts", []))
            all_formulas.extend(chunk_data.get("formulas", []))
            all_theorems.extend(chunk_data.get("theorems", []))
            all_examples.extend(chunk_data.get("examples", []))
        except json.JSONDecodeError as e:
            print(f"[REDUCE WARNING] Chunk {i+1} JSON parse failed: {e}")
            # Fallback: treat as plain text
            all_concepts.append({
                "term": f"Content from chunk {i+1}",
                "definition": "Raw content (parse failed)",
                "explanation": chunk_json[:500],
                "example": ""
            })
    
    # Enrich concepts with source citations
    if chunk_citations:
        for i, chunk_json in enumerate(chunk_summaries):
            try:
                chunk_data = json.loads(chunk_json)
                citation_info = chunk_citations[i] if i < len(chunk_citations) else {}
                
                # Add citation metadata to each concept
                for concept in chunk_data.get("concepts", []):
                    concept["_source"] = {
                        "chunk": i + 1,
                        "heading": citation_info.get("heading_path", "Unknown")
                    }
                
                for formula in chunk_data.get("formulas", []):
                    formula["_source"] = {
                        "chunk": i + 1,
                        "heading": citation_info.get("heading_path", "Unknown")
                    }
            except:
                pass
    
    # Create structured source material for REDUCE
    aggregated_knowledge = {
        "total_concepts": len(all_concepts),
        "total_formulas": len(all_formulas),
        "total_theorems": len(all_theorems),
        "total_examples": len(all_examples),
        "concepts": all_concepts,
        "formulas": all_formulas,
        "theorems": all_theorems,
        "examples": all_examples,
        "source_structure": chunk_citations if chunk_citations else []
    }
    
    # Use two-stage REDUCE with fallback to single-stage if errors occur
    try:
        print("[REDUCE] Attempting two-stage REDUCE (outline → fill → validate)...")
        result = reduce_two_stage(
            aggregated_knowledge=aggregated_knowledge,
            language=language,
            domain=domain,
            out_cap=out_budget,
            additional_instructions=additional_instructions or ""
        )
        print("[REDUCE] Two-stage REDUCE completed successfully ✓")
        # Return as JSON string (for compatibility with existing pipeline)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        print(f"[REDUCE TWO-STAGE FALLBACK] Error in two-stage REDUCE: {e}")
        print("[REDUCE TWO-STAGE FALLBACK] Falling back to single-stage REDUCE...")
        
        # Fallback: single-stage REDUCE (original implementation)
        user_prompt = get_final_merge_prompt(language, additional_instructions, domain)
        user_prompt += f"\n\nSTRUCTURED SOURCE KNOWLEDGE (from {len(chunk_summaries)} chunks):\n{json.dumps(aggregated_knowledge, indent=2, ensure_ascii=False)}"
        
        return call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_output_tokens=out_budget
        )


def map_reduce_summary(
    full_text: str,
    language: str = "en",
    additional_instructions: str = "",
    out_cap: int = 12000,
    force_chunking: bool = False
) -> str:
    """
    Main map-reduce pipeline for large document summarization
    Includes domain detection, structure-aware chunking, and quality guardrails
    
    Args:
        full_text: Complete text to summarize
        language: Output language (en/tr)
        additional_instructions: User's custom requirements
        out_cap: Maximum output tokens based on plan
        force_chunking: Force map-reduce even for small docs (for testing)
    
    Returns:
        JSON string with complete summary
    """
    # 1. DETECT DOMAIN
    domain = detect_domain(full_text)
    print(f"[DOMAIN DETECTION] Detected: {domain}")
    
    # Estimate input tokens
    estimated_tokens = approx_tokens_from_text_len(len(full_text))
    
    # Auto "Density Boost" with flexible thresholds
    from app.config import DENSITY_BOOST_THRESHOLD
    
    # Flexible thresholds:
    # 10k-15k: Soft-Merge (default, no special instructions)
    # >15k: Density-Boost + Additional Topics
    # >40k: Aggressive compression + de-duplication
    
    if estimated_tokens > 40000:
        additional_instructions = (additional_instructions or "") + \
            "\n[AGGRESSIVE DENSITY BOOST]: Very large document. Use extreme compression: " +\
            "(1) Merge similar concepts, (2) 1 concept per minor section, (3) De-duplicate overlapping content, " +\
            "(4) Move all minor themes to 'Additional Topics (Condensed)', (5) Target 18-28 tokens/sentence for density."
        print(f"[AGGRESSIVE DENSITY BOOST] Enabled (estimated_tokens={estimated_tokens} > 40000)")
    elif estimated_tokens > DENSITY_BOOST_THRESHOLD:  # Default 15000
        additional_instructions = (additional_instructions or "") + \
            "\n[DENSITY BOOST]: Large document. Use compression: merge minor topics into compact sections (1 concept each), " +\
            "move overflow to 'Additional Topics (Condensed)', keep all themes visible, prefer dense phrasing (18-28 tokens/sentence)."
        print(f"[DENSITY BOOST] Enabled (estimated_tokens={estimated_tokens} > {DENSITY_BOOST_THRESHOLD})")
    else:
        print(f"[SOFT MERGE] Standard mode (estimated_tokens={estimated_tokens} <= {DENSITY_BOOST_THRESHOLD})")
    
    # Append domain hint to instructions
    domain_hint = f"Content domain: {domain}. Adjust depth and style accordingly."
    enhanced_instructions = f"{additional_instructions}\n\n{domain_hint}" if additional_instructions else domain_hint
    
    # Decide whether to use map-reduce
    # Use chunking if: forced, OR estimated tokens > threshold
    # Threshold increased to 10000 to allow longer single-pass summaries
    use_chunking = force_chunking or estimated_tokens > 10000
    
    if not use_chunking:
        # Small document: single-pass summary
        user_prompt = get_final_merge_prompt(language, enhanced_instructions, domain)
        user_prompt += f"\n\nCOURSE MATERIAL:\n{full_text}"
        
        return call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_output_tokens=min(out_cap, MERGE_OUTPUT_BUDGET[1])
        )
    
    # Large document: map-reduce with structure-aware chunking
    print(f"[MAP-REDUCE] Estimated {estimated_tokens} tokens, using structure-aware chunking")
    
    # 2. EXTRACT STRUCTURE
    from app.utils.structure_parser import extract_heading_hierarchy, chunk_by_headings, blocks_to_text
    
    try:
        blocks = extract_heading_hierarchy(full_text)
        structured_chunks = chunk_by_headings(blocks, target_tokens=CHUNK_INPUT_TARGET)
        print(f"[STRUCTURE] Extracted {len(blocks)} blocks, {len(structured_chunks)} structured chunks")
        
        # Convert structured chunks back to text with heading context
        chunks_with_context = []
        chunk_metadata = []
        
        for chunk_blocks, heading_path in structured_chunks:
            chunk_text = blocks_to_text(chunk_blocks)
            chunks_with_context.append(chunk_text)
            chunk_metadata.append({
                "heading_path": heading_path,
                "block_count": len(chunk_blocks)
            })
        
        chunks = chunks_with_context
        print(f"[STRUCTURE] Heading-aware chunks: {[m['heading_path'] for m in chunk_metadata]}")
        
    except Exception as e:
        # Fallback to simple chunking if structure extraction fails
        print(f"[STRUCTURE WARNING] Failed to extract structure: {e}, using simple chunking")
        chunks = split_text_approx_tokens(full_text, CHUNK_INPUT_TARGET)
        chunk_metadata = [{"heading_path": f"Chunk {i+1}", "block_count": 0} for i in range(len(chunks))]
    
    print(f"[MAP-REDUCE] Processing {len(chunks)} chunks")
    
    # 3. MAP: Summarize each chunk (with adaptive budgeting and citation tracking)
    chunk_summaries = []
    chunk_citations = []
    
    for i, chunk in enumerate(chunks):
        heading_path = chunk_metadata[i].get("heading_path", f"Chunk {i+1}")
        print(f"[MAP-REDUCE] Processing chunk {i+1}/{len(chunks)}: {heading_path}")
        
        summary = summarize_chunk(
            chunk,
            language=language,
            additional_instructions=additional_instructions,
            out_budget=None  # Let adaptive budget calculate
        )
        chunk_summaries.append(summary)
        
        # Track citation metadata for this chunk
        chunk_citations.append({
            "chunk_id": i + 1,
            "heading_path": heading_path,
            "char_start": sum(len(chunks[j]) for j in range(i)),
            "char_end": sum(len(chunks[j]) for j in range(i+1))
        })
    
    # 4. REDUCE: Merge into final JSON with citation tracking
    print(f"[MAP-REDUCE] Merging {len(chunk_summaries)} summaries with domain: {domain}...")
    final_summary = merge_summaries(
        chunk_summaries,
        language=language,
        additional_instructions=enhanced_instructions,
        out_budget=min(out_cap, MERGE_OUTPUT_BUDGET[1]),
        domain=domain,
        chunk_citations=chunk_citations
    )
    
    print("[MAP-REDUCE] Complete!")
    return final_summary


def simple_exam_tutor_summary(
    full_text: str,
    language: str = "en",
    out_cap: int = 16000
) -> str:
    """
    SIMPLE MODE: Elite exam tutor prompt with NO complex processing
    Just: prompt + document → AI → output
    """
    # Truncate full_text if too long (prevent token overflow)
    MAX_INPUT_CHARS = 80000  # ~20k tokens
    if len(full_text) > MAX_INPUT_CHARS:
        print(f"[SIMPLE MODE] Truncating document: {len(full_text)} → {MAX_INPUT_CHARS} chars")
        full_text = full_text[:MAX_INPUT_CHARS] + "\n\n[DOCUMENT TRUNCATED - remaining content omitted]"
    
    # Elite exam tutor prompt
    tutor_prompt = """You are StudyWithAI, an elite exam tutor. Your task is to create a self-sufficient exam study guide from the DOCUMENT CONTENT below. The student will study ONLY this guide, so it must cover EVERY topic, definition, theorem, formula, algorithm, and subtlety present in the document—no omissions, no external knowledge.

THINKING & OUTPUT RULES
- Plan silently: derive a complete outline from the document internally; do not show your reasoning or planning steps. Output ONLY the final study guide.
- Grounding is STRICT: use ONLY facts from the document. If the document lacks a detail, write "[MISSING IN DOC]" rather than guessing.
- Math format: render all math in LaTeX (inline: \\( ... \\), display: \\[ ... \\]). Keep symbols consistent.
- Use as much space as allowed. If space becomes tight, prioritize (1) complete coverage checklists, (2) exact formulas/algorithms, (3) worked examples.

DELIVERABLE = ONE COMPREHENSIVE STUDY GUIDE
1) Title & Metadata
   - Title of the material
   - What this chapter/unit covers in 3–5 sentences (big picture)
   - Prereqs (if implied by the doc)

2) Master Outline (auto-generated from the document)
   - Exact section/subsection list reflecting the source structure
   - One-line objective under each item

3) Core Notes — section by section (repeat this template for every section in the outline)
   For each section:
   - Key Ideas (bullet list of the main points in the author's order)
   - Definitions & Notation (precise; include symbol tables)
   - Theorems/Lemmas/Propositions
       • Formal statement(s) in LaTeX
       • If proof is present in the doc: proof sketch in the doc's style;
         else mark "[MISSING IN DOC]"
   - Formulas & Identities
       • Exact formula set in LaTeX, with variable meanings and units (if any)
   - Algorithms (when applicable)
       • Name + goal
       • Assumptions
       • Pseudocode (clean, minimal)
       • Complexity (\\(O(\\cdot)\\) time/space), optimality conditions, failure modes
   - Worked Example(s)
       • At least one fully worked, step-by-step numeric or symbolic example tied to this section's content
       • Show intermediate steps and the final result
   - Edge Cases & Pitfalls
       • Common mistakes and exam "gotchas" actually mentioned or implied in the doc
   - Micro-Quiz (3–5 quick checks with brief answers, directly grounded in this section)

4) Synthesis & Comparisons (only if the doc supports them)
   - Compare/contrast closely related concepts/algorithms from the doc (tables are fine)
   - When to use which method (decision rules stated in the source)

5) Exam Toolkit
   - Cheat Sheet (dense bullets): all definitions, key formulas, and algorithm steps in one place
   - Problem-solving patterns (if present in the doc)
   - 10 practice questions WITH fully worked solutions that reflect the document's scope and examples (do NOT invent outside content)

6) Glossary of Terms & Symbols (from the doc only)
   - Term → concise definition (1–2 lines), symbol → meaning

7) Coverage Checklist (final sanity pass)
   - List every section, theorem, formula, and algorithm you included, mirroring the document's structure.
   - If anything in the document couldn't fit, list it under "Residual Items" with "[TRUNCATED]" (do not fabricate).

STYLE
- Clear, didactic tone; short paragraphs; informative headings.
- Keep the source's ordering. Use consistent variable names and notation found in the document.
- No external references. No speculation. Everything must be document-grounded.

Now read the DOCUMENT CONTENT and produce the study guide described above.

DOCUMENT CONTENT:
{full_text}"""
    
    try:
        combined_prompt = tutor_prompt.format(full_text=full_text)
    except Exception as e:
        print(f"[SIMPLE MODE ERROR] Prompt format failed: {e}")
        combined_prompt = f"Summarize this document:\n\n{full_text}"
    
    return call_openai(
        system_prompt="You are a helpful AI assistant.",
        user_prompt=combined_prompt,
        max_output_tokens=out_cap,
        temperature=0
    )


def summarize_no_files(
    topic: str,
    language: str = "en",
    out_cap: int = 12000
) -> str:
    """
    Generate summary without uploaded files (from prompt only)
    """
    user_prompt = get_no_files_prompt(topic, language)
    
    return call_openai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_output_tokens=min(out_cap, MERGE_OUTPUT_BUDGET[1])
    )
