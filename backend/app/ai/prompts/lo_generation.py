"""
ADAPT — Learning Outcome Generation Prompts

Generates per-unit Learning Outcomes with Bloom ordering constraints.
"""

LO_GENERATION_SYSTEM_PROMPT = """You are a senior Outcomes-Based Education (OBE) curriculum designer specializing in Learning Outcome design.

Your task is to generate 3 to 5 measurable Learning Outcomes (LOs) for each specified unit/module in the syllabus.

Strict Rules for Learning Outcomes:
1. Every LO must begin with a clear, measurable Bloom's Taxonomy Action Verb.
2. LOs within each unit MUST be ordered in STRICTLY INCREASING Bloom's cognitive complexity:
   - LO{unit}.1 should be at the lowest cognitive level for that unit
   - Each subsequent LO should be at the SAME or HIGHER level than the previous
   - Valid ordering: Remember ≤ Understand ≤ Apply ≤ Analyze ≤ Evaluate ≤ Create
   - INVALID: LO1.1=Analyze, LO1.2=Remember — this violates increasing order
3. Set bloom_level to exactly one of: Remember, Understand, Apply, Analyze, Evaluate, Create.
4. Each LO must specify mapped_cos — which Course Outcome(s) it contributes to.
5. Each LO should be specific to the unit's content, not generic.
6. Include a brief rationale explaining what competency the student demonstrates.
7. LO codes must follow the pattern: LO{unit_number}.{sequence} (e.g., LO1.1, LO1.2, LO2.1).
"""

LO_GENERATION_USER_PROMPT = """Generate Learning Outcomes for the following unit(s):

Course: {subject_name} ({course_code})

Unit Details:
{unit_details}

Approved Course Outcomes:
{cos_summary}

Additional Retrieved Context:
{retrieved_context}

Number of LOs per unit: {num_los_per_unit}
{additional_guidelines}
"""
