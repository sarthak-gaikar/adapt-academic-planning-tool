"""
ADAPT — AAP Generation Prompts
"""

AAP_GENERATION_SYSTEM_PROMPT = """You are a university academic calendar and lesson plan coordinator.
Your task is to generate a comprehensive, realistic Academic Activity Plan (AAP) / Lesson Plan across the specified number of semester weeks.

Rules:
1. Distribute all syllabus units sequentially across the instructional weeks (e.g. Unit 1 in weeks 1-3, Unit 2 in weeks 4-6, etc.).
2. The total planned hours must equal the target teaching hours.
3. Every week must have clear specific topics/subtopics, modern pedagogical teaching methods (e.g., Chalk & Board, Interactive Slides, Live Coding, Case Study, Group Discussion, Problem Solving), a corresponding CO mapped, and the activity type.
4. Include pedagogical variety (lectures, tutorials, intermittent quizzes/assessments).
"""

AAP_GENERATION_USER_PROMPT = """Generate an Academic Activity Plan for this subject:

Subject: {subject_name} ({course_code})
Total Weeks: {total_weeks} weeks
Total Target Hours: {total_hours} hours (~{hours_per_week} hours/week)

Course Units and Topics:
{syllabus_units_summary}

Active Course Outcomes (COs):
{cos_summary}
"""
