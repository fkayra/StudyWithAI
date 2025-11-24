"""
Structure-aware document parsing
Extracts headings, sections, formulas, and examples from documents
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ContentBlock:
    block_type: str      # 'heading', 'text', 'formula', 'example', 'theorem'
    content: str
    heading_path: List[str]
    page_number: Optional[int] = None
    level: int = 0
    metadata: Dict = None


# ===========================================================
# RELAXED, SMART HEADING DETECTOR  (THE MOST CRITICAL PART)
# ===========================================================
def _looks_like_heading(line: str) -> Tuple[bool, int]:
    s = line.strip()

    if not s:
        return False, 0

    # Hard reject bullets
    if s.startswith(("-", "*", "•", "·")):
        return False, 0

    # Numbered (1.1, 2.3.4)
    num_match = re.match(r'^(\d+\.)+\d*\s+.+$', s)
    if num_match:
        depth = s.count(".")
        return True, min(depth + 1, 5)

    # Common academic keywords
    if re.match(r'^(Example|Problem|Chapter|Section|Definition|Theorem|Lemma|Algorithm)\b', s, flags=re.I):
        return True, 2

    # RELAXED rules:
    # If it starts with uppercase and is short, it's very likely a heading
    words = s.split()
    if (
        s[0].isupper()
        and len(words) <= 12
        and 5 <= len(s) <= 120
    ):
        return True, 2

    return False, 0


# ===========================================================
# MAIN HEADİNG + TEXT EXTRACTOR
# ===========================================================
def extract_heading_hierarchy(text: str) -> List[ContentBlock]:
    blocks: List[ContentBlock] = []
    lines = text.split("\n")

    current_heading_path = []
    current_level = 0
    accumulated_text = []

    for line in lines:
        stripped = line.strip()

        is_heading, heading_level = _looks_like_heading(stripped)

        if is_heading:
            # flush text
            if accumulated_text:
                blocks.append(ContentBlock(
                    block_type="text",
                    content="\n".join(accumulated_text),
                    heading_path=current_heading_path.copy(),
                    level=current_level
                ))
                accumulated_text = []

            # adjust heading path
            if heading_level <= current_level:
                current_heading_path = current_heading_path[:heading_level - 1]

            current_heading_path.append(stripped)
            current_level = heading_level

            blocks.append(ContentBlock(
                block_type="heading",
                content=stripped,
                heading_path=current_heading_path.copy(),
                level=heading_level
            ))
        else:
            accumulated_text.append(line)

    # flush last text
    if accumulated_text:
        blocks.append(ContentBlock(
            block_type="text",
            content="\n".join(accumulated_text),
            heading_path=current_heading_path.copy(),
            level=current_level
        ))

    return blocks


# ===========================================================
# STRUCTURE-AWARE CHUNKING (MORE CHUNKS = BETTER SUMMARY)
# ===========================================================
def chunk_by_headings(
    blocks: List[ContentBlock],
    target_tokens: int = 900,
    min_chunk_tokens: int = 250,
    approx_chars_per_token: float = 4.0
):
    chunks = []
    current = []
    tokens = 0
    current_heading = []

    for block in blocks:
        block_tokens = len(block.content) / approx_chars_per_token

        if tokens + block_tokens > target_tokens and tokens > min_chunk_tokens:
            chunks.append((current, " > ".join(current_heading)))
            current = [block]
            tokens = block_tokens
            if block.block_type == "heading":
                current_heading = block.heading_path.copy()
            continue

        current.append(block)
        tokens += block_tokens

        if block.block_type == "heading":
            current_heading = block.heading_path.copy()

    if current:
        chunks.append((current, " > ".join(current_heading)))

    return chunks


# ===========================================================
# CONVERT BLOCKS TO RAW TEXT FOR MODEL INPUT
# ===========================================================
def blocks_to_text(blocks: List[ContentBlock]) -> str:
    lines = []
    for b in blocks:
        if b.block_type == "heading":
            lines.append(f"\n## {' > '.join(b.heading_path)}\n")
        lines.append(b.content)
    return "\n".join(lines)


# ===========================================================
# FORMULA + EXAMPLE EXTRACTOR
# ===========================================================
def extract_formulas_and_examples(text: str) -> Dict[str, List[str]]:
    result = {"formulas": [], "examples": [], "theorems": []}

    lines = text.split("\n")
    current_type = None
    buf = []

    formula_re = re.compile(r'[=∫∑∂√∏Δ∇]|(equation|formula|derivative|integral)', re.I)
    example_re = re.compile(r'^(Example|Scenario|Case Study)\b', re.I)
    theorem_re = re.compile(r'^(Theorem|Lemma|Proposition)\b', re.I)

    for line in lines:
        stripped = line.strip()

        if example_re.match(stripped):
            if buf and current_type:
                result[current_type].append("\n".join(buf))
            current_type = "examples"
            buf = [line]
        elif theorem_re.match(stripped):
            if buf and current_type:
                result[current_type].append("\n".join(buf))
            current_type = "theorems"
            buf = [line]
        elif formula_re.search(stripped):
            if current_type != "formulas":
                if buf and current_type:
                    result[current_type].append("\n".join(buf))
                current_type = "formulas"
                buf = [line]
            else:
                buf.append(line)
        else:
            if current_type:
                buf.append(line)
                if len(buf) > 10 or stripped == "":
                    result[current_type].append("\n".join(buf))
                    buf = []
                    current_type = None

    if buf and current_type:
        result[current_type].append("\n".join(buf))

    return result
