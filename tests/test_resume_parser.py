"""Unit tests for src/resume_parser.py"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from resume_parser import extract_text

# Minimal valid PDF with "Hello World" text content
MINIMAL_PDF_WITH_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
    b" /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font"
    b" /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\n"
    b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 5\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000266 00000 n \n"
    b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
    b"startxref\n360\n%%EOF"
)

# Minimal valid PDF with no text content (empty page)
MINIMAL_PDF_NO_TEXT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n190\n%%EOF"
)


def test_valid_pdf_returns_text():
    """A valid PDF with text content should return a non-empty string."""
    result = extract_text(MINIMAL_PDF_WITH_TEXT)
    assert isinstance(result, str)
    assert len(result) > 0


def test_invalid_bytes_raises_value_error():
    """Non-PDF bytes should raise ValueError."""
    with pytest.raises(ValueError, match="Could not extract text from PDF"):
        extract_text(b"not a pdf")


def test_empty_pdf_raises_value_error():
    """A valid PDF with no text content should raise ValueError."""
    with pytest.raises(ValueError, match="Could not extract text from PDF"):
        extract_text(MINIMAL_PDF_NO_TEXT)
