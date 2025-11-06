"""
File validation and processing utilities
"""
import os
import hashlib
from typing import Set
from io import BytesIO
from PyPDF2 import PdfReader


def sha256_bytes(data: bytes) -> str:
    """Calculate SHA256 hash of bytes"""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Calculate SHA256 hash of text"""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def ext_ok(filename: str, allowed: Set[str]) -> bool:
    """Check if file extension is allowed"""
    _, ext = os.path.splitext(filename.lower())
    return ext in allowed


def pdf_page_count(pdf_bytes: bytes) -> int:
    """Count pages in a PDF file"""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        return len(reader.pages)
    except Exception:
        return 0


def approx_tokens_from_text_len(n_chars: int, token_per_char: float = 0.25) -> int:
    """Estimate token count from character count (4 chars ≈ 1 token)"""
    return max(1, int(n_chars * token_per_char))


def clamp(v: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi"""
    return max(lo, min(v, hi))


def choose_max_output_tokens(t_in: int, cap: int) -> int:
    """
    Choose adaptive max_output_tokens based on input size
    Target: ~25% of input, but at least 1200, capped at plan limit
    """
    raw = int(t_in * 0.25)  # 25% output target
    return int(clamp(max(1200, raw), 600, cap))


def estimate_file_tokens(content: bytes, token_per_char: float = 0.25) -> int:
    """
    Estimate token count from file content
    Assumes content can be decoded as UTF-8 text
    """
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    return approx_tokens_from_text_len(len(text), token_per_char)


def validate_mime_type(filename: str, content: bytes) -> bool:
    """
    Basic MIME type validation (stub for future enhancement)
    Could integrate python-magic or similar for real MIME detection
    """
    # For now, just check extension
    ext = os.path.splitext(filename.lower())[1]
    
    # Basic magic number checks
    if ext == ".pdf" and not content.startswith(b"%PDF"):
        return False
    
    if ext == ".docx" and not content.startswith(b"PK"):  # ZIP signature
        return False
    
    if ext == ".pptx" and not content.startswith(b"PK"):
        return False
    
    return True


def basic_antivirus_check(content: bytes) -> bool:
    """
    Basic antivirus stub - placeholder for real AV integration
    In production, integrate with ClamAV or cloud AV service
    """
    # Check for suspiciously large files that might be bombs
    if len(content) > 200 * 1024 * 1024:  # 200 MB
        return False
    
    # Check for suspicious patterns (very basic)
    suspicious_patterns = [
        b"<script",  # JavaScript in documents
        b"<?php",    # PHP code
        b"<%",       # ASP code
    ]
    
    content_lower = content.lower()
    for pattern in suspicious_patterns:
        if pattern in content_lower:
            return False
    
    return True
