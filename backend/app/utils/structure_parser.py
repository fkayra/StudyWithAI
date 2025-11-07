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


def extract_heading_hierarchy(text: str) -> List[ContentBlock]:
    """
    Extract heading hierarchy and content blocks from text
    
    Heuristics:
    - Lines in ALL CAPS with < 100 chars = heading
    - Lines ending with ":" = potential heading
    - Numbered sections (1.1, 1.2.3, etc.)
    - Keywords: "Chapter", "Section", "Definition", "Theorem", "Example", "Proof"
    """
    blocks = []
    lines = text.split('\n')
    
    current_heading_path = []
    current_level = 0
    accumulated_text = []
    
    # Patterns
    numbered_section = re.compile(r'^(\d+\.)+\d*\s+(.+)$')  # 1.1 Title, 2.3.4 Title
    keyword_heading = re.compile(r'^(Chapter|Section|Part|Theorem|Lemma|Definition|Example|Proof|Algorithm|Procedure)\s+[\d\w.]*:?\s*(.*)$', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        is_heading = False
        heading_text = None
        heading_level = 0
        
        # Check 1: Numbered sections (1.1, 2.3.4)
        num_match = numbered_section.match(line_stripped)
        if num_match:
            section_num = num_match.group(1).count('.')
            heading_text = line_stripped
            heading_level = min(section_num + 1, 5)
            is_heading = True
        
        # Check 2: Keyword headings (Theorem 3.1, Example 2, etc.)
        elif keyword_heading.match(line_stripped):
            keyword_match = keyword_heading.match(line_stripped)
            heading_text = line_stripped
            heading_level = 2  # Sub-heading
            is_heading = True
        
        # Check 3: ALL CAPS (and not too long)
        elif line_stripped.isupper() and len(line_stripped) < 100 and len(line_stripped.split()) > 1:
            heading_text = line_stripped.title()  # Convert to title case
            heading_level = 1
            is_heading = True
        
        # Check 4: Line ending with : (potential heading)
        elif line_stripped.endswith(':') and len(line_stripped) < 80 and len(line_stripped.split()) > 1:
            heading_text = line_stripped[:-1]  # Remove trailing :
            heading_level = 3
            is_heading = True
        
        if is_heading and heading_text:
            # Flush accumulated text
            if accumulated_text:
                text_content = '\n'.join(accumulated_text)
                blocks.append(ContentBlock(
                    block_type='text',
                    content=text_content,
                    heading_path=current_heading_path.copy(),
                    level=current_level
                ))
                accumulated_text = []
            
            # Update heading path
            if heading_level <= current_level:
                # Pop back to parent level
                current_heading_path = current_heading_path[:heading_level-1]
            
            current_heading_path.append(heading_text)
            current_level = heading_level
            
            # Add heading block
            blocks.append(ContentBlock(
                block_type='heading',
                content=heading_text,
                heading_path=current_heading_path.copy(),
                level=heading_level
            ))
        else:
            # Accumulate text
            accumulated_text.append(line)
    
    # Flush remaining text
    if accumulated_text:
        text_content = '\n'.join(accumulated_text)
        blocks.append(ContentBlock(
            block_type='text',
            content=text_content,
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
    Chunk blocks by heading boundaries, respecting structure
    
    Returns: List of (blocks_in_chunk, heading_path_str)
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_heading_path = []
    
    for block in blocks:
        block_tokens = len(block.content) / approx_chars_per_token
        
        # If adding this block exceeds target AND we have minimum chunk size
        if current_tokens + block_tokens > target_tokens and current_tokens > min_chunk_tokens:
            # If it's a heading, break here (clean boundary)
            if block.block_type == 'heading':
                # Save current chunk
                heading_str = " > ".join(current_heading_path) if current_heading_path else "Introduction"
                chunks.append((current_chunk, heading_str))
                
                # Start new chunk
                current_chunk = [block]
                current_tokens = block_tokens
                current_heading_path = block.heading_path.copy()
                continue
        
        # Add block to current chunk
        current_chunk.append(block)
        current_tokens += block_tokens
        
        # Update heading path if this is a heading
        if block.block_type == 'heading':
            current_heading_path = block.heading_path.copy()
    
    # Add final chunk
    if current_chunk:
        heading_str = " > ".join(current_heading_path) if current_heading_path else "Content"
        chunks.append((current_chunk, heading_str))
    
    return chunks


def blocks_to_text(blocks: List[ContentBlock]) -> str:
    """Convert blocks back to text for processing"""
    lines = []
    for block in blocks:
        if block.block_type == 'heading':
            # Add heading with context
            heading_path_str = " > ".join(block.heading_path)
            lines.append(f"\n### [{heading_path_str}]\n")
            lines.append(block.content)
            lines.append("")
        else:
            lines.append(block.content)
    
    return '\n'.join(lines)


def extract_formulas_and_examples(text: str) -> Dict[str, List[str]]:
    """
    Extract formulas and examples from text using heuristics
    
    Returns: {"formulas": [...], "examples": [...], "theorems": [...]}
    """
    result = {
        "formulas": [],
        "examples": [],
        "theorems": []
    }
    
    lines = text.split('\n')
    
    # Pattern detection
    formula_indicators = re.compile(r'[=∫∑∂√∏Δ∇]|\b(integral|sum|derivative|equation|formula)\b', re.IGNORECASE)
    example_indicators = re.compile(r'^\s*(Example|Ex\.|Instance|Case Study|Scenario)[\s:\d.]*', re.IGNORECASE)
    theorem_indicators = re.compile(r'^\s*(Theorem|Lemma|Proposition|Corollary|Property)[\s:\d.]*', re.IGNORECASE)
    
    current_type = None
    accumulated = []
    
    for line in lines:
        # Check for markers
        if example_indicators.match(line):
            if accumulated and current_type:
                result[current_type].append('\n'.join(accumulated))
            current_type = "examples"
            accumulated = [line]
        elif theorem_indicators.match(line):
            if accumulated and current_type:
                result[current_type].append('\n'.join(accumulated))
            current_type = "theorems"
            accumulated = [line]
        elif formula_indicators.search(line):
            if current_type != "formulas":
                if accumulated and current_type:
                    result[current_type].append('\n'.join(accumulated))
                current_type = "formulas"
                accumulated = [line]
            else:
                accumulated.append(line)
        elif accumulated:
            accumulated.append(line)
            # End block after 10 lines or empty line
            if len(accumulated) > 10 or not line.strip():
                if current_type:
                    result[current_type].append('\n'.join(accumulated))
                current_type = None
                accumulated = []
    
    # Flush remaining
    if accumulated and current_type:
        result[current_type].append('\n'.join(accumulated))
    
    return result
