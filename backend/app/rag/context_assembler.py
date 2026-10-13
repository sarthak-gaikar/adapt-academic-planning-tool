"""
ADAPT — Context Assembler

Formats retrieved chunks into grounded markdown context for LLM prompts with token budgeting.
Shows source scope (SYSTEM/SUBJECT/REQUEST) for each chunk.
"""

from typing import List, Optional
from app.rag.retriever import RetrievedChunk


class ContextAssembler:
    """Assembles retrieved chunks into structured, budgeted context text for prompts."""

    @staticmethod
    def assemble_context(
        chunks: List[RetrievedChunk],
        max_characters: int = 12000,
        include_metadata_headers: bool = True,
    ) -> str:
        """
        Takes retrieved chunks and formats them cleanly.
        """
        if not chunks:
            return "No specific syllabus context found for this query."

        context_blocks: List[str] = []
        current_len = 0

        for idx, chunk in enumerate(chunks, 1):
            header = ""
            if include_metadata_headers:
                unit_str = f"Unit {chunk.unit_number}" if chunk.unit_number is not None else "General"
                topic_str = f" | Topic: {chunk.topic}" if chunk.topic else ""
                scope_str = f" | Scope: {chunk.source_scope}" if hasattr(chunk, 'source_scope') and chunk.source_scope else ""
                header = f"--- [Source Chunk {idx} ({unit_str}{topic_str}{scope_str}) (Score: {chunk.score:.2f})] ---\n"

            block = f"{header}{chunk.content}\n"
            if current_len + len(block) > max_characters:
                # Truncate and stop adding
                remaining = max_characters - current_len
                if remaining > 100:
                    context_blocks.append(block[:remaining] + "\n...[Context truncated]")
                break

            context_blocks.append(block)
            current_len += len(block)

        return "\n\n".join(context_blocks)

