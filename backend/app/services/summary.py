"""
AI-powered summary service with map-reduce for large documents
Includes domain detection and quality guardrails for consistent output
Enhanced with deep learning prompts for maximum depth and coverage
"""
from typing import List, Optional, Dict
import os
import requests
import re
from app.config import (
    OPENAI_MODEL, TEMPERATURE, TOP_P,
    CHUNK_INPUT_TARGET, MERGE_OUTPUT_BUDGET
)
from app.utils.files import approx_tokens_from_text_len
from app.utils.chunking import split_text_approx_tokens, merge_texts


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ========== PROMPTS ==========
# Import enhanced deep prompts for maximum quality
from app.services.summary_prompts import SYSTEM_PROMPT_DEEP, FEW_SHOT_EXAMPLES

# Use the deep prompt system-wide
SYSTEM_PROMPT = SYSTEM_PROMPT_DEEP


def get_chunk_summary_prompt(language: str = "en") -> str:
    """
    Prompt for extracting key information from chunks (MAP phase)
    Focus on identifying main themes, evidence, concepts for synthesis
    Returns structured mini-JSON to preserve concept/formula/example separation
    """
    lang_instr = "Write in TURKISH." if language == "tr" else "Write in ENGLISH."
    
    return f"""You are analyzing a document excerpt to extract key information for a professional briefing.

{lang_instr}

YOUR TASK:
Extract the main themes, concepts, evidence, and findings from this excerpt. Focus on:
- Core concepts and their significance
- Key data points, statistics, evidence
- Important formulas, methodologies, frameworks (if present)
- Notable conclusions or findings
- Specific examples with concrete details

OUTPUT REQUIREMENTS:
- Be specific: Include numbers, dates, names, concrete details
- Focus on substance: Extract what matters, not background fluff
- Maintain objectivity: Present information, not opinions
- Preserve technical accuracy: Formulas, terms, methodologies must be exact

{FEW_SHOT_EXAMPLES}

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
- Extract main concepts, formulas, and examples from this excerpt
- Be specific and concrete (numbers, dates, names, data)
- Omit fields that are absent (no empty arrays)
- For formulas: include expression and brief explanation
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
    Focus: concept depth, formula completeness, examples, diagrams, pseudocode, practice problems
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
        formulas_with_examples = sum(1 for f in formulas if f.get("worked_example") or "example" in f.get("notes", "").lower())
        
        # Count new interactive features
        num_diagrams = len(s.get("diagrams", []))
        num_pseudocode = len(s.get("pseudocode", []))
        num_practice = len(s.get("practice_problems", []))
        
        # Calculate weighted score (depth + interactivity)
        concept_depth_score = min((avg_explanation_length / 400), 1.0)  # 400 chars = good depth
        example_richness_score = min(avg_examples_per_concept / 2.0, 1.0)  # 2 examples per concept = target
        formula_completeness_score = formulas_with_examples / max(num_formulas, 1) if num_formulas > 0 else 0.5
        diagrams_score = min(num_diagrams / 3, 1.0)  # 3 diagrams = target
        pseudocode_score = min(num_pseudocode / 2, 1.0)  # 2 pseudocode = target
        practice_score = min(num_practice / 4, 1.0)  # 4 practice problems = target
        
        score = (
            concept_depth_score * 0.25 +        # 25% for explanation depth
            example_richness_score * 0.20 +     # 20% for example richness
            formula_completeness_score * 0.15 + # 15% for formula completeness
            diagrams_score * 0.15 +             # 15% for visual diagrams
            pseudocode_score * 0.10 +           # 10% for pseudocode
            practice_score * 0.15               # 15% for practice problems
        )
        
        print(f"[QUALITY SCORE] Concepts: {num_concepts}, Avg explanation: {int(avg_explanation_length)} chars, "
              f"Avg examples/concept: {avg_examples_per_concept:.1f}, Formulas: {num_formulas} (examples: {formulas_with_examples}), "
              f"Diagrams: {num_diagrams}, Pseudocode: {num_pseudocode}, Practice: {num_practice}, Score: {score:.2f}")
        
        return round(score, 2)
    except Exception as e:
        print(f"[QUALITY SCORE] Error calculating: {e}")
        return 0.5  # Default to medium quality on error


def get_final_merge_prompt(language: str = "en", additional_instructions: str = "", domain: str = "general") -> str:
    """
    REDUCE phase: Synthesize all chunks into professional briefing document
    Focus on main themes, evidence, insights - NOT comprehensive tutorial
    """
    lang_instr = "Use TURKISH for ALL output." if language == "tr" else "Use ENGLISH for ALL output."
    additional = f"\n\nUSER REQUIREMENTS (FOLLOW STRICTLY):\n{additional_instructions}" if additional_instructions else ""

    # Domain-specific guidance
    domain_guidance = ""
    if domain == "technical":
        domain_guidance = "\n- For technical content: Include key formulas, methodologies, and quantitative evidence (numbers, benchmarks, metrics)."
    elif domain == "social":
        domain_guidance = "\n- For social/policy content: Include specific cases, dates, names, quotes, and empirical evidence."
    else:
        domain_guidance = "\n- Include concrete evidence: data points, specific examples, case studies as appropriate."

    return f"""🎯 PRIMARY GOAL
