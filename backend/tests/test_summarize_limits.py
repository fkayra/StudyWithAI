"""
Tests for summary system limits and functionality
"""
import pytest
from app.config import PLAN_LIMITS
from app.utils.files import (
    ext_ok, approx_tokens_from_text_len, choose_max_output_tokens,
    clamp, sha256_text, validate_mime_type
)
from app.utils.chunking import (
    split_text_approx_tokens, merge_texts, estimate_chunks_needed
)


def test_plan_limits_loaded():
    """Verify all plans are configured"""
    assert "free" in PLAN_LIMITS
    assert "standard" in PLAN_LIMITS
    assert "premium" in PLAN_LIMITS
    assert "pro" in PLAN_LIMITS  # alias
    
    # Check free plan limits
    free = PLAN_LIMITS["free"]
    assert free.max_files_total == 3
    assert free.max_pdfs == 2
    assert free.max_total_mb == 20
    assert free.max_input_tokens == 12000
    assert free.max_output_cap == 1200


def test_plan_limits_progression():
    """Verify limits increase with plan tier"""
    free = PLAN_LIMITS["free"]
    standard = PLAN_LIMITS["standard"]
    premium = PLAN_LIMITS["premium"]
    
    assert standard.max_files_total > free.max_files_total
    assert premium.max_files_total > standard.max_files_total
    
    assert standard.max_input_tokens > free.max_input_tokens
    assert premium.max_input_tokens > standard.max_input_tokens


def test_file_extension_validation():
    """Test file type whitelist"""
    assert ext_ok("document.pdf", {".pdf", ".docx"})
    assert ext_ok("presentation.PPTX", {".pdf", ".docx", ".pptx"})  # case insensitive
    assert not ext_ok("script.exe", {".pdf", ".docx"})
    assert not ext_ok("malware.js", {".pdf", ".docx"})


def test_token_estimation():
    """Test character-to-token estimation"""
    # Roughly 4 characters = 1 token
    text = "a" * 1000  # 1000 chars
    tokens = approx_tokens_from_text_len(len(text), token_per_char=0.25)
    assert 200 <= tokens <= 300  # Should be ~250
    
    # Empty text
    assert approx_tokens_from_text_len(0) == 1  # min 1


def test_adaptive_output_tokens():
    """Test adaptive max_output_tokens calculation"""
    # Small input: should use min (1200)
    result = choose_max_output_tokens(2000, cap=8000)
    assert result == 1200
    
    # Medium input: should scale
    result = choose_max_output_tokens(10000, cap=8000)
    assert 1200 < result <= 8000
    
    # Large input: should hit cap
    result = choose_max_output_tokens(50000, cap=8000)
    assert result == 8000
    
    # Respects plan cap
    result = choose_max_output_tokens(10000, cap=1500)
    assert result <= 1500


def test_clamp_function():
    """Test value clamping utility"""
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
    assert clamp(7.5, 5.0, 10.0) == 7.5


def test_text_chunking_basic():
    """Test basic text chunking"""
    # Small text: shouldn't chunk
    text = "Short text" * 10
    chunks = split_text_approx_tokens(text, chunk_tokens=5000)
    assert len(chunks) == 1
    
    # Large text: should chunk
    text = "A" * 50000  # ~12500 tokens
    chunks = split_text_approx_tokens(text, chunk_tokens=2400)
    assert len(chunks) >= 5


def test_text_chunking_paragraph_breaks():
    """Test chunking respects paragraph boundaries"""
    # Create text with clear paragraph breaks
    paragraphs = ["Paragraph {}\n\n".format(i) for i in range(100)]
    text = "".join(paragraphs) * 10
    
    chunks = split_text_approx_tokens(text, chunk_tokens=2400)
    
    # Verify chunks are created
    assert len(chunks) > 1
    
    # Verify no chunk is empty
    for chunk in chunks:
        assert len(chunk.strip()) > 0


def test_merge_texts():
    """Test text merging utility"""
    texts = ["Part 1", "Part 2", "Part 3"]
    merged = merge_texts(texts, separator=" | ")
    assert merged == "Part 1 | Part 2 | Part 3"
    
    # Handle empty texts
    texts_with_empty = ["Part 1", "", "Part 2", "   ", "Part 3"]
    merged = merge_texts(texts_with_empty)
    assert "Part 1" in merged
    assert "Part 2" in merged
    assert "Part 3" in merged


def test_estimate_chunks_needed():
    """Test chunk count estimation"""
    # 10k chars = ~2500 tokens, should need ~2 chunks of 2400 tokens
    estimate = estimate_chunks_needed(10000, chunk_tokens=2400)
    assert estimate >= 1
    
    # Very large text
    estimate = estimate_chunks_needed(100000, chunk_tokens=2400)
    assert estimate >= 10


def test_sha256_hashing():
    """Test content hashing for cache keys"""
    text1 = "Hello, World!"
    text2 = "Hello, World!"
    text3 = "Different text"
    
    hash1 = sha256_text(text1)
    hash2 = sha256_text(text2)
    hash3 = sha256_text(text3)
    
    # Same content = same hash
    assert hash1 == hash2
    
    # Different content = different hash
    assert hash1 != hash3
    
    # Hash length (SHA256 = 64 hex chars)
    assert len(hash1) == 64


def test_mime_validation_basic():
    """Test basic MIME type validation"""
    # PDF with correct magic number
    pdf_content = b"%PDF-1.4\nsome content"
    assert validate_mime_type("document.pdf", pdf_content)
    
    # PDF with wrong magic number
    fake_pdf = b"not a pdf"
    assert not validate_mime_type("fake.pdf", fake_pdf)
    
    # DOCX/PPTX (ZIP signature)
    zip_content = b"PK\x03\x04some content"
    assert validate_mime_type("document.docx", zip_content)
    assert validate_mime_type("presentation.pptx", zip_content)


# Integration-style tests (require OpenAI key)

@pytest.mark.skipif(
    not pytest.config.getoption("--integration"),
    reason="Integration tests require --integration flag and OpenAI API key"
)
def test_map_reduce_pipeline():
    """Test full map-reduce summarization (integration test)"""
    from app.services.summary import map_reduce_summary
    
    # Create moderately large text
    sample_text = """
    Machine Learning Introduction:
    Machine learning is a subset of artificial intelligence that focuses on training algorithms
    to learn patterns from data and make predictions without explicit programming.
    
    Supervised Learning:
    In supervised learning, the algorithm learns from labeled data...
    """ * 50  # Repeat to make it larger
    
    result = map_reduce_summary(
        full_text=sample_text,
        language="en",
        additional_instructions="Focus on key concepts",
        out_cap=1200,
        force_chunking=True  # Force map-reduce for testing
    )
    
    # Should return valid JSON
    import json
    parsed = json.loads(result)
    assert "summary" in parsed


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires API keys)"
    )


if __name__ == "__main__":
    # Run basic tests
    test_plan_limits_loaded()
    test_file_extension_validation()
    test_token_estimation()
    test_text_chunking_basic()
    print("✅ All basic tests passed!")
