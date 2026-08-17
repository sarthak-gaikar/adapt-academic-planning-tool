"""
ADAPT — Unit Tests for Semantic Syllabus Chunker
"""

import pytest
from app.rag.chunker import SyllabusChunker


def test_chunker_detects_units():
    sample_syllabus_text = """
    Course: Data Structures (CS201)
    
    UNIT 1: Linear Data Structures
    Arrays, Stacks, Queues, Linked Lists.
    Applications of stacks in recursion.
    
    UNIT 2: Trees and Hierarchical Data
    Binary Search Trees, AVL Trees, B-Trees.
    Tree traversal algorithms.
    
    UNIT 3: Graphs and Algorithms
    Graph representations, BFS, DFS, Dijkstra shortest path algorithm.
    """

    chunker = SyllabusChunker(target_chunk_size=500, overlap=50)
    chunks = chunker.chunk_document(sample_syllabus_text)

    assert len(chunks) >= 3
    unit_nums = [c.unit_number for c in chunks if c.unit_number is not None]
    assert 1 in unit_nums
    assert 2 in unit_nums
    assert 3 in unit_nums


def test_chunker_empty_input():
    chunker = SyllabusChunker()
    assert chunker.chunk_document("") == []
    assert chunker.chunk_document("   ") == []
