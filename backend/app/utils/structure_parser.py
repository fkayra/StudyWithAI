"""
Structure-aware document parsing
Extracts headings, sections, formulas, and examples from documents
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ContentBlock:
    """Represents a structured block of content with metadata"""
    block_type: str  # 'heading', 'text', 'formula', 'theorem', 'example', 'list'
    content: str
    heading_path: List[str]  # ["Chapter 1", "Section 1.1", ...]
    page_number: Optional[int] = None
    level: int = 0  # Heading level (1=H1, 2=H2, etc.)
    metadata: Dict = None



def _looks_like_heading(line: str) -> Tuple[bool, int]:
    """
    Strong, noise-resistant heading detector.
    """
    s = line.strip()

    if not s:
        return False, 0

    # bullet → heading değil
    if s[0] in "-•*·" or "•" in s:
        return False, 0

    # çok kısa veya çok uzun → heading değil
    if len(s) < 3 or len(s) > 120:
        return False, 0

    words = s.split()
    if len(words) == 1 and len(words[0]) <= 3:
        return False, 0

    # tamamen küçük harfli → heading değil
    if s == s.lower() and len(words) > 3:
        return False, 0

    # cümle sonu noktalama → heading değil
    if s[-1] in ".!?":
        return False, 0

    # özel anahtar kelimeler
    if re.match(r'^(Chapter|Section|Theorem|Lemma|Definition|Example|Algorithm)\b', s, flags=re.I):
        return True, 2

    # ALL CAPS → H1
    if s.isupper() and len(words) >= 2:
        return True, 1

    # Title Case + ":" → heading
    if s.endswith(":") and s[0].isupper():
        return True, 2

    return False, 0



def extract_heading_hierarchy(text: str) -> List[ContentBlock]:
    """
    Extracts headings using ONLY the new modern _looks_like_heading().
    All old heading heuristics REMOVED (numbered_section, keyword_heading, ALL CAPS checks, etc.)
    """
    blocks = []
    lines = text.split('\n')

    current_heading_path = []
    current_level = 0
    accumulated_text = []

    for line in lines:
        s = line.strip()
        if not s:
            continue

        is_heading, heading_level = _looks_like_heading(s)
        heading_text = s if is_heading else None

        if is_heading:
            # Accumulated text flush
            if accumulated_text:
                blocks.append(ContentBlock(
                    block_type="text",
                    content="\n".join(accumulated_text),
                    heading_path=current_heading_path.copy(),
                    level=current_level
                ))
                accumulated_text = []

            # Heading hierarchy update
            if heading_level <= current_level:
                current_heading_path = current_heading_path[:heading_level - 1]

            current_heading_path.append(heading_text)
            current_level = heading_level

            blocks.append(ContentBlock(
                block_type="heading",
                content=heading_text,
                heading_path=current_heading_path.copy(),
                level=heading_level
            ))

        else:
            accumulated_text.append(line)

    # flush final text block
    if accumulated_text:
        blocks.append(ContentBlock(
            block_type="text",
            content="\n".join(accumulated_text),
            heading_path=current_heading_path.copy(),
            level=current_level
        ))

    return blocks



def chunk_by_headings(
    blocks: List[ContentBlock],
    target_tokens: int = 3500,
    min_chunk_tokens: int = 1000,
    approx_chars_per_token: float = 4.0
) -> List[Tuple[List[ContentBlock], str]]:
    """
    Chunk blocks by heading boundaries.
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_heading_path = []

    for block in blocks:
        block_tokens = len(block.content) / approx_chars_per_token

        if current_tokens + block_tokens > target_tokens and current_tokens > min_chunk_tokens:
            if block.block_type == "heading":
                heading_str = " > ".join(current_heading_path) if current_heading_path else "Introduction"
                chunks.append((current_chunk, heading_str))

                current_chunk = [block]
                current_tokens = block_tokens
                current_heading_path = block.heading_path.copy()
                continue

        current_chunk.append(block)
        current_tokens += block_tokens

        if block.block_type == "heading":
            current_heading_path = block.heading_path.copy()

    if current_chunk:
        heading_str = " > ".join(current_heading_path) if current_heading_path else "Content"
        chunks.append((current_chunk, heading_str))

    return chunks



def blocks_to_text(blocks: List[ContentBlock]) -> str:
    """
    Converts structured blocks back to annotated text.
    """
    lines = []
    for block in blocks:
        if block.block_type == 'heading':
            heading_path_str = " > ".join(block.heading_path)
            lines.append(f"\n## {heading_path_str}\n")
            lines.append(block.content)
            lines.append("")
        else:
            lines.append(block.content)

    return "\n".join(lines)



def extract_formulas_and_examples(text: str) -> Dict[str, List[str]]:
    """
    Extract formulas / examples / theorems using simple heuristics.
    """
    result = {
        "formulas": [],
        "examples": [],
        "theorems": []
    }

    lines = text.split("\n")

    formula_ind = re.compile(r'[=∫∑∂√∏Δ∇]|\b(integral|sum|derivative|equation|formula)\b', re.IGNORECASE)
    example_ind = re.compile(r'^\s*(Example|Ex\.|Instance|Case Study|Scenario)[\s:\d.]*', re.IGNORECASE)
    theorem_ind = re.compile(r'^\s*(Theorem|Lemma|Proposition|Corollary|Property)[\s:\d.]*', re.IGNORECASE)

    current_type = None
    accumulated = []

    for line in lines:
        if example_ind.match(line):
            if accumulated and current_type:
                result[current_type].append("\n".join(accumulated))
            current_type = "examples"
            accumulated = [line]
        elif theorem_ind.match(line):
            if accumulated and current_type:
                result[current_type].append("\n".join(accumulated))
            current_type = "theorems"
            accumulated = [line]
        elif formula_ind.search(line):
            if current_type != "formulas":
                if accumulated and current_type:
                    result[current_type].append("\n".join(accumulated))
                current_type = "formulas"
                accumulated = [line]
            else:
                accumulated.append(line)
        elif accumulated:
            accumulated.append(line)
            if len(accumulated) > 10 or not line.strip():
                if current_type:
                    result[current_type].append("\n".join(accumulated))
                current_type = None
                accumulated = []

    if accumulated and current_type:
        result[current_type].append("\n".join(accumulated))

    return result
