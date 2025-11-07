"""
AI-powered summary service with map-reduce for large documents
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

SYSTEM_PROMPT = """You are StudyWithAI, a world-class academic tutor and study guide creator. Your mission is to transform course materials into comprehensive, exam-ready study guides that maximize student learning and retention.

Core Principles:
1. **Exam-Ready Focus**: Structure all content to directly support exam preparation
2. **Active Learning**: Include examples, applications, and practice problems
3. **Clear Hierarchy**: Organize from foundational concepts to advanced applications
4. **Practical Application**: Show how concepts apply in real scenarios
5. **Memory Aids**: Use analogies, mnemonics, and visual descriptions

Your summaries should be:
- Comprehensive yet concise
- Logically structured
- Rich with examples
- Practice-oriented
- Easy to review before exams"""


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


def get_final_merge_prompt(language: str = "en", additional_instructions: str = "") -> str:
    """Prompt for merging chunk summaries into final JSON (reduce phase)"""
    lang_instr = "Generate the ENTIRE summary in TURKISH language." if language == "tr" else "Generate the ENTIRE summary in ENGLISH language."
    
    additional = f"\n\nADDITIONAL USER INSTRUCTIONS:\n{additional_instructions}" if additional_instructions else ""
    
    return f"""Based on the bullet-point summaries provided, create a comprehensive exam-ready study guide.

{lang_instr}{additional}

Output ONLY valid JSON in this EXACT structure (no markdown code blocks):

{{
  "summary": {{
    "title": "Study Guide: [Topic Name]",
    "overview": "2-3 sentence overview of what this material covers",
    "learning_objectives": [
      "Objective 1: What students should be able to do",
      "Objective 2: Key skills or knowledge to master"
    ],
    "sections": [
      {{
        "heading": "Section Title",
        "concepts": [
          {{
            "term": "Concept Name",
            "definition": "Clear, concise definition",
            "explanation": "Detailed explanation with context, 2-3 paragraphs",
            "example": "Concrete example showing application",
            "key_points": ["Important point 1", "Important point 2"]
          }}
        ]
      }}
    ],
    "formula_sheet": [
      {{
        "name": "Formula Name",
        "formula": "Mathematical notation or rule",
        "variables": "What each variable represents",
        "when_to_use": "Application scenarios"
      }}
    ],
    "glossary": [
      {{"term": "Term", "definition": "Quick definition"}}
    ],
    "exam_practice": {{
      "multiple_choice": [
        {{
          "question": "Practice question text",
          "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
          "correct": "A",
          "explanation": "Why this is correct"
        }}
      ],
      "short_answer": [
        {{"question": "Short answer prompt", "key_points": ["Point 1", "Point 2"]}}
      ],
      "problem_solving": [
        {{"problem": "Problem description", "approach": "Solution strategy", "solution": "Step-by-step solution"}}
      ]
    }}
  }},
  "citations": [
    {{"file_id": "source", "evidence": "Where this information came from"}}
  ]
}}

CRITICAL: 
- Output PURE JSON only (no ```json``` markers)
- Include ALL sections from the schema
- Make content exam-focused and actionable
- Use the language specified above for ALL text"""


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
    top_p: float = TOP_P
) -> str:
    """
    Call OpenAI API with given prompts
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
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_output_tokens
    }
    
    print(f"[OPENAI REQUEST] Model: {OPENAI_MODEL}, max_tokens: {max_output_tokens}")
    
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    
    if response.status_code != 200:
        error_detail = response.text[:500]
        raise Exception(f"OpenAI API call failed ({response.status_code}): {error_detail}")
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    finish_reason = result["choices"][0].get("finish_reason")
    print(f"[OPENAI RESPONSE] Returned {len(content)} chars, finish_reason: {finish_reason}")
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
    out_budget: int = 1500
) -> str:
    """
    Merge chunk summaries into final JSON summary (REDUCE phase)
    Returns JSON string
    """
    # Combine all chunk summaries
    combined = merge_texts(chunk_summaries, separator="\n\n---SECTION BREAK---\n\n")
    
    user_prompt = get_final_merge_prompt(language, additional_instructions)
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
    
    Args:
        full_text: Complete text to summarize
        language: Output language (en/tr)
        additional_instructions: User's custom requirements
        out_cap: Maximum output tokens based on plan
        force_chunking: Force map-reduce even for small docs (for testing)
    
    Returns:
        JSON string with complete summary
    """
    # Estimate input tokens
    estimated_tokens = approx_tokens_from_text_len(len(full_text))
    
    # Decide whether to use map-reduce
    # Use chunking if: forced, OR estimated tokens > threshold
    use_chunking = force_chunking or estimated_tokens > 8000
    
    if not use_chunking:
        # Small document: single-pass summary
        user_prompt = get_final_merge_prompt(language, additional_instructions)
        user_prompt += f"\n\nCOURSE MATERIAL:\n{full_text}"
        
        return call_openai(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_output_tokens=min(out_cap, MERGE_OUTPUT_BUDGET[1])
        )
    
    # Large document: map-reduce
    print(f"[MAP-REDUCE] Estimated {estimated_tokens} tokens, using chunking")
    
    # 1. SPLIT into chunks
    chunks = split_text_approx_tokens(full_text, CHUNK_INPUT_TARGET)
    print(f"[MAP-REDUCE] Split into {len(chunks)} chunks")
    
    # 2. MAP: Summarize each chunk
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
    
    # 3. REDUCE: Merge into final JSON
    print(f"[MAP-REDUCE] Merging {len(chunk_summaries)} summaries...")
    final_summary = merge_summaries(
        chunk_summaries,
        language=language,
        additional_instructions=additional_instructions,
        out_budget=min(out_cap, MERGE_OUTPUT_BUDGET[1])
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