Create a comprehensive BRIEFING DOCUMENT that synthesizes the main themes and ideas from the material.

⚠️ CRITICAL: This is an EXECUTIVE BRIEFING, not a textbook or tutorial. Your audience:
- Needs rapid comprehension of key themes and conclusions
- Values evidence-based analysis over exhaustive explanation
- Expects synthesis and insight, not repetition
- Requires professional, objective, incisive presentation

LANGUAGE
{lang_instr}

BRIEFING STRUCTURE (MANDATORY):

1. **MAIN SECTIONS** (MINIMUM 6 sections)
   - Organize by major themes/topics
   - Create AT LEAST 6 sections (aim for 8-12 if material is rich)
   - Each theme = own section with clear heading
   - Within each section:
     • AT LEAST 2-3 concepts per section
     • Each concept: 150-250 words explanation
     • Core concept/finding
     • Supporting evidence (data, examples, specifics)
     • Analysis (what it means, implications)
   - Use bullet points for scannability
   - Include concrete details: numbers, dates, names, cases

🚨 CRITICAL BAYESIAN/PROBABILISTIC NETWORK RULE 🚨
IF the material involves Bayesian networks, Markov chains, probabilistic graphical models, or ANY network with probabilities:
→ EVERY edge in diagram MUST have probability/weight label
→ Example CORRECT: A[Rain] -->|P=0.8| B[Wet]
→ Example WRONG: A[Rain] --> B[Wet]  ❌ MISSING PROBABILITY!
→ This is NOT optional - it's REQUIRED for the diagram to be usable!

OUTPUT REQUIREMENTS:
- Specific and concrete: Include numbers, dates, names, data points
- Evidence-based: Ground claims in source material
- Comprehensive: Use available token budget fully (aim for max_output_cap)
- Don't be unnecessarily brief - depth matters
- Include pitfalls, when_to_use, limitations where applicable
- AT LEAST 2-4 diagrams (visualizations, flowcharts, trees):
  • If source contains charts/graphs/figures → Recreate EXACTLY with ALL details (values, numbers, labels, probabilities)
  • For Bayesian/probabilistic networks → MANDATORY: Include edge labels with probability values
    CORRECT: graph TD; A[Node1] -->|P=0.7| B[Node2]; A -->|P=0.3| C[Node3];
    WRONG: graph TD; A[Node1] --> B[Node2]; ❌ NO PROBABILITY = UNUSABLE!
  • For concepts that can be visualized → Create Mermaid diagrams
  • Use LaTeX in diagram labels if needed (e.g., -->|$P(A|B)=0.3$|)
  • Each diagram must have clear description explaining what it shows
