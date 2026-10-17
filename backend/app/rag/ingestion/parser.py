"""Page-aware PDF text extraction."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf


class PdfParsingError(ValueError):
    """Raised when a PDF cannot safely provide usable text."""


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Normalized native text associated with its one-based PDF page number."""

    page_number: int
    text: str


def normalize_text(text: str) -> str:
    """Normalize extraction noise while preserving paragraph boundaries."""

    lines = [" ".join(line.split()) for line in text.replace("\x00", "").splitlines()]
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs).strip()


def validate_pdf_structure(path: Path, max_pages: int) -> int:
    """Open the real PDF bytes and validate encryption and page-count limits."""

    try:
        with pymupdf.open(path) as pdf:
            if not pdf.is_pdf:
                raise PdfParsingError("File content is not a valid PDF")
            if pdf.needs_pass:
                raise PdfParsingError("Password-protected PDFs are not supported")
            if pdf.page_count == 0:
                raise PdfParsingError("PDF contains no pages")
            if pdf.page_count > max_pages:
                raise PdfParsingError(f"PDF exceeds the {max_pages}-page limit")
            return pdf.page_count
    except PdfParsingError:
        raise
    except Exception as exc:
        raise PdfParsingError("PDF could not be parsed") from exc


def extract_pdf_pages(path: Path, max_pages: int) -> list[ExtractedPage]:
    """Extract non-empty text with one-based source page numbers."""

    try:
        validate_pdf_structure(path, max_pages)
        with pymupdf.open(path) as pdf:

            pages = [
                ExtractedPage(page_number=index + 1, text=normalize_text(page.get_text("text")))
                for index, page in enumerate(pdf)
            ]
    except PdfParsingError:
        raise
    except Exception as exc:
        raise PdfParsingError("PDF could not be parsed") from exc

    usable_pages = [page for page in pages if page.text]
    if not usable_pages:
        raise PdfParsingError(
            "PDF contains no extractable text; only text-based PDFs are supported"
        )
    return usable_pages
