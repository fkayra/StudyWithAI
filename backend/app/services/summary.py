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
3. **Worked Examples**: Every concept and formula must have detailed numerical examples
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

⚠️ PRE-FINALIZATION SELF-CHECK:
Before outputting, verify your work against your internal plan:
✓ Did you cover all topics from your outline?
✓ Does every formula have: expression + variables + multiple worked examples?
✓ Does every concept have at least 2-3 concrete examples with calculations?
✓ Did you include algorithm complexity analysis where applicable?
✓ Does glossary have ≥8 substantive terms?
✓ Is JSON structure complete and valid (all brackets closed)?
✓ Did you use full token budget for depth (no practice questions)?

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
- If no formulas/theorems, return empty arrays []
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


def quality_score(result: dict) -> float:
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
    Domain-adaptive prompt for merging chunk summaries into final JSON (reduce phase)
    Includes chain-of-thought planning for higher quality single-call output
    Adjusts emphasis based on detected content type (technical/social/procedural/general)
    """
    # Language instruction
    lang_instr = (
        "Generate the ENTIRE summary in TURKISH. All headings, explanations, and content must be in Turkish."
        if language == "tr"
        else "Generate the ENTIRE summary in ENGLISH."
    )
    
    # Domain-specific guidance
    domain_guidance = {
        "technical": "This is TECHNICAL/SCIENTIFIC content. Emphasize: formulas with derivations, algorithms with complexity analysis, mathematical proofs, numerical examples with step-by-step calculations, and precise technical definitions.",
        "social": "This is SOCIAL SCIENCES content. Emphasize: theoretical frameworks, conceptual relationships, historical context, real-world applications, case studies, critical analysis, and diverse perspectives.",
        "procedural": "This is PROCEDURAL/MANUAL content. Emphasize: step-by-step processes, decision trees, implementation guidelines, prerequisites, common errors, troubleshooting tips, and practical application.",
        "general": "Adapt your approach based on the content. Balance conceptual understanding with practical application."
    }
    
    domain_instr = domain_guidance.get(domain, domain_guidance["general"])
    additional = f"\n\nUSER ADDITIONAL REQUIREMENTS:\n{additional_instructions}" if additional_instructions else ""
    
    # Chain-of-thought planning instruction
    planning_instr = """
⚡ CRITICAL: TWO-STEP INTERNAL PROCESS (DO NOT OUTPUT THE PLAN)

STEP 1 - INTERNAL PLANNING (think, don't write):
Before generating the JSON, mentally build a complete outline:
1. List ALL major topics and subtopics from the source material
2. Identify which concepts need formulas and multiple worked examples
3. Plan where to add numerical examples, edge cases, and complexity analysis
4. Note critical formulas that MUST have variables + multiple worked examples
5. Plan glossary terms (technical vocabulary, key definitions)
6. Structure sections logically (foundational concepts → advanced applications)
7. Allocate token budget: prioritize depth over breadth

STEP 2 - EXECUTION (write the JSON):
Now produce the comprehensive study notes following your internal plan.
DO NOT include any practice questions (multiple-choice, short-answer, or problem-solving).
Use all available token budget to deepen explanations, add numeric worked examples,
include algorithm complexity notes, and clarify formulas with multiple examples.
Ensure every part of your outline is reflected in the final JSON.
Cross-check: did you include all topics? Multiple examples per concept? Detailed formulas?
"""
    
    return f"""You are StudyWithAI, an elite academic tutor. Your mission: transform structured knowledge into comprehensive, deeply explanatory study notes.

{lang_instr}

{planning_instr}

🎯 DOMAIN CONTEXT:
{domain_instr}{additional}

📚 SOURCE DATA FORMAT:
You will receive pre-extracted structured knowledge with:
- concepts[] (already has term/definition/explanation/example)
- formulas[] (already has expression/variables/worked_example)
- theorems[] (already has statement/proof_sketch/application)
- examples[] (already has context/solution/key_insight)

YOUR TASK:
1. **Organize by topic**: Group related concepts/formulas/theorems into logical sections
2. **Deduplicate**: If same concept appears multiple times, merge into single entry (keep best explanation + all examples)
3. **Enrich deeply**: Add multiple worked examples, edge cases, complexity analysis to each concept
4. **Complete**: Build comprehensive formula_sheet and glossary from the source material
5. **Verify depth**: Every formula has multiple worked examples, every concept has 2-3 concrete examples

🎯 QUALITY REQUIREMENTS:
- **MAXIMUM DEPTH**: Use all token budget for explanations, NOT practice questions
- **Multiple examples**: Each concept should have 2-3 worked examples with actual calculations
- **NO generic tips**: "Study carefully" → ❌ | "When x=0, denominator becomes zero causing undefined behavior" → ✅
- **NO placeholder content**: If source lacks info, use what's there (don't invent generic content)
- **Preserve all worked examples**: Source examples must appear in your output
- **DO NOT include practice questions**: No MCQ, no short-answer, no problem-solving sections

🚫 ABSOLUTE PROHIBITIONS:
✗ Describe the document → ✓ Teach the subject directly
✗ Generic phrases ("review carefully", "important for exams") → ✓ Specific actionable tips
✗ Formulas without variables defined → ✓ Every symbol explained with at least one worked example
✗ Questions without answers → ✓ Every question has clear answer + explanation

