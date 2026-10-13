"""
ADAPT — Unified Examination Paper Generation Prompts

Single set of prompts for both MSE and ESE, with configurable parameters.
System sample papers are included as style/format reference only —
the model must NOT copy or paraphrase questions from them.
"""

UNIFIED_EXAM_SYSTEM_PROMPT = """You are a senior university examination controller setting an official {exam_type_full} paper.

STRICT RULES:
1. Generate questions that EXACTLY match the total marks target. The sum of all question marks must equal {total_marks}.
2. Generate exactly the specified number of questions at each mark level:
{mark_config_summary}
3. Questions MUST be grounded in the provided syllabus context for the selected units.
4. Each question must specify: question_text, marks, bloom_level, difficulty, co_code, unit_number, topic, reference_answer, and marking_scheme.
5. Distribute questions across the selected units: {units_covered}.
6. DO NOT copy or closely paraphrase any questions from the sample papers provided. Sample papers are reference for FORMAT and STYLE only.
7. Questions must be original, syllabus-grounded, and appropriately challenging.
8. For questions with sub-parts, the total marks of sub-parts must add up correctly.
"""

UNIFIED_EXAM_USER_PROMPT = """Generate a {exam_type_full} paper for: {subject_name} ({course_code})

=== BLUEPRINT ===
- Paper Type: {exam_type}
- Total Marks: {total_marks}
- Units Covered: {units_covered}
- Question Configuration:
{mark_config_detail}

=== SECTION STRUCTURE ===
{section_structure}

=== SYLLABUS CONTEXT (Selected Units) ===
{syllabus_context}

=== INSTITUTIONAL SAMPLE PAPER REFERENCE (Format/Style Only — DO NOT COPY QUESTIONS) ===
{sample_context}

=== COURSE OUTCOMES ===
{co_context}

=== ADDITIONAL REFERENCE MATERIAL ===
{additional_context}

Generate the examination paper now. Ensure total marks sum to exactly {total_marks}.
"""

# Default section structures per exam type
MSE_DEFAULT_SECTIONS = """Section A: Short Answer / Conceptual Questions (compulsory)
Section B: Long Answer / Problem Solving Questions (compulsory)"""

ESE_DEFAULT_SECTIONS = """Section A: Short Answer Questions (compulsory, 2-mark each)
Section B: Medium Answer Questions (5-mark each, with internal choices where applicable)
Section C: Long Answer / Design Questions (10-mark each, with internal choices where applicable)"""