- AT LEAST 2-3 pseudocode examples for algorithms/procedures
- AT LEAST 3-5 practice problems with VISUAL solutions:
  • If problem asks to "construct" or "draw" → solution MUST include actual diagram
  • If constructing Bayesian/probabilistic network → MUST include probability values on edges
- No vague generalities: "Increased 47%" not "grew significantly"{domain_guidance}{additional}

MINDSET CHECK:
"Does this briefing enable rapid comprehension of the material's key themes, evidence, and conclusions?"
"Would this satisfy a demanding executive or academic reviewer?"

If NO → Add specificity, evidence, and synthesis.

PLANNING (internal, before output):
1) Identify ALL main themes from all chunks
2) Create AT LEAST 6 sections (aim for 8-12 for rich material)
3) For each section: AT LEAST 2-3 concepts with depth
4) Create 2-4 diagrams:
   • FIRST: Check if source has charts/graphs/figures → Recreate EXACTLY with ALL details (values, labels, probabilities)
   • THEN: Create new diagrams for complex concepts (trees, flowcharts, hierarchies)
   • Use Mermaid syntax (graph TD, flowchart LR, etc.)
   • For Bayesian/probabilistic networks → Include edge labels with probability values (e.g., A -->|P=0.7| B)
   • For charts from source → Preserve ALL data points and values accurately