✅ MANDATORY QUALITY STANDARDS:

**Concepts:**
- Definition: Precise, technical
- Explanation: 3-4 detailed paragraphs covering:
  * Core mechanism (HOW it works in detail)
  * Mathematical foundation (WHY it works)
  * Practical applications (WHEN to use)
  * Edge cases and limitations (WHAT can go wrong)
  * Complexity analysis (if algorithm: O(n) time/space)
- Examples: 2-3 concrete examples with actual numbers and step-by-step calculations
- Key Points: Specific pitfalls, special cases, implementation notes

**Formulas:**
- Expression: Full mathematical notation
- Variables: Dictionary format {{"symbol": "meaning with units and constraints"}}
- Derivation: Show key derivation steps (not just final form)
- Notes: Multiple worked examples (at least 2-3), edge cases, when formula breaks down
- Common Mistakes: Specific calculation errors with corrections

**Glossary:**
- Minimum 10 terms covering all major vocabulary and technical concepts
- Substantive definitions (not just dictionary)
- Include: mathematical definition, intuitive explanation, related concepts

**Citations:**
- For each concept/formula, preserve _source metadata if present
- Transform into citations array with format: {{"section": "heading_path", "content_type": "concept|formula", "term": "..."}}
- Provide specific references students can trace back to source material

🔒 JSON OUTPUT REQUIREMENTS:
✓ Pure JSON only (NO markdown fences like ```json```)
✓ Complete structure (close all brackets, braces, quotes)
✓ No trailing commas
✓ Valid syntax throughout
✓ Match schema exactly

📐 EXACT JSON SCHEMA (NO PRACTICE QUESTIONS):

{{
  "summary": {{
    "title": "Study Notes: [Detected Topic]",
    "overview": "2-3 sentence overview of what this material covers and depth of coverage",
    "learning_objectives": [
      "Objective 1: Deep understanding of concept X",
      "Objective 2: Master mathematical foundations of Y",
      "Objective 3: Apply techniques to solve Z-type problems"
    ],
    "sections": [
      {{
        "heading": "Main Topic Name",
        "concepts": [
          {{
            "term": "Concept Name",
            "definition": "Precise, technical definition with mathematical notation",
            "explanation": "Extensive explanation (3-4 paragraphs covering: detailed mechanism, mathematical foundation, practical applications, edge cases, complexity if applicable)",
            "examples": [
              {{
                "scenario": "What we're calculating",
                "setup": "Given values and constraints",
                "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
                "result": "Final answer with units and interpretation"
              }},
              {{
                "scenario": "Edge case or alternative approach",
                "setup": "Different initial conditions",
                "steps": ["Step 1: ...", "Step 2: ..."],
                "result": "Result showing different behavior"
              }}
            ],
            "key_points": ["Critical insight 1", "Common pitfall with explanation", "Implementation note"]
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "Formula Name",
        "expression": "Full mathematical notation",
        "variables": {{"x": "meaning with units and valid range", "y": "meaning with constraints"}},
        "derivation_steps": ["Key step 1 in derivation", "Key step 2", "Final form"],
        "worked_examples": [
          {{
            "given": "x=5, y=10",
            "calculation": "Step-by-step substitution",
            "result": "Final numerical answer"
          }},
          {{
            "given": "Edge case: x=0",
            "calculation": "How formula behaves",
            "result": "Limiting behavior or error"
          }}
        ],
        "notes": "When to use, when it breaks down, common calculation errors"
      }}
    ],
    "glossary": [
      {{
        "term": "Technical Term",
        "definition": "Mathematical definition",
        "intuition": "Plain language explanation",
        "related_concepts": ["Related term 1", "Related term 2"]
      }}
    ]
  }},
  "citations": [
    {{"section": "heading_path", "content_type": "concept|formula", "term": "what was cited"}}
  ]
}}

🔍 PRE-FINALIZATION CHECKLIST:
✔ Coverage — every major topic from the material is represented
✔ Maximum Depth — each concept has 3-4 paragraph explanation + multiple examples
✔ Worked Examples — at least 2-3 numerical examples per concept with step-by-step calculations
✔ Formula Depth — each formula has derivation steps + multiple worked examples
✔ Complexity Analysis — algorithms include time/space complexity where applicable
✔ Glossary — ≥10 terms with substantive definitions
✔ NO Practice Questions — confirm no MCQ, short-answer, or problem-solving sections included
✔ JSON validity — all brackets and arrays closed; no markdown fences

OUTPUT PURE JSON NOW (no other text):"""


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
    out_cap: int = 8000,
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
    
    # Append domain hint to instructions
    domain_hint = f"Content domain: {domain}. Adjust depth and style accordingly."
    enhanced_instructions = f"{additional_instructions}\n\n{domain_hint}" if additional_instructions else domain_hint
    
    # Estimate input tokens
    estimated_tokens = approx_tokens_from_text_len(len(full_text))
    
    # Decide whether to use map-reduce
    # Use chunking if: forced, OR estimated tokens > threshold
    use_chunking = force_chunking or estimated_tokens > 8000
    
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


def summarize_no_files(
    topic: str,
    language: str = "en",
    out_cap: int = 8000
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
