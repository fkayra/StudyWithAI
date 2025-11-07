"""
AI-powered summary service with map-reduce for large documents
Includes domain detection and quality guardrails for consistent output
"""
from typing import List, Optional
import os
import requests
from app.config import (
    OPENAI_MODEL, TEMPERATURE, TOP_P,
    CHUNK_INPUT_TARGET, CHUNK_OUTPUT_BUDGET, MERGE_OUTPUT_BUDGET
)
from app.utils.files import approx_tokens_from_text_len
from app.utils.chunking import split_text_approx_tokens, merge_texts


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ========== PROMPTS ==========

SYSTEM_PROMPT = """You are StudyWithAI, an elite academic tutor specializing in exam preparation. Your mission: transform course materials into comprehensive, exam-ready study guides that guarantee student success.

CORE PRINCIPLES (NON-NEGOTIABLE):
1. **Complete Coverage**: Cover EVERY major concept, formula, and algorithm in the material
2. **Exam Focus**: Every section must prepare students for exam questions
3. **Depth Over Breadth**: Detailed explanations with worked examples
4. **Teach Directly**: Write as if teaching the student, not describing the document
5. **Quality Standards**:
   - Each concept: definition, detailed explanation (2-3 paragraphs), concrete example, exam tips
   - Each formula: full variable definitions, when to use, worked example, common mistakes
   - Each algorithm: purpose, step-by-step procedure, complexity, typical pitfalls

OUTPUT REQUIREMENTS:
- COMPREHENSIVE: Cover all major topics (minimum 3-5 sections)
- DETAILED: Each concept needs substantive explanation (not just definitions)
- ACTIONABLE: Include exam tips, common mistakes, quick checks
- COMPLETE: Formula sheet, glossary, and exam practice questions REQUIRED
- JSON ONLY: Output pure JSON (no markdown, no extra text)

BEFORE FINALIZING:
- Verify all formulas have worked examples
- Ensure glossary has ALL key terms
- Check that exam practice covers main concepts
- Validate JSON structure is complete and valid"""


