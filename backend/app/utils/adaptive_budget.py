"""
Adaptive token budget allocation based on content density
"""
from app.config import CHUNK_OUTPUT_BASE, CHUNK_OUTPUT_FORMULA_BOOST, CHUNK_OUTPUT_THEOREM_BOOST


def calculate_chunk_budget(chunk_text: str) -> int:
    """
    Calculate appropriate output budget for a chunk based on content density
    
    Heuristics:
    - Base: 400 tokens for regular text
    - +150 if chunk contains formulas/equations
    - +200 if chunk contains theorems/proofs/algorithms
    
    Returns: Recommended max_output_tokens for this chunk
    """
    text_lower = chunk_text.lower()
    
    budget = CHUNK_OUTPUT_BASE
    
    # Check for formula indicators
    formula_indicators = ["equation", "formula", "=", "∫", "∑", "∂", "calculate", "solve"]
    if any(indicator in text_lower for indicator in formula_indicators):
        budget += CHUNK_OUTPUT_FORMULA_BOOST
    
    # Check for theorem/proof indicators
    theorem_indicators = ["theorem", "proof", "lemma", "proposition", "algorithm", "procedure"]
    if any(indicator in text_lower for indicator in theorem_indicators):
        budget += CHUNK_OUTPUT_THEOREM_BOOST
    
    # Cap at reasonable maximum
    budget = min(budget, 800)
    
    return budget


def distribute_merge_budget(
    total_concepts: int,
    total_formulas: int,
    total_theorems: int,
    max_budget: int
) -> dict:
    """
    Distribute merge budget across different output components
    
    Args:
        total_concepts: Number of concepts from MAP phase
        total_formulas: Number of formulas from MAP phase
        total_theorems: Number of theorems from MAP phase
        max_budget: Maximum total tokens available
    
    Returns:
        Dict with recommended token allocation per component
    """
    # Minimum allocations
    min_per_concept = 80
    min_per_formula = 100
    min_per_theorem = 120
    
    # Calculate minimum needed
    min_needed = (
        total_concepts * min_per_concept +
        total_formulas * min_per_formula +
        total_theorems * min_per_theorem +
        500  # Base for overview, objectives, exam practice
    )
    
    if min_needed >= max_budget:
        # Scale down proportionally
        scale = max_budget / min_needed
        return {
            "per_concept": int(min_per_concept * scale),
            "per_formula": int(min_per_formula * scale),
            "per_theorem": int(min_per_theorem * scale),
            "base": max(200, int(500 * scale))
        }
    
    # We have budget surplus, distribute generously
    surplus = max_budget - min_needed
    
    # Give extra tokens proportionally to content density
    total_items = total_concepts + total_formulas + total_theorems
    
    if total_items == 0:
        # Fallback if no structured content
        return {
            "per_concept": 100,
            "per_formula": 150,
            "per_theorem": 180,
            "base": max_budget - 1000
        }
    
    extra_per_item = surplus // total_items
    
    return {
        "per_concept": min_per_concept + extra_per_item,
        "per_formula": min_per_formula + extra_per_item,
        "per_theorem": min_per_theorem + extra_per_item,
        "base": 500
    }
