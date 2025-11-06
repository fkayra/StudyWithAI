"""
Text chunking utilities for map-reduce summarization
"""
from typing import List


def split_text_approx_tokens(
    text: str,
    chunk_tokens: int = 2400,
    token_per_char: float = 0.25
) -> List[str]:
    """
    Split text into chunks of approximately chunk_tokens size
    Uses character-based approximation (4 chars ≈ 1 token)
    Tries to break at paragraph boundaries when possible
    """
    if not text:
        return []
    
    chars_per_chunk = int(chunk_tokens / token_per_char)
    chunks = []
    i = 0
    n = len(text)
    
    while i < n:
        # Calculate end position for this chunk
        j = min(n, i + chars_per_chunk)
        
        # Try to find a good break point (paragraph boundary)
        if j < n:  # Not at end of text
            # Look for double newline (paragraph break) in last 50% of chunk
            search_start = i + int(0.5 * (j - i))
            k = text.rfind("\n\n", search_start, j)
            
            # If no paragraph break found, try single newline
            if k == -1 or k <= i:
                k = text.rfind("\n", search_start, j)
            
            # If still no break found, try sentence ending
            if k == -1 or k <= i:
                for punct in [". ", "! ", "? "]:
                    k = text.rfind(punct, search_start, j)
                    if k != -1 and k > i:
                        k += len(punct)  # Include the punctuation
                        break
            
            # Use the break point if found, otherwise use calculated position
            if k != -1 and k > i:
                j = k
        
        chunk = text[i:j].strip()
        if chunk:
            chunks.append(chunk)
        
        i = j
    
    return chunks


def merge_texts(texts: List[str], separator: str = "\n\n") -> str:
    """
    Merge multiple texts with separator
    Useful for combining chunk summaries
    """
    return separator.join([t.strip() for t in texts if t.strip()])


def estimate_chunks_needed(text_length: int, chunk_tokens: int = 2400, token_per_char: float = 0.25) -> int:
    """
    Estimate how many chunks will be needed for given text
    """
    total_tokens = int(text_length * token_per_char)
    return max(1, (total_tokens + chunk_tokens - 1) // chunk_tokens)