def get_chunk_summary_prompt(language: str = "en") -> str:
    """Prompt for summarizing individual chunks (map phase)"""
    lang_instr = "Write in TURKISH." if language == "tr" else "Write in ENGLISH."
    
    return f"""Summarize this course excerpt into compact, information-dense bullet points.

{lang_instr}

Include:
- Key concepts and definitions
- Important formulas or principles
- One concrete example per major point
- Critical facts to remember

Format: Plain text bullets, no JSON. Keep it dense and factual.

Do not include meta-commentary like "This document discusses...". Present the actual knowledge directly."""


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
    Calculate quality score (0.0-1.0) based on content richness.
    Checks: number of concepts, formulas, exam questions, glossary terms
    """
    try:
        s = result.get("summary", {})
        sections = s.get("sections", [])
        
        # Count concepts across all sections
        num_concepts = sum(len(sec.get("concepts", [])) for sec in sections)
        
        # Count formulas
        num_formulas = len(s.get("formula_sheet", []))
        
        # Count exam questions
        exam = s.get("exam_practice", {})
        num_mcq = len(exam.get("multiple_choice", []))
        num_short = len(exam.get("short_answer", []))
        num_problems = len(exam.get("problem_solving", []))
        num_questions = num_mcq + num_short + num_problems
        
        # Count glossary terms
        num_glossary = len(s.get("glossary", []))
        
        # Calculate weighted score
        score = (
            (min(num_concepts, 10) / 10) * 0.35 +  # Max 10 concepts worth 35%
            (min(num_formulas, 5) / 5) * 0.15 +    # Max 5 formulas worth 15%
            (min(num_questions, 9) / 9) * 0.35 +   # Min 9 questions worth 35%
            (min(num_glossary, 8) / 8) * 0.15      # Min 8 terms worth 15%
        )
        
        print(f"[QUALITY SCORE] Concepts: {num_concepts}, Formulas: {num_formulas}, Questions: {num_questions}, Glossary: {num_glossary}, Score: {score:.2f}")
        return round(score, 2)
    except Exception as e:
        print(f"[QUALITY SCORE] Error calculating: {e}")
        return 0.5  # Default to medium quality on error


def get_final_merge_prompt(language: str = "en", additional_instructions: str = "", domain: str = "general") -> str:
    """
    Domain-adaptive prompt for merging chunk summaries into final JSON (reduce phase)
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
    
    return f"""You are StudyWithAI, an elite academic tutor. Your mission: merge the source summaries into a single, exam-ready study guide.

{lang_instr}

🎯 DOMAIN CONTEXT:
{domain_instr}{additional}

📚 COVERAGE LOGIC (apply to every document):
1. Identify every MAJOR TOPIC or HEADING in the material (concept, theory, method, model, algorithm, formula group)
2. For each topic, provide:
   • Clear definition and purpose
   • Detailed explanation (HOW it works, WHY it matters, WHEN to apply)
   • Key formalism or equation (if applicable)
   • Concrete example or case study (with numbers when possible)
   • Common pitfalls or misconceptions
   • Exam-style insight (how this is typically tested)
3. Create an EXAM PRACTICE KIT with realistic questions:
   • Multiple-choice (≥4 questions)
   • Short-answer (≥3 questions)
   • Problem-solving (≥2 questions)

🚫 ABSOLUTE PROHIBITIONS:
✗ Describe the document → ✓ Teach the subject directly
✗ Generic phrases ("review carefully", "important for exams") → ✓ Specific actionable tips
✗ Formulas without variables defined → ✓ Every symbol explained with at least one worked example
✗ Questions without answers → ✓ Every question has clear answer + explanation

✅ MANDATORY QUALITY STANDARDS:

**Concepts:**
- Definition: Precise, technical
- Explanation: 2-3 paragraphs (mechanism + motivation + application + limitations)
- Example: Concrete with actual numbers/values
- Exam Tips: Specific mistakes, shortcuts, how it appears in tests

**Formulas:**
- Expression: Full mathematical notation
- Variables: Dictionary format {{"symbol": "meaning with units"}}
- Notes: Derivation intuition, when to use, common errors
- Must include at least ONE worked numerical example in explanation

**Exam Practice:**
- Multiple-choice: Options as object {{"A": "text", "B": "text", "C": "text", "D": "text"}}
- Correct answer: Use "correct" field with letter ("A", "B", "C", or "D")
- Every question needs "explanation" field with reasoning

**Glossary:**
- Minimum 8 terms covering all major vocabulary
- Substantive definitions (not just dictionary)
- Include: technical meaning, relevance, distinctions from related terms

🔒 JSON OUTPUT REQUIREMENTS:
✓ Pure JSON only (NO markdown fences like ```json```)
✓ Complete structure (close all brackets, braces, quotes)
✓ No trailing commas
✓ Valid syntax throughout
✓ Match schema exactly

📐 EXACT JSON SCHEMA:

{{
  "summary": {{
    "title": "Study Guide: [Detected Topic]",
    "overview": "2-3 sentence overview of what this material covers",
    "learning_objectives": [
      "Objective 1: What students should be able to do",
      "Objective 2: Key skills or knowledge to master"
    ],
    "sections": [
      {{
        "heading": "Main Topic Name",
        "concepts": [
          {{
            "term": "Concept Name",
            "definition": "Precise, technical definition",
            "explanation": "Detailed explanation (2-3 paragraphs covering: how it works, why it matters, when to apply, limitations)",
            "example": "Concrete example with actual numbers/values and step-by-step work",
            "key_points": ["Critical point 1", "Critical point 2"],
            "exam_tips": ["Specific mistake to avoid", "Quick check method", "How this appears in tests"]
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "Formula Name",
        "expression": "Full mathematical notation",
        "variables": {{"x": "meaning with units", "y": "meaning with constraints"}},
        "notes": "Derivation intuition, when to use, common errors, worked example"
      }}
    ],
    "glossary": [
      {{"term": "Technical Term", "definition": "Substantive definition with context and relevance"}}
    ],
    "exam_practice": {{
      "multiple_choice": [
        {{
          "question": "Question text testing understanding",
          "options": {{"A": "Option A text", "B": "Option B text", "C": "Option C text", "D": "Option D text"}},
          "correct": "A",
          "explanation": "Why A is correct; why B, C, D are incorrect"
        }}
      ],
      "short_answer": [
        {{"question": "Short answer prompt", "answer": "Expected answer with key points"}}
      ],
      "problem_solving": [
        {{"prompt": "Problem description", "solution": "Step-by-step solution showing all work", "answer": "Final answer with units"}}
      ]
    }}
  }},
  "citations": [
    {{"file_id": "source", "evidence": "Where this information came from"}}
  ]
}}

🔍 PRE-FINALIZATION CHECKLIST:
✔ Coverage — every major topic from the material is represented
✔ Depth — each concept has explanation + example + exam tip
✔ Accuracy — formulas consistent with text; variables defined
✔ Completeness — exam_practice ≥4 MCQ, ≥3 short-answer, ≥2 problems
✔ Glossary — ≥8 terms with substantive definitions
✔ JSON validity — all brackets and arrays closed; no markdown fences

OUTPUT PURE JSON NOW (no other text):"""


