"""
AI-powered summary service with map-reduce for large documents
Includes domain detection and quality guardrails for consistent output
Enhanced with deep learning prompts for maximum depth and coverage
"""
from typing import List, Optional, Dict
import os
import requests
import re
import time
import json
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

# CRITICAL FIX: Stage-specific system prompts to prevent JSON corruption
# MAP/OUTLINE need ultra-minimal prompts, FILL needs deep prompt

MAP_SYSTEM_PROMPT = """You are an expert educator extracting and expanding conceptual content from document chunks.

YOUR ROLE IN MAP PHASE:
- Extract ALL key concepts, definitions, and explanations
- EXPAND ideas with additional context and clarification
- Add missing explanations that would help students understand
- Write in clear, teaching-oriented prose
- Add examples and real-world context
- Clarify technical terms and their relationships

CRITICAL RULES:
- Output PLAIN TEXT only (NO JSON, NO structured format)
- Write as continuous prose with natural paragraphs
- Use a teaching tone (explain WHY and HOW, not just WHAT)
- Minimum 1200-2000 words per chunk
- Be comprehensive - cover ALL content in the chunk
- DO NOT compress - EXPAND for deeper understanding
- Add context from domain knowledge when helpful
- Make connections between concepts explicit

FORMAT:
Write naturally flowing explanatory text. Use paragraphs.
You may use simple lists within prose if natural, but no rigid structure."""

OUTLINE_SYSTEM_PROMPT = """
You generate a STRICT JSON OUTLINE for a study guide.

OUTPUT RULES (EXTREMELY IMPORTANT):
- Output ONLY valid JSON. No markdown. No explanations.
- NEVER output prose outside JSON brackets.
- The JSON structure MUST be exactly:

{
  "title": "<Extracted or generic topic>",
  "sections": [
    {
      "heading": "<Real theme heading>",
      "concepts": []
    }
  ]
}

SECTION RULES:
- MINIMUM 10 sections.
- SOFT MAXIMUM 18 sections.
- IDEAL RANGE: 12–16 sections.
- Section headings MUST come from:
    • heading_path metadata (MAP stage)
    • or major themes inferred from it.
- NEVER invent fake headings like "Section 1".
- NEVER group multiple themes into one section.
- NEVER output empty or placeholder headings.

COVERAGE REQUIREMENTS:
- Every UNIQUE top-level heading_path MUST produce a section.
- If MAP produced 14 top-level headings → You MUST output 14 sections.
- If MAP produced <10 themes → Expand by splitting large themes into sub-themes.
- ZERO themes may be dropped.

QUALITY:
- Section headings must be meaningful, short, and descriptive.
- Do NOT fill concepts; keep concepts=[] only.

STRICTNESS:
- If you are unsure, ALWAYS err toward producing MORE sections (never fewer).
- Missing sections = INVALID OUTPUT.

Return ONLY the JSON object.
"""





FILL_SYSTEM_PROMPT = """You fill an outline into FULL STUDY NOTES.

OUTPUT FORMAT:
{
  "summary": {
    "title": "...",
    "overview": "...",
    "learning_objectives": [],
    "sections": [
      {
        "heading": "...",
        "concepts": [
          {
            "term": "...",
            "definition": "...",
            "explanation": "...",
            "example": "...",
            "key_points": []
          }
        ]
      }
    ],
    "formula_sheet": [],
    "diagrams": [],
    "pseudocode": [],
    "practice_problems": []
  }
}

RULES:
- Follow the EXACT section order from the outline.
- For each section, attach ALL concepts whose
  concept._source.heading_path matches that section heading.
- If needed, fuzzy match: lowercase + prefix match.
- Minimum total length: 32000 characters (NOT tokens - more predictable)
- Ideal target: 40000-56000 characters (use 70-95% of available budget)
- No content outside JSON

🚨 CRITICAL EXPANSION RULES:
- DO NOT compress content
- Use the ENTIRE max_tokens budget available
- Expand each concept with MINIMUM 3 examples
- Expand each formula with MINIMUM 2 worked examples
- Expand each section with 5-10 sentences of explanation
- If output feels short, EXPAND MORE - never stop early
- Better to be comprehensive than brief
"""



# Deep prompt only for single-pass summaries (not used in two-stage reduce)
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
    REDUCE phase: Synthesize all chunks into EXAM-READY STUDY NOTES.
    Student should be able to prepare for an exam using only this output.
    """
    lang_instr = "Use TURKISH for ALL output." if language == "tr" else "Use ENGLISH for ALL output."
    additional = f"\n\nUSER REQUIREMENTS (FOLLOW STRICTLY):\n{additional_instructions}" if additional_instructions else ""

    domain_guidance = ""
    if domain == "technical":
        domain_guidance = "\n- For technical content: include ALL major definitions, theorems, formulas and algorithms with worked examples."
    elif domain == "social":
        domain_guidance = "\n- For social/policy content: include key theories, schools of thought, important names, dates, cases and empirical evidence."
    elif domain == "procedural":
        domain_guidance = "\n- For procedural content: include clear step-by-step procedures, workflows, edge cases and common pitfalls."
    else:
        domain_guidance = "\n- Always include concrete examples, real contexts and practical applications."

    return f"""🎯 PRIMARY GOAL
Create a FULL, EXAM-READY STUDY GUIDE from the material.

The reader should be able to:
- Learn (or refresh) the entire topic from scratch
- Understand all key ideas, not just headlines
- See worked examples and practice problems
- Sit an exam using only these notes

LANGUAGE
{lang_instr}

OVERALL STYLE:
- Think like a professor writing complete lecture notes.
- PRIORITIZE DEPTH and COVERAGE over brevity.
- It is OK if the output is long, as long as it is dense and useful.
- Avoid repetition of identical sentences, but DO explain ideas from multiple angles.

STRUCTURE (REQUIRED):

1. **OVERVIEW**
   - 2–4 sentences summarizing what the whole material is about.
   - Mention the main themes / chapters.

2. **LEARNING OBJECTIVES**
   - 4–8 clear objectives, starting with verbs:
     • "Define...", "Explain...", "Compare...", "Apply...", "Prove...", "Solve..."

3. **MAIN SECTIONS**
   - Organize by major themes/topics of the material.
   - Create as many sections as needed to cover EVERYTHING (no fixed number).
   - Each section MUST contain:
     • A clear heading
     • 3–6 key concepts
     • For each concept:
       - A precise definition
       - 2–4 dense paragraphs of explanation
       - At least ONE concrete example
       - Key points / bullet summary at the end
   - Emphasize:
     • When the concept is used
     • Why it matters
     • How it connects to other concepts in this document

4. **FORMULAS / ALGORITHMS (if present in material)**
   - For each important formula/algorithm:
     • name
     • expression in LaTeX
     • variables with meanings
     • one worked example with real numbers
     • notes on validity, limitations, complexity

5. **DIAGRAMS (ONLY if they help understanding)**
   - Use Mermaid or clear ASCII art ONLY for structures that are naturally visual:
     • trees, graphs, pipelines, process flows, hierarchies
   - Do NOT invent random diagrams if text explanation is clearer.
   - For each diagram: title, short description, and the diagram content.

6. **PSEUDOCODE (when relevant)**
   - 2–4 key algorithms or procedures in simple pseudocode.
   - Each: name, code, explanation, small example trace.

7. **PRACTICE PROBLEMS**
   - 5–10 problems of mixed difficulty (easy/medium/hard).
   - For each:
     • full problem statement
     • difficulty
     • step-by-step solution
     • highlight key concepts used.

COVERAGE RULES:
- EVERY major topic from the material must appear in at least one section.
- Minor topics can be grouped under "Additional notes" subsections.
- If something appears many times in the source, summarize it once but deeply.
- Do NOT skip important topics just to be brief.

TOKEN / LENGTH GUIDANCE:
- Use as MUCH of the available output budget as needed.
- Aim to fill roughly 70–90% of the allowed max tokens.
- Do NOT deliberately stop early if there are still uncovered topics or missing examples.

OUTPUT FORMAT:
Return EXACTLY this JSON structure:

{{
  "summary": {{
    "title": "Study Notes: <topic>",
    "overview": "<2–4 sentence high-level overview>",
    "learning_objectives": [
      "Objective 1",
      "Objective 2"
    ],
    "sections": [
      {{
        "heading": "<Section heading>",
        "concepts": [
          {{
            "term": "<Key concept>",
            "definition": "<Short, precise definition>",
            "explanation": "<2–4 paragraphs of detailed explanation>",
            "example": "<Concrete example (numeric or real-world)>",
            "key_points": ["<Bullet summary>", "<Bullet summary>"]
            // Optional fields:
            // "pitfalls": [...],
            // "when_to_use": [...],
            // "limitations": [...]
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "<Formula or algorithm>",
        "expression": "<LaTeX expression, wrapped in \\( \\)>",
        "variables": {{ "x": "meaning of x" }},
        "worked_example": "<Step-by-step numeric example>",
        "pseudocode": "<Optional pseudocode if algorithmic>",
        "notes": "<Constraints, complexity, usage hints>"
      }}
    ],
    "diagrams": [
      {{
        "title": "<Diagram title>",
        "description": "<What it shows and why it matters>",
        "content": "<Mermaid or ASCII>",
        "type": "tree|flowchart|graph|hierarchy|other"
      }}
    ],
    "pseudocode": [
      {{
        "name": "<Algorithm name>",
        "code": "<Pseudocode>",
        "explanation": "<What it does, when to use>",
        "example_trace": "<Example input → output trace>"
      }}
    ],
    "practice_problems": [
      {{
        "problem": "<Full statement>",
        "difficulty": "easy|medium|hard",
        "solution": "<Detailed step-by-step solution>",
        "steps": ["<Step 1>", "<Step 2>"],
        "key_concepts": ["<Concept>", "<Concept>"]
      }}
    ]
  }},
  "citations": [
    {{
      "file_id": "source",
      "section_or_heading": "<where in the source>",
      "page_range": "<pages if known>",
      "evidence": "<short snippet from source>"
    }}
  ]
}}

{domain_guidance}{additional}

Before you answer, think about:
- "Can a student reasonably prepare for an exam using ONLY this output?"
If not, ADD more explanations, examples and practice problems BEFORE finishing.

OUTPUT PURE JSON NOW (no other text):"""


def get_reduce_outline_prompt(language: str, domain: str) -> str:
    L = "Use TURKISH." if language == "tr" else "Use ENGLISH."

    return f"""
You are generating an OUTLINE for a full study guide.

{L}

STRUCTURE (STRICT):
Return ONLY this JSON structure:

{{
  "title": "Generated Outline",
  "sections": [
    {{
      "heading": "Topic heading",
      "concepts": []
    }}
  ]
}}

RULES:
- 10–18 sections total
- Each section heading MUST be based on:
    • heading_path (from MAP stage)
    • top-level themes extracted from _source.heading
- Section titles MUST be descriptive phrases (not “Section 1”)
- Do NOT write explanations or definitions
- Do NOT add content, only headings
"""




def get_reduce_fill_prompt(language: str, additional_instructions: str, domain: str):
    """
    Fill stage prompt — ensures deep, exam-ready content with maximum token usage.
    """

    return f"""
You are an elite academic tutor generating FINAL STUDY NOTES.

STAGE = FILL (CONTENT EXPANSION)
Your task:
- Expand EACH section from the outline into a fully detailed, exam-ready explanation.
- Use ALL available space (target 8,000–14,000 tokens if possible).
- Never shorten explanations unnecessarily.
- Never stop early.
- Never leave a section shallow.

===========================
ABSOLUTE RULES (CRITICAL)
===========================

1) **JSON ONLY**
   Output MUST be valid JSON.
   Do NOT add commentary before or after.

2) **LENGTH REQUIREMENTS** (CHARACTER-BASED - MORE PREDICTABLE)
   - TOTAL output: **minimum 32,000 characters** (target 40k-56k chars)
   - Each section: **minimum 1,600 characters**, may exceed 4,800+
   - Depth > brevity. If unsure, write more.
   
   🚨 IMPORTANT: DO NOT compress content.
   🚨 Use the ENTIRE max_tokens budget.
   🚨 Expand each concept with MINIMUM 3 examples.
   🚨 Expand each formula with MINIMUM 2 worked examples.
   🚨 Expand each section with 5–10 sentences.

3) **DEPTH REQUIREMENTS**
   For EVERY concept, include:
   - Clear definition (100+ chars)
   - Long-form explanation (800+ characters, multiple paragraphs)
   - MINIMUM 3 real-world examples (each 150+ chars)
   - Edge cases and limitations
   - Common pitfalls and mistakes
   - When to use / when not to use
   - Step-by-step reasoning or workflow
   - Mini-scenario or analogy when appropriate

4) **DOMAIN-ADAPTIVE DEPTH**
   Domain is: {domain}
   - If technical → include detailed reasoning with multiple examples
   - If math → include MINIMUM 2–3 worked examples per formula
   - If CS → include pseudocode + flow + complexity analysis
   - If social sciences → include theory comparison + historical examples
   - If business/econ → include frameworks + multiple case examples

5) **USE ALL AVAILABLE TOKENS - NEVER STOP EARLY**
   🔥 Maximize detail, examples, explanations.
   🔥 Never conclude early - keep writing until budget is exhausted.
   🔥 If a section feels short, ADD MORE examples and explanations.
   🔥 Better to exceed than to fall short.

6) **STRICT ALIGNMENT WITH OUTLINE**
   - Do NOT add new sections.
   - Do NOT remove sections.
   - All final JSON must follow EXACT structure of outline.

7) **SELF-REPAIR MODE**
   - If a concept seems under-explained (<250 tokens), automatically expand it.
   - If a formula lacks examples, add more.
   - If a section is shorter than others, expand to match depth.
   - Keep self-repair reasonable (academic-level, not “write a textbook”).

8) **NO FLUFF**
   - Never say “this is important.”
   - Never list topics without explaining.
   - Every sentence must add knowledge.

===========================
OUTPUT FORMAT
===========================

Return ONLY:

{{
  "summary": {{
     "title": "...",
     "overview": "...",
     "learning_objectives": [...],
     "sections": [...]
  }}
}}

No analysis, no markdown.
"""




def get_no_files_prompt(topic: str, language: str = "en") -> str:
    """Prompt for generating summary without uploaded files - from general knowledge"""
    lang_instr = "Generate in TURKISH." if language == "tr" else "Generate in ENGLISH."
    
    return f"""You are creating comprehensive study notes on: "{topic}"

{lang_instr}

