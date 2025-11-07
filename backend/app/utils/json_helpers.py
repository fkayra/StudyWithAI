"""
JSON extraction and repair utilities
"""
import re
import json
from typing import Optional


# Filler patterns to remove from AI outputs
FILLER_PATTERNS = [
    r"\b(review this concept|study carefully|it is important to note that)\b"
]


def defill(text: str) -> str:
    """Remove generic filler phrases from text"""
    out = text
    for pat in FILLER_PATTERNS:
        out = re.sub(pat, "", out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


def extract_json_block(text: str) -> str:
    """
    Extract JSON from text, removing code fences and extra content
    """
    text = text.strip()
    
    # Remove markdown code fences
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    
    # Extract outermost JSON object
    match = re.search(r'\{[\s\S]*\}\s*$', text)
    return match.group(0) if match else text


def balance_braces(json_str: str) -> str:
    """
    Attempt to balance braces in truncated JSON
    """
    json_str = json_str.rstrip()
    
    # Count braces
    open_braces = json_str.count("{")
    close_braces = json_str.count("}")
    open_brackets = json_str.count("[")
    close_brackets = json_str.count("]")
    
    # Add missing closing braces/brackets
    if open_braces > close_braces:
        json_str += "}" * (open_braces - close_braces)
    
    if open_brackets > close_brackets:
        json_str += "]" * (open_brackets - close_brackets)
    
    return json_str


def parse_json_robust(text: str, max_attempts: int = 3) -> dict:
    """
    Robustly parse JSON with multiple fallback strategies
    
    Args:
        text: Raw text that should contain JSON
        max_attempts: Number of repair attempts
    
    Returns:
        Parsed JSON dict
    
    Raises:
        ValueError if all parsing attempts fail
    """
    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e1:
        print(f"[JSON PARSE] Attempt 1 failed: {e1}")
    
    # Attempt 2: Extract and parse
    try:
        extracted = extract_json_block(text)
        return json.loads(extracted)
    except json.JSONDecodeError as e2:
        print(f"[JSON PARSE] Attempt 2 failed: {e2}")
    
    # Attempt 3: Balance braces and parse
    try:
        extracted = extract_json_block(text)
        balanced = balance_braces(extracted)
        return json.loads(balanced)
    except json.JSONDecodeError as e3:
        print(f"[JSON PARSE] Attempt 3 failed: {e3}")
    
    # Attempt 4: Try to find largest valid JSON object
    try:
        # Start from beginning, try progressively smaller substrings
        extracted = extract_json_block(text)
        for i in range(len(extracted), len(extracted) // 2, -100):
            candidate = balance_braces(extracted[:i])
            try:
                return json.loads(candidate)
            except:
                continue
    except Exception as e4:
        print(f"[JSON PARSE] Attempt 4 failed: {e4}")
    
    # All attempts failed
    raise ValueError(f"Failed to parse JSON after {max_attempts} attempts. Text length: {len(text)}")


def create_error_response(error_message: str, response_length: int = 0) -> dict:
    """
    Create standardized error response
    """
    return {
        "summary": {
            "title": "Summary Generation Error",
            "overview": "An error occurred while generating the summary.",
            "sections": [{
                "heading": "Error Details",
                "concepts": [{
                    "term": "Error",
                    "definition": error_message,
                    "explanation": f"The AI response could not be parsed. Response length: {response_length} characters.",
                    "key_points": [
                        "Try with a shorter document or fewer files",
                        "If the problem persists, contact support"
                    ]
                }]
            }]
        },
        "citations": []
    }