def get_no_files_prompt(topic: str, language: str = "en") -> str:
    """Prompt for generating summary without uploaded files"""
    lang_instr = "Generate in TURKISH." if language == "tr" else "Generate in ENGLISH."
    
    return f"""Create a comprehensive study guide on this topic: {topic}

{lang_instr}

Use the same JSON structure as file-based summaries. Include exam-ready content:
- Learning objectives
- Core concepts with explanations and examples  
- Formula sheet (if applicable)
- Glossary of key terms
- Practice questions

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
    out_budget: int = 300
) -> str:
    """
    Summarize a single chunk of text (MAP phase)
    Returns plain text bullet points
    """
    user_prompt = get_chunk_summary_prompt(language)
    
    if additional_instructions:
        user_prompt += f"\n\nUser preferences: {additional_instructions}"
    
    user_prompt += f"\n\nTEXT TO SUMMARIZE:\n{chunk_text}"
    
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
    domain: str = "general"
) -> str:
    """
    Merge chunk summaries into final JSON summary (REDUCE phase)
    Returns JSON string
    """
    # Combine all chunk summaries
    combined = merge_texts(chunk_summaries, separator="\n\n---SECTION BREAK---\n\n")
    
    user_prompt = get_final_merge_prompt(language, additional_instructions, domain)
    user_prompt += f"\n\nSOURCE SUMMARIES:\n{combined}"
    
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
    Includes domain detection and quality guardrails
    
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
    
    # Large document: map-reduce
    print(f"[MAP-REDUCE] Estimated {estimated_tokens} tokens, using chunking")
    
    # 2. SPLIT into chunks
    chunks = split_text_approx_tokens(full_text, CHUNK_INPUT_TARGET)
    print(f"[MAP-REDUCE] Split into {len(chunks)} chunks")
    
    # 3. MAP: Summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"[MAP-REDUCE] Processing chunk {i+1}/{len(chunks)}...")
        summary = summarize_chunk(
            chunk,
            language=language,
            additional_instructions=additional_instructions,
            out_budget=CHUNK_OUTPUT_BUDGET[1]
        )
        chunk_summaries.append(summary)
    
    # 4. REDUCE: Merge into final JSON
    print(f"[MAP-REDUCE] Merging {len(chunk_summaries)} summaries with domain: {domain}...")
    final_summary = merge_summaries(
        chunk_summaries,
        language=language,
        additional_instructions=enhanced_instructions,
        out_budget=min(out_cap, MERGE_OUTPUT_BUDGET[1]),
        domain=domain
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
