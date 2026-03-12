"""Parse different file formats (PDF, DOCX, TXT)."""
import io
from typing import List, Tuple
from pypdf import PdfReader
from docx import Document


def parse_pdf(file_bytes: bytes, filename: str) -> Tuple[str, List[str]]:
    """Parse PDF and return (full_text, list_of_pages)."""
    try:
        pdf = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        full_text = "\n\n".join(pages)
        return full_text, pages
    except Exception as e:
        raise ValueError(f"Failed to parse PDF {filename}: {e}")


def parse_docx(file_bytes: bytes, filename: str) -> Tuple[str, List[str]]:
    """Parse DOCX and return (full_text, list_of_paragraphs)."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        return full_text, paragraphs
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX {filename}: {e}")


def parse_txt(file_bytes: bytes, filename: str) -> Tuple[str, List[str]]:
    """Parse TXT and return (full_text, list_of_lines)."""
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        lines = [line for line in text.split("\n") if line.strip()]
        return text, lines
    except Exception as e:
        raise ValueError(f"Failed to parse TXT {filename}: {e}")


def parse_file(file_bytes: bytes, filename: str) -> Tuple[str, List[str]]:
    """Detect file type and parse accordingly."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith(".pdf"):
        return parse_pdf(file_bytes, filename)
    elif filename_lower.endswith(".docx"):
        return parse_docx(file_bytes, filename)
    elif filename_lower.endswith(".txt"):
        return parse_txt(file_bytes, filename)
    elif filename_lower.endswith(".md"):
        return parse_txt(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file type: {filename}")
