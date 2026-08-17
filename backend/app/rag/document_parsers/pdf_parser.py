"""
ADAPT — PDF Document Parser

Extracts text, pages, metadata, and structural headers from PDF files using PyMuPDF (fitz).
"""

import fitz  # PyMuPDF
from typing import Dict, List, Any
from pathlib import Path
from app.core.exceptions import FileParsingError
from app.core.logging import get_logger

logger = get_logger("rag.pdf_parser")


class PDFParser:
    """Extracts raw text, page-by-page text, and basic outline from PDF."""

    @staticmethod
    def parse(file_path: str) -> Dict[str, Any]:
        """
        Parses a PDF file and returns extracted text and metadata.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileParsingError(f"PDF file not found at {file_path}")

        try:
            doc = fitz.open(file_path)
            full_text_parts: List[str] = []
            pages_data: List[Dict[str, Any]] = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                cleaned = text.strip()
                if cleaned:
                    full_text_parts.append(cleaned)
                pages_data.append({
                    "page_number": page_num + 1,
                    "text": cleaned,
                    "char_count": len(cleaned),
                })

            total_text = "\n\n".join(full_text_parts)

            # Metadata
            meta = doc.metadata or {}
            toc = doc.get_toc()  # Table of contents if present

            doc.close()

            if not total_text.strip():
                logger.warning(f"Extracted 0 characters from PDF: {file_path}. Might be scanned.")

            return {
                "full_text": total_text,
                "pages": pages_data,
                "page_count": len(pages_data),
                "title": meta.get("title") or path.stem,
                "author": meta.get("author", ""),
                "toc": toc,
            }

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise FileParsingError(f"Could not parse PDF: {str(e)}")
