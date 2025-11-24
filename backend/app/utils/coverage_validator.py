"""
Coverage validation to ensure no topics are skipped
Extracts all headings/topics from source and verifies they appear in summary
"""

import re
from typing import List, Dict
from difflib import SequenceMatcher

# NEW: use the same heading engine as summarizer
from app.utils.structure_parser import extract_heading_hierarchy


def extract_source_topics(text: str) -> List[str]:
    """
    Extract source topics using the SAME heading engine as the summarizer.
    This guarantees consistent topic detection.
    """

    blocks = extract_heading_hierarchy(text)
    topics = []

    for block in blocks:
        if block.block_type == "heading":

            # include the heading itself
            topics.append(block.content.strip())

            # also include full heading path for stronger coverage matching
            if block.heading_path:
                full_path = " > ".join(block.heading_path)
                topics.append(full_path)

    # remove duplicates while preserving order
    cleaned = []
    seen = set()
    for t in topics:
        if t not in seen and len(t.strip()) > 2:
            cleaned.append(t)
            seen.add(t)

    return cleaned



def extract_summary_topics(summary_json: dict) -> List[str]:
    """
    Extract all topics/concepts from generated summary
    Returns list of topic strings found in the summary
    """
    topics = []
    
    summary_data = summary_json.get("summary", {})

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
    """Fuzzy string similarity"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()



def find_missing_topics(source_topics: List[str], summary_topics: List[str], threshold: float = 0.70) -> List[str]:
    """
    Find source topics not represented in summary topics.
    """
    missing = []

    for source_topic in source_topics:
        best_score = 0.0
        for summary_topic in summary_topics:
            score = similarity_score(source_topic, summary_topic)
            if score > best_score:
                best_score = score

        if best_score < threshold:
            missing.append(source_topic)

    return missing



def calculate_coverage_score(source_topics: List[str], summary_topics: List[str], threshold: float = 0.70) -> float:
    """
    Calculate percentage of source headings that appear in summary.
    """
    if not source_topics:
        return 1.0

    matched = 0
    for source_topic in source_topics:
        for summary_topic in summary_topics:
            if similarity_score(source_topic, summary_topic) >= threshold:
                matched += 1
                break

    return matched / len(source_topics)



def validate_coverage(source_text: str, summary_json: dict, min_coverage: float = 0.85) -> Dict:
    """
    Main coverage validation logic.
    """

    source_topics = extract_source_topics(source_text)
    summary_topics = extract_summary_topics(summary_json)

    missing = find_missing_topics(source_topics, summary_topics)
    coverage = calculate_coverage_score(source_topics, summary_topics)
    matched = len(source_topics) - len(missing)

    return {
        "passed": coverage >= min_coverage,
        "coverage_score": coverage,
        "total_source_topics": len(source_topics),
        "matched_topics": matched,
        "missing_topics": missing,
        "source_topics_sample": source_topics[:10],
        "summary_topics_count": len(summary_topics),
    }



def generate_coverage_report(result: Dict) -> str:
    """
    Human-readable coverage report
    """
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
        for i, topic in enumerate(result['missing_topics'][:15], 1):
            report += f"  {i}. {topic}\n"
        if len(result['missing_topics']) > 15:
            report += f"  ...and {len(result['missing_topics']) - 15} more\n"
    else:
        report += "\n✅ All major topics covered!\n"

    report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    return report
