"""
Coverage validation to ensure no topics are skipped
Extracts all headings/topics from source and verifies they appear in summary
"""
import re
from typing import List, Dict
from difflib import SequenceMatcher


# ===========================================================
# RELIABLE HEADING EXTRACTION (more aligned with parser)
# ===========================================================
HEADING_RE = re.compile(
    r'^(?:'
    r'(\d+(?:\.\d+)+\s+.+)'                           # 1.2.3 Heading
    r'|([A-Z][A-Za-z0-9\s]{5,120})'                    # Capitalized lines
    r'|(Example|Problem|Definition|Theorem)\b.+)'      # Keyword start
    r'$',
    re.MULTILINE
)


def extract_source_topics(text: str) -> List[str]:
    topics = []

    for match in HEADING_RE.finditer(text):
        line = match.group(0).strip()
        # exclude too long garbage
        if 5 <= len(line) <= 140:
            topics.append(line)

    return list(dict.fromkeys(topics))


# ===========================================================
# SUMMARY TOPIC EXTRACTION
# ===========================================================
def extract_summary_topics(summary_json: dict) -> List[str]:
    topics = []
    data = summary_json.get("summary", {})

    for section in data.get("sections", []):
        if section.get("heading"):
            topics.append(section["heading"])
        for c in section.get("concepts", []):
            if c.get("term"):
                topics.append(c["term"])

    for f in data.get("formula_sheet", []):
        if f.get("name"):
            topics.append(f["name"])

    for g in data.get("glossary", []):
        if g.get("term"):
            topics.append(g["term"])

    return topics


# ===========================================================
# FUZZY MATCHING + COVERAGE SCORING
# ===========================================================
def similarity_score(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_missing_topics(source_topics, summary_topics, threshold=0.55):
    missing = []
    for st in source_topics:
        if max(similarity_score(st, s) for s in summary_topics) < threshold:
            missing.append(st)
    return missing


def calculate_coverage_score(source_topics, summary_topics, threshold=0.55):
    matched = sum(
        1 for st in source_topics
        if any(similarity_score(st, s) >= threshold for s in summary_topics)
    )
    return matched / len(source_topics) if source_topics else 1.0


# ===========================================================
# VALIDATE + REPORTING
# ===========================================================
def validate_coverage(source_text: str, summary_json: dict, min_coverage=0.80):
    source_topics = extract_source_topics(source_text)
    summary_topics = extract_summary_topics(summary_json)

    coverage = calculate_coverage_score(source_topics, summary_topics)
    missing = find_missing_topics(source_topics, summary_topics)

    return {
        "passed": coverage >= min_coverage,
        "coverage_score": coverage,
        "total_source_topics": len(source_topics),
        "matched_topics": len(source_topics) - len(missing),
        "missing_topics": missing,
        "summary_topics_count": len(summary_topics)
    }


def generate_coverage_report(result: Dict) -> str:
    rep = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 COVERAGE VALIDATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: {"✅ PASSED" if result['passed'] else "❌ FAILED"}
Coverage Score: {result['coverage_score']*100:.1f}%

Topics Found in Source: {result['total_source_topics']}
Topics Matched in Summary: {result['matched_topics']}
Topics in Summary: {result['summary_topics_count']}
"""

    if result["missing_topics"]:
        rep += "\n⚠️ Missing Topics:\n"
        for i, t in enumerate(result["missing_topics"][:20], 1):
            rep += f"  {i}. {t}\n"

    rep += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    return rep