🎯 YOUR TASK: Generate a complete, detailed study guide based on your knowledge of this topic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL REQUIREMENTS (NO-FILES MODE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Since no files were uploaded, you MUST generate ACTUAL CONTENT from your knowledge base:

1. **REAL CONTENT REQUIRED:**
   - ❌ NO placeholders like "Concept 1", "Concept 2", "Section 1"
   - ✅ ACTUAL topic-specific information with real names, dates, facts
   - ✅ Real examples, real data, real explanations
   - ✅ If you don't have deep knowledge → focus on core fundamentals + applications

2. **STRUCTURE (same as file-based):**
   - MINIMUM 10-15 sections covering main aspects of the topic
   - Each section: 3-5 detailed concepts (250-400 words each)
   - Learning objectives: 3-5 specific, measurable outcomes
   - Formula sheet: Include key formulas/equations (if applicable to topic)
   - Diagrams: 1-3 diagrams ONLY if helpful (hierarchies, processes, relationships)
   - Pseudocode: 2-3 examples (ONLY for algorithmic/programming topics)
   - Practice problems: 4-6 with detailed step-by-step solutions

3. **DEPTH & QUALITY:**
   - Each concept: definition + detailed explanation + 2-3 real examples + applications
   - Include: history, key figures, methodologies, best practices, common pitfalls
   - Real-world context: Where is this used? Why does it matter?
   - Practical demonstrations with concrete examples

4. **OUTPUT LENGTH:**
   - 🚨 MINIMUM 6,000 tokens output (CRITICAL!)
   - Target: 9,000-12,000 tokens (use 70-90% of available budget)
   - If you're under 6,000 tokens → You're being TOO BRIEF - EXPAND!
   - Each concept should be 300-500 words (not 100-150!)
   - Expand explanations, add more examples, include more details
   - This should be a COMPREHENSIVE study guide, not a quick overview

5. **TOPIC-SPECIFIC APPROACH:**
   For "{topic}":
   - Identify main themes/categories within this topic
   - Cover fundamentals + advanced concepts
   - Include practical applications and real-world examples
   - Add historical context if relevant
   - Discuss current state and future directions (if applicable)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use EXACT JSON format from system prompt (with all required fields: title, overview, learning_objectives, sections with concepts, formula_sheet, diagrams, pseudocode, practice_problems, citations).

🚨 VALIDATION: Before output, check:
✓ NO placeholder text (all content is topic-specific)
✓ 10-15+ sections created
✓ Each concept has 300-500 words (not 100-150!)
✓ Real examples included (2-3 per concept)
✓ Output is 6,000+ tokens (aim for 9,000-12,000)

🚨 REMEMBER: Generate REAL CONTENT about "{topic}", NOT placeholders!"""


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
    NEW LOGIC:
    - Section count MUST EQUAL number of top-level headings
    - Allow +2 buffer for small theme expansions
    """
    theme_heads = infer_theme_heads(aggregated_knowledge)
    theme_count = max(1, len(theme_heads))

    # We ALWAYS want a large outline to allow deep final output
    target_min = 10
    target_soft_max = 18

    return target_min, target_soft_max, theme_count


def coverage_gaps(outline: dict, aggregated_knowledge: dict) -> list:
    """
    Detect missing themes: present in source but not in outline
    """
    planned = {(sec.get("heading") or "").strip() for sec in outline.get("sections", [])}
    source_tops = set(infer_theme_heads(aggregated_knowledge))
    return [h for h in source_tops if h and all(h.lower() not in p.lower() for p in planned)]


def validate_reduce_output(result: dict, out_cap: int | None = None) -> list:
    """
    Validate the merged summary with SOFT, PLAN-ADAPTIVE checks.
    This no longer enforces an impossible fixed 10000-token minimum.
    Instead:
      - Minimum tokens = max(2500, out_cap * 0.6), capped at 9000.
      - If below target → trigger expansion via self-repair.
    Returns list of issue strings (empty if all good)
    """
    import re
    issues = []
    # Allow both top-level or wrapped summaries
    summary = result.get("summary")
    if summary is None:
        # auto-wrap
        summary = result
        result = {"summary": result}

    
    # Check sections
    sections = summary.get("sections", [])
    # Allow flexible section count - do not enforce minimum
    if len(sections) == 0:
        issues.append("No sections produced — JSON invalid.")
    
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
        if not has_citation and i < 3:
            print(f"[CITATION] Warning: Section '{section_heading}' missing citation")
            # NO issues.append !!!
            continue

    
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
    
    # Validate diagram probability values for Bayesian/probabilistic networks
    for idx, diagram in enumerate(diagrams):
        diagram_type = diagram.get("type", "").lower()
        diagram_title = diagram.get("title", f"Diagram {idx+1}").lower()
        diagram_content = diagram.get("content", "")
        
        # Check if this is a probabilistic diagram
        is_probabilistic = any(keyword in diagram_title or keyword in diagram_type or keyword in diagram_content.lower()
                              for keyword in ["bayesian", "probabilistic", "markov", "probability", "network", "chain"])
        
        if is_probabilistic and "-->" in diagram_content:
            # Count edges (connections)
            edge_count = diagram_content.count("-->")
            # Count probability labels (P=, P(, probability values)
            prob_label_count = diagram_content.count("|P=") + diagram_content.count("|P(") + diagram_content.count("|$P")
            
            if prob_label_count < edge_count:
                missing = edge_count - prob_label_count
                issues.append(f"⚠️ CRITICAL: Diagram '{diagram.get('title', 'Untitled')}' is a probabilistic network with {edge_count} edges but only {prob_label_count} probability labels! Missing {missing} probability values. EVERY edge MUST have a probability label (e.g., -->|P=0.7|)!")
    
    # Pseudocode: Only for algorithmic content
    # (No minimum check - not all content needs pseudocode)
    
    # Practice problems: Should have adequate examples
    if len(practice_problems) < 2:
        issues.append(f"Practice problems too few ({len(practice_problems)}), expected ≥2")
    
    # ---- LENGTH CHECK (ADAPTIVE, PLAN-BASED) ----
    import json
    result_json = json.dumps(result, ensure_ascii=False)
    estimated_tokens = len(result_json) // 4  # ≈ 4 chars per token

    # LENGTH CHECK: Character-based (more predictable than tokens)
    min_chars = 32000   # <- Minimum acceptable length (characters)
    target_min_chars = 40000  # <- Target minimum (better quality)
    target_max_chars = 56000  # <- Ideal comprehensive output
    
    # Estimate characters from JSON
    estimated_chars = len(result_json)

    if estimated_chars < min_chars:
        issues.append(f"Output too short ({estimated_chars} chars, ~{estimated_tokens} tokens). MUST be >= {min_chars} chars.")
    elif estimated_chars < target_min_chars:
        issues.append(f"Output below target range ({estimated_chars} chars, ~{estimated_tokens} tokens). Should be >= {target_min_chars} chars.")
        

    
    return issues


def build_self_repair_prompt(result: dict, issues: list, language: str) -> str:
    """
    Soft self-repair:
    - Küçük eksikleri düzelt
    - Belgeyi baştan yazma
    - 4000 token'ı geçme
    """
    import json
    lang = "Use TURKISH." if language == "tr" else "Use ENGLISH."
    issues_text = "\n- ".join(issues)
    
    return f"""{lang}
You are repairing an existing study-guide JSON.

GOAL:
Fix ONLY the issues listed below. Do NOT rewrite or heavily expand the document.

ALLOWED FIXES:
- Add missing examples (1 per concept if required)
- Add missing citations
- Add missing key_points
- Add a short numeric example for formulas that require it
- Slightly extend very short explanations (2–3 sentences max)
- Fix invalid JSON structure

NOT ALLOWED:
- Do NOT create new sections
- Do NOT rename or remove existing sections/concepts
- Do NOT significantly increase total length
- Do NOT exceed 4000 tokens in this repair step

ISSUES TO FIX:
- {issues_text}

Return a SINGLE valid JSON with the improved version.
CURRENT JSON:
{json.dumps(result, ensure_ascii=False)}"""



# ========== Two-Stage REDUCE Orchestrator ==========

# ========== Supportive functions first ==========
def safe_parse_outline(raw: str):
    """
    SAFE JSON PARSER v3 — NEVER truncate valid JSON.
    Tries several strategies:
    1. Direct JSON parse
    2. Extract largest JSON object using a bracket counter
    3. Last-resort fallback: return {"summary": {}, "sections": []}
    """

    import json

    if not raw or not isinstance(raw, str):
        return {"title": "Invalid", "sections": []}

    # 1. Direct parse
    try:
        return json.loads(raw)
    except:
        pass

    # 2. Extract the largest {...} block using bracket stack
    start = None
    depth = 0
    best_block = ""

    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                candidate = raw[start:i+1]
                if len(candidate) > len(best_block):
                    best_block = candidate

    if best_block:
        try:
            return json.loads(best_block)
        except:
            pass

    # 3. ABSOLUTE LAST RESORT (never crash)
    return {
        "title": "Fallback Outline",
        "sections": []
    }


def detect_heading_from_text(chunk: str) -> str:
    # Look for lines that look like headings
    lines = chunk.split("\n")
    for line in lines:
        if len(line) < 80 and line.strip().istitle():
            return line.strip()
    return "General Topic"





def reduce_two_stage(
    aggregated_knowledge: dict,
    language: str,
    domain: str,
    out_cap: int,
    additional_instructions: str = "",
    user_id: Optional[int] = None,
    db = None
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
        + "\n\nIMPORTANT:\n"
        + "Use _source.heading_path metadata to generate SECTIONS.\n"
        + "Each section MUST correspond to major themes extracted from heading_path.\n"
        + "Do NOT invent new themes.\n"
    )
    
    outline_max = max(3000, int(out_cap * 0.30))  # 12k → 3600 minimum → 3600
    
    outline_json = call_openai(
        system_prompt=OUTLINE_SYSTEM_PROMPT,  # SHORT, JSON-focused prompt
        user_prompt=outline_user,
        max_output_tokens = outline_max,
        temperature=0,
        user_id=user_id,
        endpoint="/summarize",
        db=db
    )
    outline = safe_parse_outline(outline_json)

    
    # Compute dynamic targets
    target_min, target_soft_max, approx_themes = compute_outline_targets(
        aggregated_knowledge=aggregated_knowledge,
        out_cap=out_cap,
        domain=domain
    )
    print(f"[REDUCE] Outline targets: min={target_min}, soft_max={target_soft_max}, themes={approx_themes}")

    # === EXTRACT ALL MAP HEADINGS ===
    source_themes = set()
    
    for c in aggregated_knowledge.get("concepts", []):
        if "_source" in c and "heading_path" in c["_source"]:
            source_themes.add(c["_source"]["heading_path"])
    
    for f in aggregated_knowledge.get("formulas", []):
        if "_source" in f and "heading_path" in f["_source"]:
            source_themes.add(f["_source"]["heading_path"])
    
    for t in aggregated_knowledge.get("theorems", []):
        if "_source" in t and "heading_path" in t["_source"]:
            source_themes.add(t["_source"]["heading_path"])
    
    # NOW update outline targets
    map_heading_count = len(source_themes)
    target_min = max(target_min, map_heading_count)
    target_soft_max = max(target_soft_max, map_heading_count)

    # Check 1b: Missing MAP themes (always check!)
    
    # === SELF-REPAIR: Max 1 repair attempt to prevent loop ===
    outline_needs_repair = False
    repair_reason = []
    
    # Check 1: Too shallow?
    current_sections = len(outline.get("sections", []))
    if current_sections < target_min:
        outline_needs_repair = True
        repair_reason.append(
            f"too shallow ({current_sections} < {target_min}) — MUST MATCH major themes"
        )
    
    
    
    outline_themes = {sec.get("heading","") for sec in outline.get("sections", [])}
    
    missing_themes = [t for t in source_themes if t not in outline_themes]
    
    if missing_themes:
        outline_needs_repair = True
        repair_reason.append(f"missing MAP themes: {missing_themes[:5]}")
    
    
    # Single repair attempt (prevents loop)
    if outline_needs_repair:
        print(f"[REDUCE] Outline repair needed: {'; '.join(repair_reason)}")
        outline_user += (
            f"\n\n[REPAIR] You MUST produce EXACTLY {target_min}–{target_soft_max} sections.\n"
            f"One section per major heading. Do NOT merge themes. Do NOT delete themes.\n"
            f"Expand outline to match the exact theme count from source.\n"
            f"Fix issues: {'; '.join(repair_reason)}."
        )

        outline_json = call_openai(
            system_prompt=OUTLINE_SYSTEM_PROMPT,  # SHORT, JSON-focused
            user_prompt=outline_user,
            max_output_tokens=6000,
            temperature=0,
            user_id=user_id,
            endpoint="/summarize",
            db=db
        )
        outline = safe_parse_outline(outline_json)
        # Normalize section headings
        for sec in outline.get("sections", []):
            if not isinstance(sec.get("heading"), str) or not sec.get("heading").strip():
                sec["heading"] = "General Topic"

        print(f"[REDUCE] Outline repaired: {len(outline.get('sections', []))} sections")
    else:
        print(f"[REDUCE] Outline OK: {len(outline.get('sections', []))} sections")
    
    # === STAGE 2: Fill Outline ===
    print("[REDUCE] Stage 2: Filling outline with content...")
    agg_trim = agg_str[:min(len(agg_str), 120000)]
    fill_prompt = get_reduce_fill_prompt(language, domain, additional_instructions)
    fill_prompt += """
    MATCHING RULE (CRITICAL):
    For every concept from aggregated_knowledge.concepts:
    - Read concept._source.heading_path
    - Compare to section headings in the OUTLINE
    - Normalize both: lowercase + strip
    - If heading_path starts with section heading → attach concept to that section
    - If no direct match, attach to the closest semantically similar heading
    """

    fill_user = (
        fill_prompt
        + "\n\nOUTLINE (DO NOT CHANGE ORDER):\n"
        + json.dumps(outline, ensure_ascii=False, indent=2)
        + "\n\nSTRUCTURED SOURCE KNOWLEDGE:\n"
        + agg_trim
        + "\n\n🚨 CRITICAL REQUIREMENTS (NON-NEGOTIABLE):\n"
        + "1. Cover 100% of the content from structured knowledge\n"
        + "2. Use ALL available tokens (min 40,000 characters output)\n"
        + "3. MINIMUM per section: 1,600 characters\n"
        + "4. MINIMUM per concept: 3 examples (each 150+ chars)\n"
        + "5. MINIMUM per formula: 2 worked examples with step-by-step calculations\n"
        + "6. Create 5-10 practice problems with detailed solutions\n"
        + "7. Add diagrams (textual/Mermaid) where concepts are visual\n"
        + "8. Add pseudocode for algorithmic content\n"
        + "9. DO NOT compress - expand everything to maximum depth\n"
        + "10. Use 80-95% of token budget - DO NOT stop early\n"
    )
    time.sleep(2.0) 
    fill_max = 14000  # Maximum tokens allowed
    filled_json = call_openai(
        system_prompt=FILL_SYSTEM_PROMPT,  # MODERATE, structure-focused prompt
        user_prompt=fill_user,
        max_output_tokens = fill_max,
        temperature=0,
        user_id=user_id,
        endpoint="/summarize",
        db=db
    )
    result = safe_parse_outline(filled_json)
    
    # === STAGE 3: Validate & Self-Repair ===
    print("[REDUCE] Stage 3: Validating output...")
    issues = validate_reduce_output(result, out_cap=out_cap)
    if issues:
        print(f"[REDUCE] Quality issues detected: {issues}")
        repair_user = (
            build_self_repair_prompt(result, issues, language)
            + "\n\nFIX INSTRUCTIONS (SOFT):\n"
              "- Focus only on the listed issues.\n"
              "- Do NOT significantly change length or structure.\n"
              "- Keep the original outline and section order.\n"
        )
        repair_max = min(int(out_cap * 0.40), 6000)
        repaired = call_openai(
            system_prompt=FILL_SYSTEM_PROMPT,  # Same as fill - repairing JSON structure
            user_prompt=repair_user,
            max_output_tokens = repair_max,
            temperature=0,
            user_id=user_id,
            endpoint="/summarize",
            db=db
        )
        result = parse_json_robust(repaired) or result
        print("[REDUCE] Self-repair complete")
    else:
        print("[REDUCE] Output validated ✓")
    
    # === STAGE 4: Auto-Expansion if output is too short ===
    result_json = json.dumps(result, ensure_ascii=False)
    result_chars = len(result_json)
    min_acceptable_chars = 32000  # Minimum for comprehensive output
    
    if result_chars < min_acceptable_chars:
        print(f"[REDUCE] Output too short ({result_chars} chars), triggering auto-expansion...")
        
        # Count current content for targeted expansion
        num_concepts = sum(len(sec.get("concepts", [])) for sec in result.get("summary", {}).get("sections", []))
        num_practice = len(result.get("summary", {}).get("practice_problems", []))
        num_formulas = len(result.get("summary", {}).get("formula_sheet", []))
        
        expansion_prompt = f"""
You are enhancing a study guide that is currently too brief.

CURRENT STATE:
- Output length: {result_chars} characters
- Concepts: {num_concepts}
- Practice problems: {num_practice}
- Formulas: {num_formulas}

REQUIRED ENHANCEMENTS:
1. EXPAND each concept explanation to 800+ characters
2. ADD 2-3 more examples to EACH concept (total 3+ examples per concept)
3. ADD 2 worked examples to EACH formula with step-by-step calculations
4. ADD 5-10 practice problems with detailed solutions
5. ADD diagrams (Mermaid/textual) for visual concepts
6. ADD pseudocode for algorithmic content
7. EXPAND learning objectives to 5-8 items
8. ADD more key_points, pitfalls, when_to_use, limitations to concepts

TARGET: Minimum 40,000 characters (current: {result_chars})

CURRENT JSON TO EXPAND:
{result_json}

Return the EXPANDED version as valid JSON. DO NOT remove any existing content, only ADD and EXPAND."""

        try:
            expanded_json = call_openai(
                system_prompt="You are an expert at expanding study notes while maintaining structure.",
                user_prompt=expansion_prompt,
                max_output_tokens=16000,  # Allow large expansion
                temperature=0.3,  # Slightly creative for examples
                user_id=user_id,
                endpoint="/summarize",
                db=db
            )
            expanded_result = parse_json_robust(expanded_json)
            if expanded_result:
                expanded_chars = len(json.dumps(expanded_result, ensure_ascii=False))
                print(f"[REDUCE] Auto-expansion complete: {result_chars} → {expanded_chars} chars")
                result = expanded_result
            else:
                print("[REDUCE] Auto-expansion failed to parse, keeping original")
        except Exception as e:
            print(f"[REDUCE] Auto-expansion error: {e}, keeping original")
    else:
        print(f"[REDUCE] Output length acceptable ({result_chars} chars)")
    
    return result


# ========== OpenAI Integration ==========
import time
def call_openai(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: Optional[int] = None,
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

    if max_output_tokens is None:
        max_output_tokens = 14000  # default fallback

    # En düşük sınır 6000; hiçbir aşama 4000’e düşemez
    if max_output_tokens < 6000:
        max_output_tokens = 6000
    
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
        time.sleep(1.0) 
        attempt += 1
        
        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": current_max_tokens
        }
        
        print(f"[OPENAI REQUEST] Attempt {attempt}, Model: {OPENAI_MODEL}, max_tokens: {current_max_tokens}")
        
        # Increased timeout: 180s → 600s (10 min)
        # GPT-4o with large JSON outputs (10k-14k tokens) often exceeds 3 minutes
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        
        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(f"OpenAI API call failed ({response.status_code}): {error_detail}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        finish_reason = result["choices"][0].get("finish_reason")
        usage = result.get("usage", {})
        
        print(f"[OPENAI RESPONSE] Returned {len(content)} chars, finish_reason: {finish_reason}")
        
        # Track token usage in database (non-blocking)
        if endpoint and attempt == 1 and usage and user_id:  # Only track on first successful attempt with usage data
            try:
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                # Skip if no tokens
                if total_tokens == 0:
                    print(f"[TOKEN TRACKING] ⚠️ Skipping - zero tokens")
                else:
                    # Cost calculation (per 1M tokens)
                    if "gpt-4o" in OPENAI_MODEL.lower() and "mini" not in OPENAI_MODEL.lower():
                        input_cost_per_1m = 2.50
                        output_cost_per_1m = 10.00
                    elif "gpt-4" in OPENAI_MODEL.lower():
                        input_cost_per_1m = 30.00
                        output_cost_per_1m = 60.00
                    else:
                        input_cost_per_1m = 0.150
                        output_cost_per_1m = 0.600
                    
                    estimated_cost = (input_tokens / 1_000_000 * input_cost_per_1m) + (output_tokens / 1_000_000 * output_cost_per_1m)
                    
                    # Use centralized token tracker with fresh session
                    from app.services.token_tracker import log_token_usage
                    log_token_usage(
                        user_id=user_id,
                        endpoint=endpoint,
                        model=OPENAI_MODEL,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        estimated_cost=estimated_cost
                    )
            except Exception as e:
                # Don't fail the request if token tracking fails
                print(f"[TOKEN TRACKING ERROR] ❌ Failed to track: {e}")
                import traceback
                traceback.print_exc()
        
        # If truncated and retry enabled, try with 20% more tokens
        if finish_reason == "length" and retry_on_length and attempt < 2:
            current_max_tokens = 14000
            # Retry sırasında minimum 8000'e çık
            if current_max_tokens < 8000:
                current_max_tokens = 8000
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
    out_budget: int = None,
    user_id: Optional[int] = None,
    db = None
) -> str:
    """
    Extract and expand content from a single chunk (MAP phase)
    Returns PLAIN TEXT (not JSON) - comprehensive explanatory prose
    Reduce phase will later synthesize all chunks into structured JSON
    """
    # Adaptive budget based on chunk content (boosted for deeper output)
    if out_budget is None:
        from app.utils.adaptive_budget import calculate_chunk_budget
        out_budget = calculate_chunk_budget(chunk_text)
        # Boost budget for plain text mode (more comprehensive)
        out_budget = int(out_budget * 1.5)  # 50% more tokens for deeper prose
        print(f"[MAP ADAPTIVE] Allocated {out_budget} tokens for this chunk (plain text mode)")
    
    lang_instruction = "Write in TURKISH." if language == "tr" else "Write in ENGLISH."
    
    user_prompt = f"""
You are extracting the raw conceptual content of this document chunk.

TASK:
- Extract ALL concepts, definitions, explanations, formulas, examples
- EXPAND ideas with additional context and clarification
- Add missing explanations that help understanding
- Clarify relationships between concepts
- Add examples and real-world applications
- Explain WHY and HOW, not just WHAT

OUTPUT FORMAT:
- Plain text prose (NO JSON, NO rigid structure)
- Use natural paragraphs
- Teaching tone - explain deeply
- Minimum 1200-2000 words
- Cover EVERYTHING in the chunk
- DO NOT compress - EXPAND for clarity

{lang_instruction}

{additional_instructions if additional_instructions else ""}

CHUNK TO PROCESS:

{chunk_text}

Write comprehensive explanatory text covering all content above:"""
    
    response = call_openai(
        system_prompt=MAP_SYSTEM_PROMPT,  # Plain text mode
        user_prompt=user_prompt,
        max_output_tokens=out_budget,
        temperature=0.2,  # Slightly creative but focused
        user_id=user_id,
        endpoint="/summarize",
        db=db
    )
    
    # Plain text - no parsing needed, just return as-is
    print(f"[MAP OUTPUT] Generated {len(response)} chars of explanatory text")
    return response


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
    Merge plain text chunks into final structured JSON study guide (REDUCE phase)
    MAP phase returns plain text - REDUCE synthesizes into comprehensive JSON
    Returns final JSON string
    """
    import json
    from app.utils.coverage_validator import validate_coverage, generate_coverage_report
    
    # Chunks are now plain text, not JSON - combine them all
    print(f"[REDUCE] Merging {len(chunk_summaries)} plain text chunks into structured JSON")
    
    # Combine all chunk texts with separators
    combined_text = "\n\n=== CHUNK SEPARATOR ===\n\n".join(chunk_summaries)
    total_chars = len(combined_text)
    print(f"[REDUCE] Combined chunks: {total_chars} characters total")
    
    # Truncate if too large (keep most recent/important content)
    max_chars = 120000  # ~30k tokens
    if total_chars > max_chars:
        print(f"[REDUCE] Truncating combined text from {total_chars} to {max_chars} chars")
        combined_text = combined_text[-max_chars:]  # Keep end (usually most detailed)
    
    # Language instruction
    lang_instruction = "Output in TURKISH." if language == "tr" else "Output in ENGLISH."
    
    # Build comprehensive reduce prompt
    reduce_prompt = f"""
You are StudyWithAI, an elite academic tutor.

You will receive MULTIPLE text chunks extracted from a document.
These chunks contain EXPANDED explanatory content (plain text, NOT JSON).

YOUR TASK:
Synthesize ALL chunks into ONE comprehensive structured JSON study guide.

REQUIRED JSON STRUCTURE:
{{
  "summary": {{
    "title": "Study Guide: [Topic]",
    "overview": "2-4 sentence comprehensive overview",
    "learning_objectives": ["Objective 1", "Objective 2", ...],
    "sections": [
      {{
        "heading": "Section name",
        "concepts": [
          {{
            "term": "Concept name",
            "definition": "Clear, concise definition",
            "explanation": "Deep explanation (800+ characters)",
            "example": "Real-world example with details",
            "key_points": ["Point 1", "Point 2", ...],
            "pitfalls": ["Common mistake 1", ...],
            "when_to_use": ["Use case 1", ...],
            "limitations": ["Limitation 1", ...]
          }}
        ],
        "bullets": ["Summary bullet 1", ...]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "Formula name",
        "expression": "LaTeX expression in \\\\( \\\\)",
        "variables": {{"x": "meaning of x"}},
        "worked_example": "Step-by-step calculation with numbers",
        "notes": "Usage hints, complexity, constraints"
      }}
    ],
    "diagrams": [
      {{
        "title": "Diagram title",
        "description": "What it shows and why",
        "content": "Mermaid syntax or textual description",
        "type": "flowchart|graph|tree|other"
      }}
    ],
    "pseudocode": [
      {{
        "name": "Algorithm name",
        "code": "Pseudocode here",
        "explanation": "What it does, when to use",
        "example_trace": "Example input → output"
      }}
    ],
    "practice_problems": [
      {{
        "problem": "Full problem statement",
        "difficulty": "easy|medium|hard",
        "solution": "Detailed solution",
        "steps": ["Step 1", "Step 2", ...],
        "key_concepts": ["Concept used", ...]
      }}
    ]
  }},
  "citations": []
}}

CRITICAL REQUIREMENTS (NON-NEGOTIABLE):
1. Cover 100% of content from ALL chunks
2. Minimum output: 40,000 characters (target 50,000-60,000)
3. Minimum 12-20 sections (organize logically by topic)
4. MINIMUM 3 examples per concept (each 150+ chars)
5. MINIMUM 2 worked examples per formula (with step-by-step calculations)
6. Create 8-12 practice problems with detailed solutions
7. Add diagrams (Mermaid/textual) for visual concepts
8. Add pseudocode for all algorithmic content
9. Each concept explanation: minimum 800 characters
10. DO NOT compress - EXPAND everything to maximum depth
11. Use 85-95% of available token budget
12. Never say "not provided" or "not available" - infer from content

{lang_instruction}
{f"User instructions: {additional_instructions}" if additional_instructions else ""}

CHUNKS TO SYNTHESIZE:

{combined_text}

Generate the complete structured JSON study guide:"""
    
    # Call OpenAI for final synthesis
    print("[REDUCE] Calling OpenAI for final JSON synthesis...")
    try:
        final_json = call_openai(
            system_prompt="You are an expert at synthesizing educational content into structured study guides.",
            user_prompt=reduce_prompt,
            max_output_tokens=out_budget,
            temperature=0.3,  # Slightly creative for examples
            user_id=user_id,
            endpoint="/summarize",
            db=db
        )
        
        # Parse and validate JSON
        from app.utils.json_helpers import parse_json_robust
        result = parse_json_robust(final_json)
        
        if not result:
            print("[REDUCE] JSON parse failed, attempting repair...")
            repair_prompt = f"Fix this into valid JSON only (no other text):\n\n{final_json}"
            repaired = call_openai(
                system_prompt="You repair invalid JSON.",
                user_prompt=repair_prompt,
                max_output_tokens=4000,
                temperature=0,
                user_id=user_id,
                endpoint="/summarize",
                db=db
            )
            result = parse_json_robust(repaired)
        
        if not result:
            raise ValueError("Failed to generate valid JSON after repair attempt")
        
        print("[REDUCE] JSON synthesis successful ✓")
        
        # Auto-expansion if output is too short
        result_chars = len(json.dumps(result, ensure_ascii=False))
        min_acceptable_chars = 40000
        
        if result_chars < min_acceptable_chars:
            print(f"[REDUCE] Output too short ({result_chars} chars), triggering auto-expansion...")
            
            expansion_prompt = f"""
You are enhancing a study guide that needs MORE DEPTH.

CURRENT STATE: {result_chars} characters

REQUIRED ENHANCEMENTS:
1. EXPAND each concept explanation to 800+ characters  
2. ADD 2-3 more examples to EACH concept (total 3+ per concept)
3. ADD 2 worked examples to EACH formula with calculations
4. ADD 5-10 practice problems with detailed solutions
5. ADD diagrams (Mermaid) for visual concepts
6. ADD pseudocode for algorithms
7. EXPAND learning objectives to 6-10 items
8. ADD pitfalls, limitations, when_to_use to concepts

TARGET: Minimum 50,000 characters

CURRENT JSON:
{json.dumps(result, ensure_ascii=False)}

Return EXPANDED version as valid JSON:"""
            
            try:
                expanded_json = call_openai(
                    system_prompt="You expand study notes while preserving structure.",
                    user_prompt=expansion_prompt,
                    max_output_tokens=16000,
                    temperature=0.3,
                    user_id=user_id,
                    endpoint="/summarize",
                    db=db
                )
                expanded = parse_json_robust(expanded_json)
                if expanded:
                    expanded_chars = len(json.dumps(expanded, ensure_ascii=False))
                    print(f"[REDUCE] Auto-expansion: {result_chars} → {expanded_chars} chars")
                    result = expanded
            except Exception as e:
                print(f"[REDUCE] Auto-expansion error: {e}, keeping original")
        
        # COVERAGE VALIDATION: Check if all topics are covered
        if original_text:
            print("[COVERAGE] Validating topic coverage...")
            coverage_result = validate_coverage(original_text, result, min_coverage=0.85)
            print(generate_coverage_report(coverage_result))
            
            # CRITICAL FIX: NO REGENERATION! Prevents infinite loop
            # Coverage validator was causing timeout by recursively calling reduce_two_stage
            # If coverage insufficient, just log and continue with what we have
            if not coverage_result['passed'] and coverage_result['missing_topics']:
                print(f"[COVERAGE] ⚠️ Coverage insufficient ({coverage_result['coverage_score']:.1%})")
                print(f"[COVERAGE] Missing {len(coverage_result['missing_topics'])} topics — accepting current output (NO regeneration)")
            else:
                print(f"[COVERAGE] ✅ Coverage validated ({coverage_result['coverage_score']:.1%})")
            
                        
        # Add coverage info to result for frontend display (ALWAYS, even if 100% coverage)
        # CRITICAL: result is a JSON string, need to parse it first!
        try:
            result_dict = json.loads(result) if isinstance(result, str) else result
            # --- SAFE COVERAGE WRAP (fixes crash) ---
            if original_text and 'coverage_result' in locals():
                score = round(coverage_result.get('coverage_score', 1.0), 2)
                missing = coverage_result.get('missing_topics', [])[:20]
            else:
                score = 1.0
                missing = []
            
            result_dict['coverage'] = {
                'score': score,
                'missing_topics': missing
            }
            # FIX DIAGRAM FORMATTING: Fix Mermaid syntax errors
            import re
            if 'diagrams' in result_dict.get('summary', {}):
                for diagram in result_dict['summary']['diagrams']:
                    if 'content' in diagram:
                        content = diagram['content']
                        # Check if it's Mermaid syntax (starts with graph/flowchart)
                        if content.strip().startswith(('graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram')):
                            fixed = content
                            
                            # Fix 1: Ensure all nodes have brackets
                            lines = fixed.split('\n')
                            fixed_lines = []
                            
                            for line in lines:
                                # Skip the graph/flowchart declaration line
                                if line.strip().startswith(('graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram')):
                                    fixed_lines.append(line)
                                    continue
                                
                                # Skip empty lines
                                if not line.strip():
                                    fixed_lines.append(line)
                                    continue
                                
                                fixed_line = line
                                
                                # Fix 1: Quote ALL edge labels FIRST (before other fixes)
                                # This is CRITICAL - must quote labels before manipulating nodes
                                # Match: -->|label| where label is NOT already quoted
                                fixed_line = re.sub(r'-->\|([^|]+)\|', lambda m:
                                    f'-->|"{m.group(1).strip()}"|' if not (m.group(1).strip().startswith('"') and m.group(1).strip().endswith('"')) else m.group(0), fixed_line)
                                
                                # Fix 2: Add brackets to bare node names at START of edge
                                # Pattern: NodeName --> becomes NodeName[NodeName] -->
                                # Match word at start of line or after whitespace
                                fixed_line = re.sub(r'^(\s*)([A-Z][a-zA-Z0-9_]+)(\s+-->)', lambda m:
                                    f'{m.group(1)}{m.group(2)}[{m.group(2)}]{m.group(3)}' if '[' not in m.group(0) else m.group(0), fixed_line)
                                
                                # Fix 3: Add brackets to bare node names at END of edge (after label)
                                # Pattern: -->|"label"| NodeName becomes -->|"label"| NodeName[NodeName]
                                # Must handle both quoted and unquoted labels
                                fixed_line = re.sub(r'(\|"[^"]*"\||\|[^|]*\|)(\s+)([A-Z][a-zA-Z0-9_]+)(\s*$)', lambda m:
                                    f'{m.group(1)}{m.group(2)}{m.group(3)}[{m.group(3)}]{m.group(4)}' if '[' not in m.group(3) else m.group(0), fixed_line)
                                
                                fixed_lines.append(fixed_line)
                            
                            fixed = '\n'.join(fixed_lines)
                            
                            # Fix 3: Ensure each edge is on its own line (critical for parsing)
                            # ONLY split when there are MULTIPLE edges on the same line
                            # Pattern: node] -->|label| node] ANOTHER_EDGE -->
                            # This means: if we find a complete edge followed by another edge, split them
                            # Match complete edge (source[source] -->|label| target[target]) followed by another source node
                            fixed = re.sub(r'(\[[^\]]+\])\s+([A-Z]\w*\[[^\]]+\]\s+-->)', r'\1\n  \2', fixed)
                            
                            if fixed != content:
                                print(f"[DIAGRAM FIX] Fixed Mermaid syntax in diagram: {diagram.get('title', 'Untitled')}")
                                print(f"  BEFORE:\n{content}")
                                print(f"  AFTER:\n{fixed}")
                                diagram['content'] = fixed
            
            # Also fix practice problem solutions
            if 'practice_problems' in result_dict.get('summary', {}):
                for idx, problem in enumerate(result_dict['summary']['practice_problems']):
                    if 'solution' in problem:
                        solution = problem['solution']
                        
                        # Check if it's Mermaid syntax (with or without prefix)
                        is_mermaid = solution.strip().startswith(('graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram'))
                        
                        # Also detect Mermaid if it has pattern: Node[Label] -->|...| Node[Label]
                        if not is_mermaid and '-->' in solution and '[' in solution and ']' in solution:
                            # This looks like Mermaid without prefix - add graph TD
                            print(f"[PRACTICE FIX {idx+1}] Detected Mermaid without prefix, adding 'graph TD'")
                            solution = f"graph TD\n  {solution.strip()}"
                            is_mermaid = True
                        
                        if is_mermaid:
                            # Apply same fixes as diagrams
                            fixed = solution
                            
                            # Fix 1: Ensure all nodes have brackets
                            lines = fixed.split('\n')
                            fixed_lines = []
                            
                            for line in lines:
                                if line.strip().startswith(('graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram')):
                                    fixed_lines.append(line)
                                    continue
                                
                                if not line.strip():
                                    fixed_lines.append(line)
                                    continue
                                
                                fixed_line = line
                                
                                # Fix 1: Quote ALL edge labels FIRST
                                fixed_line = re.sub(r'-->\|([^|]+)\|', lambda m:
                                    f'-->|"{m.group(1).strip()}"|' if not (m.group(1).strip().startswith('"') and m.group(1).strip().endswith('"')) else m.group(0), fixed_line)
                                
                                # Fix 2: Add brackets to bare node names at START of edge
                                fixed_line = re.sub(r'^(\s*)([A-Z][a-zA-Z0-9_]+)(\s+-->)', lambda m:
                                    f'{m.group(1)}{m.group(2)}[{m.group(2)}]{m.group(3)}' if '[' not in m.group(0) else m.group(0), fixed_line)
                                
                                # Fix 3: Add brackets to bare node names at END of edge
                                fixed_line = re.sub(r'(\|"[^"]*"\||\|[^|]*\|)(\s+)([A-Z][a-zA-Z0-9_]+)(\s*$)', lambda m:
                                    f'{m.group(1)}{m.group(2)}{m.group(3)}[{m.group(3)}]{m.group(4)}' if '[' not in m.group(3) else m.group(0), fixed_line)
                                
                                fixed_lines.append(fixed_line)
                            
                            fixed = '\n'.join(fixed_lines)
                            
                            # Fix 3: Ensure each edge is on its own line (ONLY when multiple edges exist)
                            # Match complete edge followed by another source node
                            fixed = re.sub(r'(\[[^\]]+\])\s+([A-Z]\w*\[[^\]]+\]\s+-->)', r'\1\n  \2', fixed)
                            
                            if fixed != solution:
                                print(f"[PRACTICE FIX {idx+1}] Fixed Mermaid syntax")
                                print(f"  BEFORE:\n{solution}")
                                print(f"  AFTER:\n{fixed}")
                                problem['solution'] = fixed
                            else:
                                problem['solution'] = solution  # Still update with prefix if added
            
            # FIX LATEX FORMULAS: Ensure proper LaTeX wrapping and syntax
            if 'formula_sheet' in result_dict.get('summary', {}):
                for formula in result_dict['summary']['formula_sheet']:
                    # Fix expression field
                    if 'expression' in formula:
                        expr = formula['expression']
                        
                        # Fix 1: Replace ALL \text{...} with \mathtt{...} and escape underscores
                        def fix_text_to_mathtt(match):
                            content = match.group(1).replace("_", "\\_")
                            return f'\\mathtt{{{content}}}'
                        expr = re.sub(r'\\text\{([^}]+)\}', fix_text_to_mathtt, expr)
                        
                        # Fix 2: If not wrapped in \( \), wrap it
                        if not (expr.strip().startswith(r'\(') or expr.strip().startswith('$')):
                            expr = f'\\({expr}\\)'
                        
                        if expr != formula['expression']:
                            formula['expression'] = expr
                            print(f"[FORMULA FIX] Fixed expression: {formula.get('name', 'Unnamed')}")
                    
                    # Fix worked_example field
                    if 'worked_example' in formula:
                        example = formula['worked_example']
                        original = example
                        
                        # Fix 1: Remove broken LaTeX markers (incomplete \( or \))
                        def fix_broken_latex(match):
                            content = match.group(1).replace("_", "\\_")
                            return f'\\(\\mathtt{{{content}}}\\)'
                        example = re.sub(r'\\text\{([^}]+)\}\\?\)?', fix_broken_latex, example)
                        
                        # Fix 2: Replace remaining \text{...} with \mathtt{...}
                        def fix_text_to_mathtt(match):
                            content = match.group(1).replace("_", "\\_")
                            return f'\\mathtt{{{content}}}'
                        example = re.sub(r'\\text\{([^}]+)\}', fix_text_to_mathtt, example)
                        
                        # Fix 3: Clean up any orphaned backslashes or incomplete wrappers
                        example = re.sub(r'\\text\{', r'\\mathtt{', example)
                        example = re.sub(r'\\\)?\s*blocks', r' blocks', example)  # Fix broken wrapper at end
                        
                        if example != original:
                            formula['worked_example'] = example
                            print(f"[FORMULA FIX] Fixed worked_example: {formula.get('name', 'Unnamed')}")
                            print(f"  BEFORE: {original[:100]}")
                            print(f"  AFTER: {example[:100]}")
            
            result = json.dumps(result_dict, ensure_ascii=False, indent=2)
            print(f"[COVERAGE] ✅ Coverage added to JSON: {coverage_result['coverage_score']:.1%} score, {len(coverage_result['missing_topics'])} missing topics")
        except Exception as e:
            print(f"[COVERAGE] ⚠️  Failed to add coverage info: {e}")
            import traceback
            traceback.print_exc()
        # ==========================================================
        # AUTO-FIX: Guarantee all required summary fields exist
        # Prevents frontend from crashing on undefined.map
        # ==========================================================
        
        try:
            result_dict = json.loads(result) if isinstance(result, str) else result
        except:
            # Son çare: boş summary ile wrap
            result_dict = {"summary": {}}
        
        # SAFE DEFAULTS: FRONTEND CRASH ENGELLER
        summary_obj = result_dict.setdefault("summary", {})
        
        summary_obj.setdefault("title", "Generated Summary")
        summary_obj.setdefault("overview", "")
        summary_obj.setdefault("learning_objectives", [])
        summary_obj.setdefault("sections", [])
        summary_obj.setdefault("formula_sheet", [])
        summary_obj.setdefault("diagrams", [])
        summary_obj.setdefault("pseudocode", [])
        summary_obj.setdefault("practice_problems", [])
        
        # Citations her zaman array olmalı (frontend bunu bekliyor)
        result_dict.setdefault("citations", [])
        
        # Tekrar JSON'a çevirip return edelim
        result = json.dumps(result_dict, ensure_ascii=False, indent=2)
        # Return as JSON string (for compatibility with existing pipeline)
        return result
    
    except Exception as e:
        print(f"[REDUCE ERROR] Plain text synthesis failed: {e}")
        print(f"[REDUCE ERROR] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Fallback: Return minimal valid structure to prevent total failure
        print("[REDUCE FALLBACK] Returning minimal valid JSON structure")
        fallback = {
            "summary": {
                "title": "Summary (Error Recovery)",
                "overview": f"An error occurred during synthesis. Chunks available: {len(chunk_summaries)}",
                "learning_objectives": ["Review source material"],
                "sections": [
                    {
                        "heading": "Content Summary",
                        "concepts": [
                            {
                                "term": "Error Recovery Mode",
                                "definition": "The system encountered an error during processing",
                                "explanation": "Please try regenerating or contact support if the issue persists",
                                "example": "",
                                "key_points": []
                            }
                        ],
                        "bullets": []
                    }
                ],
                "formula_sheet": [],
                "diagrams": [],
                "pseudocode": [],
                "practice_problems": []
            },
            "citations": []
        }
        return json.dumps(fallback, ensure_ascii=False, indent=2)


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
    
    # === CHUNKING KARARI ===
    # Küçük dokümanlarda hız için tek-pass mod
    if force_chunking:
        use_chunking = True
    else:
        # 8000 token'dan küçükse tek aşama özet
        use_chunking = estimated_tokens > 8000

    if not use_chunking:
        print("[SINGLE-PASS DISABLED] Forcing MAP-REDUCE for deep academic summary")
        # simply do nothing → let normal MAP-REDUCE flow run
        pass  

    # Large document: map-reduce with pure token-based chunking
    print(f"[MAP-REDUCE] Estimated {estimated_tokens} tokens, using pure token-based chunking")
    
    # === CHUNKING (Pure token-based - universal & reliable) ===
    # Structure parser disabled: causes issues with PDFs (340+ blocks, incorrect parsing)
    # Pure token-based chunking is more reliable and works consistently across all formats
    print(f"[CHUNKING] Using pure token-based chunking (target: {CHUNK_INPUT_TARGET} tokens per chunk)")
    
    chunks = split_text_approx_tokens(full_text, CHUNK_INPUT_TARGET)
    chunk_metadata = []
    
    # Detect heading from each chunk for better traceability
    for i, chunk in enumerate(chunks):
        # Extract first meaningful line as heading hint
        first_lines = chunk.strip().split('\n')[:3]
        heading_hint = ' '.join(first_lines)[:100] if first_lines else f"Chunk {i+1}"
        chunk_metadata.append({
            "heading_path": heading_hint,
            "chunk_index": i + 1
        })
    
        
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
            out_budget=None,  # Let adaptive budget calculate
            user_id=user_id,
            db=db
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
    # Çıkış bütçesini 12k ile sınırla
    merge_budget = min(out_cap, MERGE_OUTPUT_BUDGET[1], 14000)
    print("[MAP-REDUCE] Merging ALL chunks…")
    final_summary = merge_summaries(
        chunk_summaries,
        language=language,
        additional_instructions=enhanced_instructions,
        out_budget=merge_budget,
        domain=domain,
        chunk_citations=chunk_citations,
        original_text=full_text,  # Pass original text for coverage validation
        user_id=user_id,
        db=db
    )
    
    
    return final_summary




def summarize_no_files(
    topic: str,
    language: str = "en",
    out_cap: int = 12000,
    user_id: Optional[int] = None,
    db = None
) -> str:
    """
    Generate summary without uploaded files (from prompt only)
    Uses general knowledge + same JSON format as file-based summaries
    """
    lang_instr = "Use TURKISH for ALL output." if language == "tr" else "Use ENGLISH for ALL output."
    
    # Build dedicated no-files prompt with correct JSON schema
    user_prompt = f"""You are creating comprehensive study notes on the topic: "{topic}"

{lang_instr}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TASK: Generate study guide from your knowledge base
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Since no files were uploaded, generate comprehensive content based on your knowledge of "{topic}".

REQUIREMENTS:
1. ✅ REAL CONTENT with actual names, dates, facts (NO placeholders!)
2. ✅ MINIMUM 10-15 sections covering main aspects of {topic}
3. ✅ Each section: 3-5 detailed concepts (250-400 words each)
4. ✅ MINIMUM 8,000 tokens output (comprehensive depth)
5. ✅ Real examples, historical context, practical applications

CONTENT APPROACH:
- Main themes and categories within "{topic}"
- History, key figures, major developments
- Core principles and methodologies
- Real-world applications and examples
- Current state and future directions (if applicable)
- Formulas/equations (if applicable to topic)
- Diagrams: ONLY if truly helpful (1-3 visual aids)
- Practice problems: 4-6 with detailed solutions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 OUTPUT EXACT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output ONLY valid JSON (no markdown, no code fences):

{{
  "summary": {{
    "title": "Study Notes: {topic}",
    "overview": "<2-3 sentence introduction to {topic}>",
    "learning_objectives": [
      "<Specific measurable outcome 1>",
      "<Specific measurable outcome 2>",
      "<3-5 objectives total>"
    ],
    "sections": [
      {{
        "heading": "<Real topic-specific heading (NOT 'Section 1')>",
        "bullets": ["<Key point>", "<Key point>"],
        "concepts": [
          {{
            "term": "<Real concept name>",
            "definition": "<Clear definition>",
            "explanation": "<Detailed 250-400 word explanation with examples>",
            "example": "<Concrete real-world example>",
            "key_points": ["<Essential point>", "<Essential point>"]
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "<Formula/equation name>",
        "expression": "<LaTeX: \\\\(formula\\\\)>",
        "variables": {{"symbol": "meaning"}},
        "worked_example": "<Step-by-step calculation>",
        "notes": "<When to use, constraints>"
      }}
    ],
    "diagrams": [
      {{
        "title": "<Diagram title>",
        "description": "<What it shows>",
        "content": "<Mermaid syntax or description>",
        "type": "flowchart"
      }}
    ],
    "pseudocode": [
      {{
        "title": "<Algorithm name>",
        "code": "<Step-by-step pseudocode>",
        "explanation": "<What it does>",
        "example_trace": "<Sample execution>"
      }}
    ],
    "practice_problems": [
      {{
        "problem": "<Problem statement>",
        "difficulty": "easy|medium|hard",
        "solution": "<Detailed solution>",
        "steps": ["<Step 1>", "<Step 2>"],
        "key_concepts": ["<Concept>", "<Concept>"]
      }}
    ]
  }},
  "citations": ["<General knowledge source>", "<Reference>"]
}}

🚨 CRITICAL:
- ALL content must be topic-specific (no "Concept 1" placeholders!)
- Section headings must be REAL (e.g., "History of {topic}", not "Section 1")
- Concepts must have DETAILED explanations (250-400 words each)
- Output MUST be 8,000+ tokens
- Only include diagrams/pseudocode/formulas if relevant to {topic}

Generate comprehensive study notes about: {topic}"""
    
    return call_openai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_output_tokens=min(out_cap, MERGE_OUTPUT_BUDGET[1]),
        user_id=user_id,
        endpoint="/summarize",
        db=db
    )