5) Create 2-3 pseudocode examples (for algorithms/procedures)
6) Create 3-5 practice problems with full solutions (varying difficulty)
7) Aim to use available token budget (you have 12,000-16,000 tokens available)
8) Include pitfalls, when_to_use, limitations when you have info
9) Omit fields only if genuinely no content (don't be lazy)

OUTPUT EXACTLY THIS JSON SCHEMA:
{{
  "summary": {{
    "title": "Study Notes: <topic>",
    "overview": "<2-4 sentences on scope and key topics covered>",
    "learning_objectives": [
      "Learning outcome 1",
      "Learning outcome 2"
    ],
    "sections": [
      {{
        "heading": "<Major Theme/Topic>",
        "concepts": [
          {{
            "term": "<Key concept/finding>",
            "definition": "<Concise definition or statement>",
            "explanation": "<Analysis with evidence: what it means, why it matters, implications. Include specific data, examples, cases. 2-3 focused paragraphs>",
            "key_points": ["<Bullet 1>", "<Bullet 2>"]
            
            // OPTIONAL FIELDS - Only include if you have content:
            // "example": "<Specific case study>",  ← Include if you have example
            // "pitfalls": ["<Common mistake>"],    ← Include if you have pitfalls
            // "when_to_use": ["<Condition>"],      ← Include if you have usage info
            // "limitations": ["<Constraint>"]      ← Include if you have limitations
            
            // NEVER write empty arrays like "when_to_use": []
            // Just don't include the field at all!
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "<formula / algorithm / method>",
        "expression": "<LaTeX MATHEMATICAL notation - e.g., f(x) = ax^2 + bx + c or \\prod_{{i=1}}^{{n}} P(x_i|parents(X_i))>",
        "variables": {{"symbol": "meaning (use LaTeX if needed: x_i, \\theta, etc.)"}},
        "worked_example": "<short numeric example with actual calculations, use LaTeX for math: $P(A,B,C) = P(A) \\cdot P(B|A) \\cdot P(C|B)$>",
        "pseudocode": "<OPTIONAL: if algorithm, put step-by-step procedure here>",
        "notes": "<when it applies, constraints, complexity>"
      }}
    ],
    "diagrams": [
      {{
        "title": "<Diagram title>",
        "description": "<What this diagram shows AND interpretation if from source file>",
        "content": "<Mermaid syntax (preferred) or ASCII art.
                    
                    🚨 CRITICAL FOR BAYESIAN/PROBABILISTIC NETWORKS:
                    EVERY edge MUST have probability label! Without it, diagram is UNUSABLE!
                    
                    CORRECT EXAMPLE (Bayesian Network):
                    graph TD
                      Cloudy[Cloudy] -->|P=0.8| Rain[Rain]
                      Cloudy -->|P=0.2| NoRain[No Rain]
                      Rain -->|P=0.9| Wet[Wet Grass]
                      NoRain -->|P=0.1| Wet
                    
                    WRONG EXAMPLE (MISSING PROBABILITIES - DO NOT DO THIS):
                    graph TD
                      Cloudy --> Rain
                      Rain --> Wet
                    ❌ This is UNUSABLE! Cannot calculate probabilities!
                    
                    Other Rules:
                    - If from source file → Copy ALL details accurately
                    - For charts from source → Preserve all data points and values>",
        "type": "tree|flowchart|graph|hierarchy|chart_from_source|bayesian_network",
        "source": "<OPTIONAL: 'original_file' if recreating a chart/graph from source, omit if new diagram>"
      }}
    ],
    "pseudocode": [
      {{
        "name": "<Algorithm/Procedure name>",
        "code": "<Step-by-step pseudocode with proper indentation>",
        "explanation": "<What it does, when to use, complexity>",
        "example_trace": "<Optional: trace through with example input>"
      }}
    ],
    "practice_problems": [
      {{
        "problem": "<Full problem statement>",
        "difficulty": "easy|medium|hard",
        "solution": "<Complete solution WITH VISUALS if applicable.
                     
                     🚨 IF PROBLEM ASKS TO CONSTRUCT BAYESIAN/PROBABILISTIC NETWORK:
                     Solution MUST include the diagram WITH probability values on edges!
                     
                     CORRECT:
                     graph TD
                       A[Cloudy] -->|P=0.8| B[Rain]
                       A -->|P=0.2| C[No Rain]
                       B -->|P=0.9| D[Wet Grass]
                     
                     WRONG:
                     graph TD
                       A[Cloudy] --> B[Rain] --> D[Wet Grass]
                     ❌ MISSING PROBABILITIES!
                     
                     For other construction problems: include actual diagram in Mermaid or ASCII art, not just instructions>",
        "steps": ["<Step 1>", "<Step 2>", "<Step 3>"],
        "key_concepts": ["<Concept 1>", "<Concept 2>"]
      }}
    ]
  }},
  "citations": [
    {{"file_id": "source", "section_or_heading": "<specific section/chapter>", "page_range": "<page numbers if available>", "evidence": "<max 200 chars snippet>"}}
  ]
}}

DEPTH & COMPREHENSIVENESS REQUIREMENTS:
✓ AT LEAST 6 sections (8-12 for rich material)
✓ AT LEAST 2-3 concepts per section
✓ Each concept explanation: 150-250 words
✓ Include examples where applicable (don't leave blank)
✓ Include pitfalls, when_to_use, limitations where you have information
✓ Diagrams: AT LEAST 2-4 visual representations:
  • If source has charts/graphs → Include them with interpretation
  • Create new diagrams for complex concepts (Mermaid syntax preferred)
  • 🚨 FOR BAYESIAN/PROBABILISTIC NETWORKS → EVERY edge MUST have probability label!
✓ Pseudocode: AT LEAST 2-3 algorithm examples (if applicable)
✓ Practice Problems: AT LEAST 3-5 with VISUAL solutions (if problem asks to construct/draw, solution must show the actual diagram)
✓ Use available token budget (12,000-16,000 tokens available)
✓ Don't be unnecessarily brief - fill the space with quality content

TOKEN OPTIMIZATION RULES (CRITICAL):
⚠️ NEVER include empty arrays! Omit the field entirely:
  
  ❌ BAD: "when_to_use": []        ← Wastes tokens!
  ✅ GOOD: (don't include the field at all)
  
  ❌ BAD: "limitations": []        ← Wastes tokens!
  ✅ GOOD: (don't include the field at all)
  
  ❌ BAD: "pitfalls": []           ← Wastes tokens!
  ✅ GOOD: (don't include the field at all)

OMIT these fields if empty:
  - "example" → omit if no example
  - "pitfalls" → omit if no pitfalls
  - "when_to_use" → omit if no usage conditions  
  - "limitations" → omit if no limitations
  - "formula_sheet" → omit if no formulas
  
But if you CAN add content, DO IT! Use the available tokens.

QUALITY & COMPLETENESS RULES:
- All major themes covered in dedicated sections (AT LEAST 6)
- Evidence-based: Include specific data, numbers, dates, names, cases
- Formula_sheet (if any in material): Include ALL formulas with:
  ✓ expression = MATH NOTATION
  ✓ variables = symbol meanings
  ✓ worked_example with calculations
  ✓ pseudocode for algorithms
- Validate JSON (no trailing commas, balanced braces)

VALIDATION CHECKLIST (before output):
✓ AT LEAST 6 sections created
✓ Each section has 2-3+ concepts
✓ Each concept: 150-250 word explanation
✓ Diagrams: 2-4+ visual representations:
  • Check source for charts/graphs/figures → Recreate with interpretation
  • Create new diagrams for complex concepts (use Mermaid syntax: graph TD, flowchart LR, etc.)
  • 🚨 IF BAYESIAN/PROBABILISTIC NETWORKS: Check EVERY edge has probability label (-->|P=0.7|)
✓ Pseudocode: 2-3+ algorithm examples (if applicable)
✓ Practice Problems: 3-5+ with VISUAL solutions:
  • If asking to "construct X" → solution must include actual Mermaid diagram of X
  • 🚨 IF CONSTRUCTING BAYESIAN NETWORK: Diagram MUST have probability values on ALL edges
✓ Claims are specific and concrete (not vague)
✓ Citations reference source material
✓ Used available token budget effectively (not unnecessarily brief)

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
- Diagrams: 2-4 visual representations (trees, flowcharts, hierarchies).
- Pseudocode: 2-3 algorithm examples (if applicable).
- Practice Problems: 3-5 with full solutions (varying difficulty).
- Provide citations for each main section and formula sheet.
- If the outline missed some themes, you MAY add concise sub-concepts, but avoid unnecessary padding.
- Output single valid JSON, no markdown.

{additional}"""


def get_no_files_prompt(topic: str, language: str = "en") -> str:
    """Prompt for generating summary without uploaded files"""
    lang_instr = "Generate in TURKISH." if language == "tr" else "Generate in ENGLISH."
    
    return f"""Create comprehensive study notes on this topic: {topic}

{lang_instr}

Use the same JSON structure as file-based summaries:
- Learning objectives
- Core concepts with extensive explanations (3-4 paragraphs) and multiple worked examples
- Formula sheet with derivations and worked examples (if applicable)
- Diagrams (2-4 visual representations)
- Pseudocode examples (2-3 if algorithms present)
- Practice problems (3-5 with full solutions)

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
    
    # Check new interactive features
    diagrams = summary.get("diagrams", [])
    pseudocode = summary.get("pseudocode", [])
    practice_problems = summary.get("practice_problems", [])
    
    if len(diagrams) < 2:
        issues.append(f"Diagrams too few ({len(diagrams)}), expected ≥2")
    if len(pseudocode) < 1:  # More lenient since not all topics have algorithms
        issues.append(f"Pseudocode examples missing or too few ({len(pseudocode)}), expected ≥1")
    if len(practice_problems) < 3:
        issues.append(f"Practice problems too few ({len(practice_problems)}), expected ≥3")
    
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

3) Interactive feature requirements:
   - Diagrams: Must have at least 2 visual representations (trees, flowcharts, hierarchies, graphs).
   - Pseudocode: Must have at least 1-2 algorithm examples (if applicable to the material).
   - Practice Problems: Must have at least 3 problems with full solutions and step-by-step explanations.

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
        temperature=0,
        user_id=user_id,
        endpoint="/summarize",
        db=db
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
    retry_on_length: bool = True,
    user_id: Optional[int] = None,
    endpoint: str = "/summarize",
    db = None
) -> str:
    """
    Call OpenAI API with given prompts and automatic retry on truncation
    Returns the response text
    Tracks token usage in database if db and user_id provided
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
        usage = result.get("usage", {})
        
        print(f"[OPENAI RESPONSE] Returned {len(content)} chars, finish_reason: {finish_reason}")
        
        # Track token usage in database (non-blocking)
        if db and endpoint and attempt == 1:  # Only track on first successful attempt
            try:
                from datetime import datetime
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                # Cost calculation (per 1M tokens)
                if "gpt-4o" in OPENAI_MODEL.lower():
                    input_cost_per_1m = 2.50  # $2.50 per 1M input tokens for gpt-4o
                    output_cost_per_1m = 10.00  # $10.00 per 1M output tokens for gpt-4o
                elif "gpt-4" in OPENAI_MODEL.lower():
                    input_cost_per_1m = 30.00  # $30 per 1M input tokens for gpt-4
                    output_cost_per_1m = 60.00  # $60 per 1M output tokens for gpt-4
                else:
                    input_cost_per_1m = 0.150  # $0.15 per 1M input tokens for gpt-4o-mini
                    output_cost_per_1m = 0.600  # $0.60 per 1M output tokens for gpt-4o-mini
                
                estimated_cost = (input_tokens / 1_000_000 * input_cost_per_1m) + (output_tokens / 1_000_000 * output_cost_per_1m)
                
                # Import here to avoid circular dependency
                from sqlalchemy import Column, Integer, String, Float, DateTime
                from sqlalchemy.ext.declarative import declarative_base
                
                # Use dynamic class creation to avoid import issues
                token_usage_record = type('TokenUsage', (), {
                    '__tablename__': 'token_usage',
                    'user_id': user_id,
                    'endpoint': endpoint,
                    'model': OPENAI_MODEL,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': total_tokens,
                    'estimated_cost': estimated_cost,
                    'created_at': datetime.utcnow()
                })
                
                # Try to execute raw SQL to avoid import issues
                db.execute(
                    """
                    INSERT INTO token_usage (user_id, endpoint, model, input_tokens, output_tokens, total_tokens, estimated_cost, created_at)
                    VALUES (:user_id, :endpoint, :model, :input_tokens, :output_tokens, :total_tokens, :estimated_cost, :created_at)
                    """,
                    {
                        "user_id": user_id,
                        "endpoint": endpoint,
                        "model": OPENAI_MODEL,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost": estimated_cost,
                        "created_at": datetime.utcnow()
                    }
                )
                db.commit()
                print(f"[TOKEN TRACKING] Recorded {total_tokens} tokens ({endpoint}) for user {user_id}")
            except Exception as e:
                # Don't fail the request if token tracking fails
                print(f"[TOKEN TRACKING ERROR] Failed to record token usage: {e}")
                try:
                    db.rollback()
                except:
                    pass
        
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
        max_output_tokens=out_budget,
        user_id=user_id,
        endpoint="/summarize",
        db=db
    )


def merge_summaries(
    chunk_summaries: List[str],
    language: str = "en",
    additional_instructions: str = "",
    out_budget: int = 14000,
    domain: str = "general",
    chunk_citations: List[Dict] = None,
    original_text: str = "",  # For coverage validation
    user_id: Optional[int] = None,
    db = None
) -> str:
    """
    Merge structured chunk JSONs into final exam-ready summary (REDUCE phase)
    Now receives structured mini-JSONs from MAP phase
    ENHANCED: Includes coverage validation to ensure no topics are skipped
    Returns final JSON string
    """
    import json
    from app.utils.coverage_validator import validate_coverage, generate_coverage_report
    
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
        
        # COVERAGE VALIDATION: Check if all topics are covered
        if original_text:
            print("[COVERAGE] Validating topic coverage...")
            coverage_result = validate_coverage(original_text, result, min_coverage=0.85)
            print(generate_coverage_report(coverage_result))
            
            # If coverage is insufficient, add missing topics and regenerate
            if not coverage_result['passed'] and coverage_result['missing_topics']:
                print(f"[COVERAGE] ⚠️  Coverage insufficient ({coverage_result['coverage_score']:.1%})")
                print(f"[COVERAGE] Adding {len(coverage_result['missing_topics'])} missing topics...")
                
                # Create enhanced instructions with missing topics
                missing_topics_str = ", ".join(coverage_result['missing_topics'][:10])
                coverage_instructions = f"\n\n⚠️  CRITICAL: The following topics MUST be included but are currently missing: {missing_topics_str}"
                if len(coverage_result['missing_topics']) > 10:
                    coverage_instructions += f" (and {len(coverage_result['missing_topics']) - 10} more)"
                coverage_instructions += "\n\nAdd these topics as new sections or integrate them into existing relevant sections. DO NOT skip any of them."
                
                # Regenerate with coverage fix (one retry only)
                enhanced_instructions = (additional_instructions or "") + coverage_instructions
                print("[COVERAGE] Regenerating with missing topics...")
                result = reduce_two_stage(
                    aggregated_knowledge=aggregated_knowledge,
                    language=language,
                    domain=domain,
                    out_cap=out_budget,
                    additional_instructions=enhanced_instructions
                )
                print("[COVERAGE] ✓ Regeneration complete")
                
                # Re-validate after regeneration
                coverage_result = validate_coverage(original_text, result, min_coverage=0.85)
                print(f"[COVERAGE] Post-regen coverage: {coverage_result['coverage_score']:.1%}")
            else:
                print(f"[COVERAGE] ✅ Coverage validated ({coverage_result['coverage_score']:.1%})")
            
            # Add coverage info to result for frontend display (ALWAYS, even if 100% coverage)
            # CRITICAL: result is a JSON string, need to parse it first!
            try:
                result_dict = json.loads(result) if isinstance(result, str) else result
                result_dict['coverage'] = {
                    'score': round(coverage_result['coverage_score'], 2),
                    'missing_topics': coverage_result['missing_topics'][:20]  # Limit to 20 for display
                }
                result = json.dumps(result_dict, ensure_ascii=False, indent=2)
                print(f"[COVERAGE] ✅ Coverage added to JSON: {coverage_result['coverage_score']:.1%} score, {len(coverage_result['missing_topics'])} missing topics")
            except Exception as e:
                print(f"[COVERAGE] ⚠️  Failed to add coverage info: {e}")
        
        # Return as JSON string (for compatibility with existing pipeline)
        return json.dumps(result, ensure_ascii=False, indent=2) if not isinstance(result, str) else result
    
    except Exception as e:
        print(f"[REDUCE TWO-STAGE FALLBACK] Error in two-stage REDUCE: {e}")
        print("[REDUCE TWO-STAGE FALLBACK] Falling back to single-stage REDUCE...")
        
        # Fallback: single-stage REDUCE (original implementation)
        user_prompt = get_final_merge_prompt(language, additional_instructions, domain)
        user_prompt += f"\n\nSTRUCTURED SOURCE KNOWLEDGE (from {len(chunk_summaries)} chunks):\n{json.dumps(aggregated_knowledge, indent=2, ensure_ascii=False)}"
        
        return call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_output_tokens=out_budget,
            user_id=user_id,
            endpoint="/summarize",
            db=db
        )


def map_reduce_summary(
    full_text: str,
    language: str = "en",
    additional_instructions: str = "",
    out_cap: int = 12000,
    force_chunking: bool = False,
    user_id: Optional[int] = None,
    db = None
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
        user_id: User ID for token tracking
        db: Database session for token tracking
    
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
    
    # 4. REDUCE: Merge into final JSON with citation tracking and coverage validation
    print(f"[MAP-REDUCE] Merging {len(chunk_summaries)} summaries with domain: {domain}...")
    final_summary = merge_summaries(
        chunk_summaries,
        language=language,
        additional_instructions=enhanced_instructions,
        out_budget=min(out_cap, MERGE_OUTPUT_BUDGET[1]),
        domain=domain,
        chunk_citations=chunk_citations,
        original_text=full_text  # Pass original text for coverage validation
    )
    
    print("[MAP-REDUCE] Complete!")
    return final_summary




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

