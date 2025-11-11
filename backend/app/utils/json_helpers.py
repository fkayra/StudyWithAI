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


def detect_empty_fields(parsed_json: dict) -> list:
    """
    Detect critical empty fields that should trigger self-repair.
    
    Args:
        parsed_json: Parsed JSON dict
    
    Returns:
        List of field paths that are empty/missing (e.g., ["summary.learning_objectives", "summary.glossary"])
    """
    empty_fields = []
    
    if "summary" not in parsed_json:
        return ["summary"]
    
    summary = parsed_json["summary"]
    
    # Check critical arrays that should have content
    critical_arrays = {
        "learning_objectives": 2,  # Min 2 objectives
        "sections": 2,             # Min 2 sections
        # NOTE: glossary removed in favor of diagrams/pseudocode/practice
    }
    
    for field, min_count in critical_arrays.items():
        if field not in summary:
            empty_fields.append(f"summary.{field}")
        elif not summary[field] or len(summary[field]) < min_count:
            empty_fields.append(f"summary.{field} (has {len(summary.get(field, []))}, need {min_count})")
    
    # Check sections for empty concepts
    sections = summary.get("sections", [])
    for i, section in enumerate(sections):
        if "concepts" not in section or not section["concepts"]:
            empty_fields.append(f"summary.sections[{i}].concepts")
    
    # Check formulas for incomplete structure
    formulas = summary.get("formula_sheet", [])
    for i, formula in enumerate(formulas):
        if not formula.get("expression"):
            empty_fields.append(f"summary.formula_sheet[{i}].expression")
        if not formula.get("variables"):
            empty_fields.append(f"summary.formula_sheet[{i}].variables")
    
    return empty_fields


def fix_escape_sequences(text: str) -> str:
    """
    Fix common escape sequence issues in JSON, especially LaTeX formulas
    
    Strategy: Replace ALL backslashes with double backslashes in string values,
    but preserve valid JSON escape sequences (\n, \t, \", \\, etc.)
    """
    import re
    
    # Valid JSON escape sequences we want to preserve
    VALID_ESCAPES = {'n', 't', 'r', 'b', 'f', '"', '/', '\\', 'u'}
    
    # Strategy: Find all string values and fix backslashes within them
    # Match strings: "..." (but not escaped quotes \")
    def fix_string_backslashes(match):
        string_content = match.group(1)
        
        # Process character by character to handle backslashes correctly
        result = []
        i = 0
        while i < len(string_content):
            if string_content[i] == '\\':
                # Check what follows the backslash
                if i + 1 < len(string_content):
                    next_char = string_content[i + 1]
                    
                    # If it's a valid JSON escape, keep it as-is
                    if next_char in VALID_ESCAPES:
                        result.append('\\')
                        result.append(next_char)
                        i += 2
                    # If it's u followed by 4 hex digits (unicode escape), keep it
                    elif next_char == 'u' and i + 5 < len(string_content):
                        if all(c in '0123456789abcdefABCDEF' for c in string_content[i+2:i+6]):
                            result.append(string_content[i:i+6])
                            i += 6
                        else:
                            # Not valid unicode, double the backslash
                            result.append('\\\\')
                            i += 1
                    else:
                        # Invalid escape sequence (like \(, \), \[, etc.)
                        # Double the backslash
                        result.append('\\\\')
                        i += 1
                else:
                    # Backslash at end of string - double it
                    result.append('\\\\')
                    i += 1
            else:
                result.append(string_content[i])
                i += 1
        
        return '"' + ''.join(result) + '"'
    
    # Match JSON string values: "..." 
    # Negative lookbehind to avoid already-escaped quotes
    pattern = r'"((?:[^"\\]|\\.)*)(?<!\\)"'
    
    try:
        fixed = re.sub(pattern, fix_string_backslashes, text)
        return fixed
    except Exception as e:
        print(f"[ESCAPE FIX] Error: {e}, falling back to simple replacement")
        # Fallback: simple double-backslash replacement (less accurate but safe)
        return text.replace('\\', '\\\\')


def parse_json_robust(text: str, max_attempts: int = 3) -> dict:
    """
    Robustly parse JSON with multiple fallback strategies
    
    Args:
        text: Raw text that should contain JSON
        max_attempts: Number of repair attempts
    
    Returns:
        Parsed JSON dict with empty_fields_detected flag if issues found
    
    Raises:
        ValueError if all parsing attempts fail
    """
    # Attempt 1: Direct parse
    try:
        parsed = json.loads(text)
        # Check for empty fields
        empty_fields = detect_empty_fields(parsed)
        if empty_fields:
            parsed["_empty_fields_detected"] = empty_fields
            print(f"[JSON VALIDATION] Empty fields detected: {empty_fields}")
        return parsed
    except json.JSONDecodeError as e1:
        print(f"[JSON PARSE] Attempt 1 failed: {e1}")
    
    # Attempt 2: Fix escape sequences and parse
    try:
        fixed = fix_escape_sequences(text)
        parsed = json.loads(fixed)
        empty_fields = detect_empty_fields(parsed)
        if empty_fields:
            parsed["_empty_fields_detected"] = empty_fields
        print(f"[JSON PARSE] Attempt 2 succeeded (fixed escape sequences)")
        return parsed
    except json.JSONDecodeError as e2:
        print(f"[JSON PARSE] Attempt 2 failed: {e2}")
    
    # Attempt 3: Extract and parse
    try:
        extracted = extract_json_block(text)
        parsed = json.loads(extracted)
        empty_fields = detect_empty_fields(parsed)
        if empty_fields:
            parsed["_empty_fields_detected"] = empty_fields
        return parsed
    except json.JSONDecodeError as e3:
        print(f"[JSON PARSE] Attempt 3 failed: {e3}")
    
    # Attempt 4: Extract, fix escapes, and parse
    try:
        extracted = extract_json_block(text)
        fixed = fix_escape_sequences(extracted)
        parsed = json.loads(fixed)
        empty_fields = detect_empty_fields(parsed)
        if empty_fields:
            parsed["_empty_fields_detected"] = empty_fields
        print(f"[JSON PARSE] Attempt 4 succeeded (extract + fix escapes)")
        return parsed
    except json.JSONDecodeError as e4:
        print(f"[JSON PARSE] Attempt 4 failed: {e4}")
    
    # Attempt 5: Balance braces and parse
    try:
        extracted = extract_json_block(text)
        balanced = balance_braces(extracted)
        fixed = fix_escape_sequences(balanced)
        parsed = json.loads(fixed)
        empty_fields = detect_empty_fields(parsed)
        if empty_fields:
            parsed["_empty_fields_detected"] = empty_fields
        print(f"[JSON PARSE] Attempt 5 succeeded (balance + fix escapes)")
        return parsed
    except json.JSONDecodeError as e5:
        print(f"[JSON PARSE] Attempt 5 failed: {e5}")
    
    # Attempt 6: Try to find largest valid JSON object
    try:
        # Start from beginning, try progressively smaller substrings
        extracted = extract_json_block(text)
        for i in range(len(extracted), len(extracted) // 2, -100):
            candidate = balance_braces(extracted[:i])
            fixed = fix_escape_sequences(candidate)
            try:
                parsed = json.loads(fixed)
                empty_fields = detect_empty_fields(parsed)
                if empty_fields:
                    parsed["_empty_fields_detected"] = empty_fields
                print(f"[JSON PARSE] Attempt 6 succeeded (progressive truncation)")
                return parsed
            except:
                continue
    except Exception as e6:
        print(f"[JSON PARSE] Attempt 6 failed: {e6}")
    
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
