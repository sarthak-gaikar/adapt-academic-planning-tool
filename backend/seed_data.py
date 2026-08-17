"""
ADAPT — Database Seeding Script

Initializes the database with:
1. Default Faculty User (faculty@university.edu / Password123!)
2. NBA Program Outcomes (PO1-PO12 + PSO1-PSO2)
3. Default Natural Language Processing subject with structured syllabus units
"""

import asyncio
import json
from pathlib import Path
from sqlalchemy import select
from app.database import async_session_factory, init_db
from app.models.user import User
from app.models.subject import Subject
from app.models.program_outcome import ProgramOutcome
from app.models.syllabus import Syllabus, SyllabusUnit, Topic
from app.models.exam import ExamBlueprint
from app.core.security import hash_password


async def seed():
    print("Initializing database tables...")
    await init_db()

    async with async_session_factory() as session:
        # 1. Create Demo Faculty User
        res = await session.execute(select(User).where(User.email == "faculty@university.edu"))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email="faculty@university.edu",
                hashed_password=hash_password("Password123!"),
                full_name="Dr. Alan Turing",
                role="FACULTY",
                department="Department of Computer Science & Engineering",
            )
            session.add(user)
            await session.flush()
            print(f"Created default user: {user.email}")

        # 2. Seed Program Outcomes
        po_path = Path("data/knowledge_base/program_outcomes.json")
        if po_path.exists():
            with open(po_path, "r", encoding="utf-8") as f:
                pos_data = json.load(f)
                for item in pos_data:
                    p_res = await session.execute(
                        select(ProgramOutcome).where(ProgramOutcome.po_code == item["po_code"])
                    )
                    if not p_res.scalar_one_or_none():
                        po_obj = ProgramOutcome(
                            po_code=item["po_code"],
                            statement=item["statement"],
                            category=item.get("category", "PO"),
                            is_active=True,
                        )
                        session.add(po_obj)
            await session.flush()
            print("Seeded standard NBA Program Outcomes.")

        # 3. Seed Sample Subject: Natural Language Processing
        sub_res = await session.execute(select(Subject).where(Subject.course_code == "CS602"))
        subject = sub_res.scalar_one_or_none()
        if not subject:
            subject = Subject(
                created_by=user.id,
                name="Natural Language Processing",
                course_code="CS602",
                credits=4,
                teaching_hours=45,
                semester="VI",
                academic_year="2024-25",
                department="Department of Computer Science & Engineering",
                prerequisites=["Data Structures", "Theory of Computation", "Python Programming"],
                course_objectives=[
                    "Understand foundational computational linguistics and token processing",
                    "Apply statistical and neural models for language modeling and part-of-speech tagging",
                    "Analyze parsing algorithms and semantic representations",
                    "Design and evaluate transformer-based architectures for machine translation and QA",
                ],
                status="ACTIVE",
            )
            session.add(subject)
            await session.flush()
            print(f"Created course: {subject.name} ({subject.course_code})")

            # Add structured syllabus
            syllabus_data = {
                "subject_name": "Natural Language Processing",
                "course_code": "CS602",
                "credits": 4,
                "teaching_hours": 45,
                "units": [
                    {
                        "unit_number": 1,
                        "title": "Introduction to NLP & Text Preprocessing",
                        "hours": 8,
                        "topics": [
                            {"name": "Regular Expressions & Tokenization", "subtopics": ["Word tokenization", "Sentence boundary detection", "Byte-Pair Encoding (BPE)"]},
                            {"name": "Morphology & Stemming", "subtopics": ["Porter Stemmer", "Snowball Stemmer", "Lemmatization with WordNet"]},
                            {"name": "Text Normalization", "subtopics": ["Case folding", "Stopword removal", "Levenshtein Edit Distance"]},
                        ]
                    },
                    {
                        "unit_number": 2,
                        "title": "Language Modeling & Part-of-Speech Tagging",
                        "hours": 9,
                        "topics": [
                            {"name": "N-gram Language Models", "subtopics": ["Maximum Likelihood Estimation", "Laplace smoothing", "Good-Turing discounting", "Perplexity evaluation"]},
                            {"name": "POS Tagging Techniques", "subtopics": ["Penn Treebank tagset", "Hidden Markov Models (HMM)", "Viterbi decoding algorithm", "Maximum Entropy Markov Models (MEMM)"]},
                        ]
                    },
                    {
                        "unit_number": 3,
                        "title": "Syntactic Parsing & Grammar Formalisms",
                        "hours": 10,
                        "topics": [
                            {"name": "Context-Free Grammars", "subtopics": ["Chomsky Normal Form", "Structural ambiguity", "Treebanks"]},
                            {"name": "Parsing Algorithms", "subtopics": ["Cocke-Younger-Kasami (CYK) algorithm", "Earley parsing algorithm", "Probabilistic Context-Free Grammars (PCFG)"]},
                            {"name": "Dependency Parsing", "subtopics": ["Transition-based parsing", "Graph-based parsing", "Universal Dependencies"]},
                        ]
                    },
                    {
                        "unit_number": 4,
                        "title": "Vector Semantics & Word Embeddings",
                        "hours": 9,
                        "topics": [
                            {"name": "Distributional Semantics", "subtopics": ["Term-document matrix", "TF-IDF weighting", "Pointwise Mutual Information (PMI)"]},
                            {"name": "Dense Embeddings", "subtopics": ["Word2Vec (Skip-gram & CBOW)", "GloVe vectors", "FastText subword embeddings", "Cosine similarity evaluation"]},
                        ]
                    },
                    {
                        "unit_number": 5,
                        "title": "Transformers & Modern Sequence Models",
                        "hours": 9,
                        "topics": [
                            {"name": "Recurrent Models & Seq2Seq", "subtopics": ["LSTM", "GRU", "Encoder-Decoder architecture", "Bahdanau attention"]},
                            {"name": "The Transformer Architecture", "subtopics": ["Scaled dot-product attention", "Multi-head attention", "Positional encoding"]},
                            {"name": "Pretrained Language Models", "subtopics": ["BERT masked language modeling", "GPT autoregressive generation", "Fine-tuning on downstream GLUE benchmarks"]},
                        ]
                    },
                ]
            }

            syllabus = Syllabus(
                subject_id=subject.id,
                version=1,
                structured_data=syllabus_data,
                status="CONFIRMED",
                confirmed_by=user.id,
            )
            session.add(syllabus)
            await session.flush()

            for u in syllabus_data["units"]:
                u_obj = SyllabusUnit(
                    syllabus_id=syllabus.id,
                    unit_number=u["unit_number"],
                    title=u["title"],
                    hours=u["hours"],
                )
                session.add(u_obj)
                await session.flush()

                for idx, t in enumerate(u["topics"]):
                    t_obj = Topic(
                        unit_id=u_obj.id,
                        name=t["name"],
                        sequence_order=idx + 1,
                        subtopics=t["subtopics"],
                    )
                    session.add(t_obj)

            # Create default blueprints
            bp_mse = ExamBlueprint(
                subject_id=subject.id,
                created_by=user.id,
                exam_type="MSE",
                total_marks=30,
                units_covered=[1, 2, 3],
                difficulty_distribution={"EASY": 30, "MEDIUM": 50, "HARD": 20},
                bloom_distribution={"Remember": 10, "Understand": 30, "Apply": 40, "Analyze": 20},
                section_structure=[
                    {"name": "Section A", "total_marks": 10, "marks_per_question": 2, "num_questions_to_answer": 5, "num_questions_given": 5, "question_type": "SHORT"},
                    {"name": "Section B", "total_marks": 20, "marks_per_question": 10, "num_questions_to_answer": 2, "num_questions_given": 3, "question_type": "LONG"},
                ],
                status="APPROVED",
            )
            session.add(bp_mse)

            bp_ese = ExamBlueprint(
                subject_id=subject.id,
                created_by=user.id,
                exam_type="ESE",
                total_marks=50,
                units_covered=[1, 2, 3, 4, 5],
                difficulty_distribution={"EASY": 20, "MEDIUM": 60, "HARD": 20},
                bloom_distribution={"Remember": 10, "Understand": 25, "Apply": 35, "Analyze": 20, "Evaluate": 10},
                section_structure=[
                    {"name": "Section A", "total_marks": 10, "marks_per_question": 2, "num_questions_to_answer": 5, "num_questions_given": 5, "question_type": "SHORT"},
                    {"name": "Section B", "total_marks": 20, "marks_per_question": 5, "num_questions_to_answer": 4, "num_questions_given": 6, "question_type": "MEDIUM"},
                    {"name": "Section C", "total_marks": 20, "marks_per_question": 10, "num_questions_to_answer": 2, "num_questions_given": 4, "question_type": "LONG"},
                ],
                has_internal_choice=True,
                status="APPROVED",
            )
            session.add(bp_ese)

        await session.commit()
        print("\nSeed completed successfully!")
        print("Credentials: faculty@university.edu / Password123!")


if __name__ == "__main__":
    asyncio.run(seed())
