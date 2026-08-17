# ADAPT — AI-Driven Academic Planning & Assessment Tool

> **End-to-End Agentic Outcomes-Based Education (OBE) Platform**
> Automated Syllabus Ingestion, RAG Grounding, Course Outcomes (CO) Generation, Bloom's Taxonomy Classification, CO-PO Mapping, 15-Week Academic Activity Plans (AAP), Question Banking, Exam Papers (MSE/ESE), Step-by-Step Marking Rubrics, and Print-Ready DOCX Document Export.

---

## 🏛️ Core Architectural Principle

```
SOURCE (PDF/DOCX)
   ↓
RETRIEVE (pgvector RAG)
   ↓
REASON (LLM Provider)
   ↓
GENERATE (Structured JSON)
   ↓
VALIDATE (Deterministic Code)
   ↓
REVIEW (Faculty Approval)
   ↓
EXPORT (Official DOCX/PDF)
```

**LLM** = Semantic Reasoning & Question Generation  
**RAG** = Syllabus Grounding & Source Tracking  
**Agent** = Autonomous Multi-Tool Orchestration  
**Database** = Relational PostgreSQL + pgvector State  
**Validators** = Deterministic Arithmetic, Bloom, Coverage & Duplicate Correctness  
**Templates** = University-Branded Documents  
**Faculty** = Final Human-in-the-Loop Authority  

---

## 🌟 Key Modules

| Module | Description | Engine |
|---|---|---|
| **Syllabus Ingestion & RAG** | Ingests PDF / DOCX syllabi, chunks by Unit boundaries with 200-char overlap, embeds via `text-embedding-3-small`, indexes into `pgvector`. | PyMuPDF + python-docx + pgvector |
| **Course Outcomes (COs)** | Generates 4–6 measurable, action-verb driven outcomes mapped to syllabus units with cognitive progression. | LLM + RAG + OBE Rules |
| **Bloom Classifier** | Classifies questions and outcomes across the 6 Bloom cognitive levels (Remember, Understand, Apply, Analyze, Evaluate, Create) with confidence metrics. | Keyword Baseline + Few-shot LLM |
| **CO-PO Correlation Matrix** | Generates the NBA/Washington Accord 2D correlation matrix (0=None, 1=Low, 2=Med, 3=High) with pedagogical rationales and inline cell overrides. | LLM + NBA Standards |
| **Academic Activity Plan (AAP)** | Generates a 15-week lesson plan distributed across all units, teaching methods (PPT, Chalk, Lab), mapped COs, and contact hours. | Planning Engine + AAP Validator |
| **Question Bank** | Central repository with multi-criteria filtering (Unit, Bloom, Difficulty, Marks, Type). Features embedding cosine similarity duplicate detection (>0.85). | pgvector + Cosine Similarity |
| **MSE & ESE Paper Generator** | Assembles Mid-Semester (30M) and End-Semester (50M) exams from configurable blueprints with multi-section layout and internal choices (Q_A OR Q_B). | Blueprint Engine + LLM |
| **Deterministic Validation** | Validates marks arithmetic, unit coverage, Bloom cognitive percentages, and duplicate questions, generating a real-time validation scorecard. | Deterministic Python Validators |
| **Answer Key & Rubrics** | Produces concise model answers, required key concepts, sequential problem-solving steps, and itemized marking schemes. | LLM Evaluator |
| **Document Publishing** | Exports faculty-ready, styled Word documents (.docx) with university headers, course codes, time allowed, instructions, and OBE tags. | python-docx Template Engine |
| **Supervisor Agent** | Dispatches natural-language faculty instructions (e.g. *"Generate a 30-mark MSE on Units 1-3"*) across the specialized toolchain. | Agent Planner + Execution Trace |

---

## 🛠️ Technology Stack

- **AI Engine**: Google Gemini (`gemini-2.5-flash` / `gemini-1.5-pro` & `text-embedding-004`) via `google-genai` SDK
- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), pgvector, PyMuPDF, python-docx, scikit-learn
- **Database & Vector Store**: PostgreSQL 16 + `pgvector` extension
- **Frontend**: React 18, Vite, Tailwind CSS v3, React Router v7, Axios, Lucide React
- **Containerization**: Docker Compose (`pgvector/pgvector:pg16`, FastAPI backend, Nginx frontend)

---

## 🚀 Quick Start (Docker)

To launch the complete platform with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/adapt.git
cd adapt

# 2. Configure Environment
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY

# 3. Start via Docker Compose
docker compose up --build
```

- **Frontend Faculty Portal**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Default Demo Credentials**: `faculty@university.edu` / `Password123!`

---

## 💻 Local Development Setup

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Seed database with sample course (Natural Language Processing CS602) & NBA POs
python seed_data.py

# Run FastAPI dev server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Running Tests & Research Experiments

### Run Unit Tests:
```bash
cd backend
pytest -v tests/
```

### Run Research Benchmark Experiments:
```bash
# 1. Bloom's Taxonomy Cognitive Classification Experiment (Keyword vs LLM accuracy, F1, Kappa)
python research/experiments/bloom_classification/run_experiment.py

# 2. RAG Grounding Comparison (No RAG vs RAG vs RAG+Validation)
python research/experiments/rag_comparison/run_experiment.py
```

---

## 📁 Repository Structure

```
c:\Projects\ADAPT\
├── frontend/                     # React + Vite + Tailwind Faculty Dashboard
│   ├── src/
│   │   ├── components/           # Syllabus, CO, CO-PO, AAP, Questions, Exams, Export, Agent
│   │   ├── pages/                # Dashboard, SubjectDetailPage, Login, Register
│   │   ├── services/             # Axios API Client
│   │   └── context/              # Auth Context
├── backend/
│   ├── app/
│   │   ├── api/                  # 17 REST API Endpoints
│   │   ├── models/               # SQLAlchemy ORM Models + pgvector
│   │   ├── schemas/              # Pydantic v2 validation models
│   │   ├── ai/                   # LLM/Embedding provider abstractions & generators
│   │   ├── rag/                  # PDF/DOCX parsers, chunker, retriever, context assembler
│   │   ├── validators/           # Deterministic marks, bloom, coverage & duplicate validators
│   │   ├── agents/               # Supervisor Agent orchestrator
│   │   └── document_generation/  # python-docx publication engine
│   ├── tests/                    # Unit tests for validators, chunker, auth
│   └── seed_data.py              # Sample course & PO database seeding
├── data/
│   └── knowledge_base/           # Bloom taxonomy JSON, NBA PO1-PO12, exam rules
├── research/
│   └── experiments/              # Bloom and RAG research evaluation scripts
├── docker-compose.yml            # Multi-container orchestration
└── README.md
```

---

## 🔒 Security & Privacy

- Strict Password Hashing with `bcrypt` (12 rounds)
- JWT Token Authentication (`HS256`, configurable expiration)
- Row-Level Access Controls: Faculty users only access courses and assessments they create
- No API keys exposed to frontend client
- Zero hallucination validation gates before faculty approval
