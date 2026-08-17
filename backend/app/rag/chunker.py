"""
ADAPT — Semantic Syllabus Chunker

Segments syllabus/academic text into chunks aligned with Units, Topics, and Sections,
preserving context boundaries with overlap.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TextChunk(BaseModel):
    content: str
    unit_number: Optional[int] = None
    topic: Optional[str] = None
    chunk_index: int
    char_count: int
    metadata: Dict[str, Any] = {}


class SyllabusChunker:
    """
    Intelligent chunker for academic syllabi and documents.
    1. Detects Unit / Module / Chapter headers.
    2. Groups text by unit.
    3. Splits long units into 500-800 token chunks with 100 token overlap.
    """

    def __init__(self, target_chunk_size: int = 1500, overlap: int = 200):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_document(self, text: str, default_metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        if not text or not text.strip():
            return []

        meta = default_metadata or {}
        
        # Step 1: Detect Unit sections using Regex
        # Matches e.g. "Unit 1", "UNIT - I", "Module 2:", "CHAPTER 3"
        unit_pattern = re.compile(
            r"(?i)(?:^|\n)(?:unit|module|chapter)\s*([0-9IVXLCDM]+)[\s:\-\.]*(.*?)(?=\n(?:unit|module|chapter)\s*[0-9IVXLCDM]+|\Z)",
            re.DOTALL
        )

        matches = list(unit_pattern.finditer(text))
        chunks: List[TextChunk] = []
        chunk_idx = 0

        if matches:
            # We found structured units
            # Also capture any preamble before Unit 1 (Course Objectives, Prerequisites)
            first_match_start = matches[0].start()
            if first_match_start > 50:
                preamble = text[:first_match_start].strip()
                if preamble:
                    sub_chunks = self._split_text_with_overlap(preamble)
                    for sc in sub_chunks:
                        chunks.append(TextChunk(
                            content=sc,
                            unit_number=0,  # 0 indicates preamble / course-wide
                            topic="Course Objectives & Overview",
                            chunk_index=chunk_idx,
                            char_count=len(sc),
                            metadata={**meta, "section": "overview"},
                        ))
                        chunk_idx += 1

            for match in matches:
                raw_num = match.group(1).strip()
                unit_num = self._roman_or_int(raw_num)
                unit_title = match.group(2).strip().split("\n")[0][:150]
                unit_full_content = match.group(0).strip()

                sub_chunks = self._split_text_with_overlap(unit_full_content)
                for sc in sub_chunks:
                    chunks.append(TextChunk(
                        content=sc,
                        unit_number=unit_num,
                        topic=unit_title,
                        chunk_index=chunk_idx,
                        char_count=len(sc),
                        metadata={**meta, "unit_raw": raw_num, "unit_title": unit_title},
                    ))
                    chunk_idx += 1
        else:
            # Fallback to paragraph/sliding window chunking if no explicit unit headers found
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            current_buffer = []
            current_len = 0

            for p in paragraphs:
                if current_len + len(p) > self.target_chunk_size and current_buffer:
                    chunk_content = "\n\n".join(current_buffer)
                    chunks.append(TextChunk(
                        content=chunk_content,
                        unit_number=None,
                        topic=None,
                        chunk_index=chunk_idx,
                        char_count=len(chunk_content),
                        metadata=meta,
                    ))
                    chunk_idx += 1
                    # Keep last paragraph for overlap
                    current_buffer = [current_buffer[-1]] if len(current_buffer) > 1 else []
                    current_len = sum(len(x) for x in current_buffer)

                current_buffer.append(p)
                current_len += len(p)

            if current_buffer:
                chunk_content = "\n\n".join(current_buffer)
                chunks.append(TextChunk(
                    content=chunk_content,
                    unit_number=None,
                    topic=None,
                    chunk_index=chunk_idx,
                    char_count=len(chunk_content),
                    metadata=meta,
                ))

        return chunks

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """Splits long text into windowed pieces."""
        if len(text) <= self.target_chunk_size:
            return [text]

        pieces: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.target_chunk_size, len(text))
            
            # Try to break at a newline or period if possible
            if end < len(text):
                newline_pos = text.rfind("\n", start + self.overlap, end)
                if newline_pos != -1 and newline_pos > start:
                    end = newline_pos + 1
                else:
                    period_pos = text.rfind(". ", start + self.overlap, end)
                    if period_pos != -1 and period_pos > start:
                        end = period_pos + 1

            chunk_str = text[start:end].strip()
            if chunk_str:
                pieces.append(chunk_str)

            if end >= len(text):
                break
            start = end - self.overlap

        return pieces

    @staticmethod
    def _roman_or_int(val: str) -> int:
        val = val.upper().strip()
        roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
        if val in roman_map:
            return roman_map[val]
        try:
            return int(val)
        except ValueError:
            return 1
