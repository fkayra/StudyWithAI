"""
Coverage validation to ensure no topics are skipped
Extracts all headings/topics from source and verifies they appear in summary
"""
import re
from typing import List, Dict, Set
from difflib import SequenceMatcher


def extract_source_topics(text: str) -> List[str]:
    """
    Extract all potential topics/headings from source material
    Returns list of topic strings found in the document
    """
    topics = []
    
    # Pattern 1: Markdown-style headings (# Heading, ## Heading, etc.)
    markdown_headings = re.findall(r'^#{1,6}\s+(.+)$', text, re.MULTILINE)
    topics.extend(markdown_headings)
    
    # Pattern 2: Numbered sections (1. Topic, 1.1 Topic, etc.)
    numbered_sections = re.findall(r'^\d+(?:\.\d+)*\.?\s+([A-Z][^\n]{10,100})$', text, re.MULTILINE)
    topics.extend(numbered_sections)
    
    # Pattern 3: ALL CAPS headings (at least 3 words)
    caps_headings = re.findall(r'^([A-Z][A-Z\s]{15,100})$', text, re.MULTILINE)
    topics.extend([h.strip() for h in caps_headings])
    
    # Pattern 4: Underlined headings (text followed by ===== or -----)
    underlined = re.findall(r'^(.+)\n[=\-]{3,}$', text, re.MULTILINE)
    topics.extend(underlined)
    
    # Pattern 5: Bold headings in common formats (**Text** or __Text__)
    bold_headings = re.findall(r'\*\*([^*]{10,100})\*\*|\__([^_]{10,100})\__', text)
    for match in bold_headings:
        topics.append(match[0] or match[1])
    
    # Pattern 6: Lines ending with colon (often section introductions)
    colon_headings = re.findall(r'^([A-Z][^\n:]{10,80}):$', text, re.MULTILINE)
    topics.extend(colon_headings)
    
    # Clean and deduplicate
    topics = [t.strip() for t in topics if t and len(t.strip()) > 3]
    topics = list(dict.fromkeys(topics))  # Remove duplicates while preserving order
    
    return topics


def extract_summary_topics(summary_json: dict) -> List[str]:
    """
    Extract all topics/concepts from generated summary
    Returns list of topic strings found in the summary
    """
    topics = []
    
    summary_data = summary_json.get("summary", {})
    
    # Extract section headings
    for section in summary_data.get("sections", []):
        heading = section.get("heading", "")
        if heading:
            topics.append(heading)
        
        # Extract concept names
        for concept in section.get("concepts", []):
            term = concept.get("term", "")
            if term:
                topics.append(term)
    
    # Extract formula names
    for formula in summary_data.get("formula_sheet", []):
        name = formula.get("name", "")
        if name:
            topics.append(name)
    
    # Extract glossary terms
    for term in summary_data.get("glossary", []):
        term_text = term.get("term", "")
        if term_text:
            topics.append(term_text)
    
    return topics


def similarity_score(a: str, b: str) -> float:
    """
    Calculate similarity between two strings (0.0 to 1.0)
    Uses SequenceMatcher for fuzzy matching
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_missing_topics(source_topics: List[str], summary_topics: List[str], threshold: float = 0.7) -> List[str]:
    """
    Find topics from source that don't appear in summary
    
    Args:
        source_topics: Topics extracted from original document
        summary_topics: Topics extracted from generated summary
        threshold: Minimum similarity score to consider a match (0.7 = 70% similar)
    
    Returns:
        List of source topics that appear to be missing from summary
    """
    missing = []
    
    for source_topic in source_topics:
        # Check if this source topic matches any summary topic
        best_match_score = 0.0
        for summary_topic in summary_topics:
            score = similarity_score(source_topic, summary_topic)
            if score > best_match_score:
                best_match_score = score
        
        # If best match is below threshold, consider it missing
        if best_match_score < threshold:
            missing.append(source_topic)
    
    return missing


def calculate_coverage_score(source_topics: List[str], summary_topics: List[str], threshold: float = 0.7) -> float:
    """
    Calculate what percentage of source topics are covered in summary
    
    Returns:
        Float between 0.0 and 1.0 representing coverage percentage
    """
    if not source_topics:
        return 1.0  # No topics to cover = 100% coverage
    
    matched_count = 0
    for source_topic in source_topics:
        for summary_topic in summary_topics:
            if similarity_score(source_topic, summary_topic) >= threshold:
                matched_count += 1
                break  # Found a match, move to next source topic
    
    return matched_count / len(source_topics)


def validate_coverage(source_text: str, summary_json: dict, min_coverage: float = 0.85) -> Dict:
    """
    Main coverage validation function
    
    Args:
        source_text: Original document text
        summary_json: Generated summary in JSON format
        min_coverage: Minimum acceptable coverage (0.85 = 85%)
    
    Returns:
        Dict with:
        - passed: bool (whether coverage meets minimum)
        - coverage_score: float (0.0 to 1.0)
        - total_source_topics: int
        - matched_topics: int
        - missing_topics: List[str]
    """
    source_topics = extract_source_topics(source_text)
    summary_topics = extract_summary_topics(summary_json)
    
    missing = find_missing_topics(source_topics, summary_topics)
    coverage = calculate_coverage_score(source_topics, summary_topics)
    matched = len(source_topics) - len(missing)
    
    result = {
        "passed": coverage >= min_coverage,
        "coverage_score": coverage,
        "total_source_topics": len(source_topics),
        "matched_topics": matched,
        "missing_topics": missing,
        "source_topics_sample": source_topics[:10],  # First 10 for debugging
        "summary_topics_count": len(summary_topics)
    }
    
    return result


def generate_coverage_report(validation_result: Dict) -> str:
    """
    Generate human-readable coverage report
    """
    result = validation_result
    
    report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 COVERAGE VALIDATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: {"✅ PASSED" if result['passed'] else "❌ FAILED"}
Coverage Score: {result['coverage_score']:.1%}

Topics Found in Source: {result['total_source_topics']}
Topics Matched in Summary: {result['matched_topics']}
Topics in Summary: {result['summary_topics_count']}

"""
    
    if result['missing_topics']:
        report += f"\n⚠️  MISSING TOPICS ({len(result['missing_topics'])}):\n"
        for i, topic in enumerate(result['missing_topics'][:15], 1):  # Show first 15
            report += f"  {i}. {topic}\n"
        if len(result['missing_topics']) > 15:
            report += f"  ... and {len(result['missing_topics']) - 15} more\n"
    else:
        report += "\n✅ All major topics covered!\n"
    
    report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return report
