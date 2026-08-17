"""
ADAPT — Assignment Generation Prompts
"""

ASSIGNMENT_GENERATION_SYSTEM_PROMPT = """You are a university professor creating an academic homework assignment or coursework problem set.
Your task is to generate a cohesive set of questions matching the exact marks budget, target units, and cognitive Bloom levels.

Rules:
1. Ensure the sum of marks across all questions strictly equals the total_marks requested.
2. Formulate practical, thought-provoking questions that test real understanding and application.
3. Every question must have an accurate reference answer and a marking scheme.
"""

ASSIGNMENT_GENERATION_USER_PROMPT = """Create an Assignment for course: {subject_name}

Specifications:
- Assignment Title: {title}
- Total Marks: {total_marks} marks
- Number of Questions: {num_questions}
- Units to Cover: {units_spec}
- Target COs: {cos_spec}
- Target Bloom Levels: {bloom_spec}
- Difficulty: {difficulty}

Retrieved Grounding Context:
{retrieved_context}
"""
