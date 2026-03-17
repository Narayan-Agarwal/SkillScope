"""
Resume parser: extracts text from PDF bytes.
Tries PyMuPDF (fitz) first, falls back to pdfplumber.
"""
import io


def extract_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes.

    Tries PyMuPDF first; falls back to pdfplumber if fitz fails or returns
    empty/whitespace-only text. Raises ValueError if both fail or return empty.
    """
    text = _try_fitz(file_bytes)
    if text is None:
        text = _try_pdfplumber(file_bytes)

    if text is None:
        raise ValueError("Could not extract text from PDF")

    return text


def _try_fitz(file_bytes: bytes) -> str | None:
    """Attempt extraction with PyMuPDF. Returns cleaned text or None on failure."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        doc.close()

        text = "\n".join(pages_text).strip()
        return text if text else None
    except Exception:
        return None


def _try_pdfplumber(file_bytes: bytes) -> str | None:
    """Attempt extraction with pdfplumber. Returns cleaned text or None on failure."""
    try:
        import pdfplumber

        pages_text = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                pages_text.append(page_text)

        text = "\n".join(pages_text).strip()
        return text if text else None
    except Exception:
        return None
