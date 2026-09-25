# AI Resume Analyzer API

AI Resume Analyzer is a production-style backend application built with FastAPI, PostgreSQL, Gemini AI, and Qdrant Vector Database. The platform analyzes resumes against job descriptions, identifies skill gaps, calculates match scores, generates recommendations, and provides AI-powered question answering using Retrieval-Augmented Generation (RAG).

The project is designed to demonstrate modern Backend Engineering, Generative AI integration, Vector Databases, Semantic Search, and RAG-based applications.

---

# Features

## Authentication & Security

* User Registration
* User Login
* JWT Authentication
* Protected API Routes
* Password Hashing (Argon2)
* User-specific Data Access

## Resume Management

* Upload PDF Resumes
* Upload DOCX Resumes
* File Validation
* Secure File Storage
* Resume Text Extraction
* Resume Metadata Storage
* Resume Text Retrieval
* Resume Listing

### Supported Parsers

* PyMuPDF (PDF)
* python-docx (DOCX)

## Job Description Management

* Create Job Descriptions
* Store Jobs in PostgreSQL
* Retrieve Job Details
* List Saved Jobs
* Delete Jobs

## AI Resume Analysis

* Resume vs Job Matching
* AI Match Score Generation
* Matched Skills Detection
* Missing Skills Detection
* Strength Analysis
* Weakness Analysis
* Personalized Recommendations
* Structured JSON Output

## AI Recommendations

* Resume Improvement Suggestions
* Skill Development Recommendations
* Career Growth Suggestions
* Job Readiness Feedback

## Embeddings & Semantic Search

* Gemini Embedding API Integration
* Resume Chunking
* Job Description Chunking
* Vector Generation
* Vector Storage in Qdrant
* Semantic Similarity Search
* Embedding-Based Retrieval

## RAG Assistant

* Resume Question Answering
* Job Description Question Answering
* Semantic Context Retrieval
* Gemini-Powered Responses
* Source Attribution
* Retrieval-Augmented Generation (RAG)

---

# Current AI Stack

* Gemini 3.6 Flash
* Gemini Embedding API
* FastAPI
* PostgreSQL
* SQLAlchemy
* Pydantic
* JWT Authentication
* Qdrant Vector Database
* PyMuPDF
* Docker

---

# Project Architecture

```text
User
 │
 ▼
FastAPI Backend
 │
 ├── Authentication Layer
 │
 ├── Resume Service
 │     ├── PDF Parser
 │     └── DOCX Parser
 │
 ├── Job Service
 │
 ├── Analysis Service
 │     └── Gemini 3.6 Flash
 │
 ├── Recommendation Service
 │     └── Gemini 3.6 Flash
 │
 ├── Embedding Service
 │     └── Gemini Embeddings
 │
 ├── RAG Assistant
 │     ├── Semantic Retrieval
 │     ├── Context Builder
 │     └── Gemini Response Generator
 │
 ├── Vector Store
 │     └── Qdrant
 │
 └── PostgreSQL Database
```

---

# Resume Processing Flow

```text
Upload Resume
      │
      ▼
Validate File
      │
      ▼
Extract Text
      │
      ▼
Store Resume
      │
      ▼
Generate Embeddings
      │
      ▼
Store Vectors in Qdrant
      │
      ▼
Enable Semantic Search
      │
      ▼
RAG Question Answering
```

---

# Tech Stack

## Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* Alembic

## Database

* PostgreSQL
* Qdrant Vector Database

## AI & GenAI

* Gemini 3.6 Flash
* Gemini Embeddings
* Vector Search
* Retrieval-Augmented Generation (RAG)

## Authentication

* JWT
* Argon2 Password Hashing

## Dev Tools

* Docker
* Git
* GitHub
* Postman
* VS Code
* Pytest

---

# Setup

## Clone Repository

```bash
git clone <your-repository-url>
cd server
```

## Create Virtual Environment

```powershell
python -m venv venv

.\venv\Scripts\activate

pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file:

```env
APP_NAME=AI Resume Analyzer
DEBUG=False

DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer
TEST_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer_test

JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_BYTES=10485760

GEMINI_API_KEY=my_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001

EMBEDDING_CHUNK_SIZE_WORDS=300
EMBEDDING_CHUNK_OVERLAP_WORDS=50
MAX_EMBEDDING_CHUNKS=50

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=resume_embeddings
```

---

## Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Dashboard:

```text
http://localhost:6333/dashboard
```

---

## Run Database Migrations

```powershell
alembic upgrade head
```

---

## Start FastAPI Server

```powershell
uvicorn app.main:app --reload
```

---

# API Documentation

Swagger UI

```text
http://127.0.0.1:8000/docs
```

ReDoc

```text
http://127.0.0.1:8000/redoc
```

---

# Main API Endpoints

## Authentication

| Method | Endpoint       |
| ------ | -------------- |
| POST   | /auth/register |
| POST   | /auth/login    |
| GET    | /auth/me       |

## Resume APIs

| Method | Endpoint                  |
| ------ | ------------------------- |
| POST   | /resumes/upload           |
| GET    | /resumes                  |
| GET    | /resumes/{resume_id}      |
| GET    | /resumes/{resume_id}/text |

| DELETE | /resumes/{resume_id}      |

Uploading a resume automatically indexes it for semantic search in the background (`AUTO_INDEX_DOCUMENTS`). Deleting a resume also removes its stored file, analyses and vectors.

## Job APIs

| Method | Endpoint       |
| ------ | -------------- |
| POST   | /jobs          |
| GET    | /jobs          |
| GET    | /jobs/{job_id} |
| DELETE | /jobs/{job_id} |

Creating a job indexes it automatically; deleting a job removes its analyses and vectors.

## Analysis APIs

| Method | Endpoint                 | Notes                                        |
| ------ | ------------------------ | -------------------------------------------- |
| POST   | /analysis/match          | Match a resume against a job with Gemini     |
| GET    | /analysis                | History, optional `resume_id` / `job_id`     |
| GET    | /analysis/{analysis_id}  | A single stored analysis                     |

### How a match is scored

1. **Retrieval (RAG):** the job description is embedded and the most similar passages of the resume are pulled from Qdrant (the resume is indexed on the fly if needed).
2. **Evidence-based assessment:** Gemini lists the job's requirements (skill / experience / education, required / preferred) and judges each one as met, partial or missing, quoting the resume verbatim as evidence.
3. **Verification:** every quote is checked against the resume. An unverifiable "met" becomes "partial" and an unverifiable "partial" becomes "missing".
4. **Scoring in code:** skills 40%, experience 25%, education 10%, semantic similarity 25%. Parts that can't be measured are re-weighted. The response includes `requirements`, `score_breakdown`, `semantic_similarity` and `retrieved_evidence`, so every score is explainable.

## Recommendations API

| Method | Endpoint              | Notes                                                                 |
| ------ | --------------------- | --------------------------------------------------------------------- |
| GET    | /recommendations      | Most frequent missing skills and latest recommendations               |
| GET    | /recommendations/jobs | Your saved jobs ranked by semantic similarity to a resume (`resume_id`, `limit`) |

## Resume Rewriting API

| Method | Endpoint         | Notes                                                                                   |
| ------ | ---------------- | --------------------------------------------------------------------------------------- |
| POST   | /resumes/rewrite | `{resume_id, job_id}` → rewrites of existing resume lines tailored to the job           |

Rewrites are validated in code: the original line must exist in the resume, and a rewrite that adds any technology, number or name not already in the resume is returned under `rejected` with the reason and the offending terms.

## Embeddings & Assistant APIs

| Method | Endpoint           | Notes                                                               |
| ------ | ------------------ | ------------------------------------------------------------------- |
| POST   | /embeddings/index  | (Re-)index a resume or job manually                                 |
| POST   | /embeddings/search | Semantic search, optional `document_type` filter                    |
| POST   | /assistant/ask     | RAG Q&A, optionally scoped with `resume_id` and/or `job_id`         |

---

# Local Infrastructure

`docker-compose.yml` starts PostgreSQL and Qdrant:

```bash
docker compose up -d
```

---

# Running Tests

Tests use the `TEST_DATABASE_URL` database and an in-memory Qdrant. Gemini is never called.

```powershell
pytest
```

---

# Optional Settings

```env
CORS_ORIGINS=["http://localhost:5173"]
AUTO_INDEX_DOCUMENTS=True
EMBEDDING_DIMENSIONS=3072
GEMINI_TIMEOUT_SECONDS=60
GEMINI_MAX_RETRIES=2
GEMINI_FALLBACK_MODELS=["gemini-3.6-flash","gemini-3.8-flash","gemini-3.5-flash-lite","gemini-flash-lite-latest"]
```

If `GEMINI_MODEL` is overloaded (503), rate limited (429) or retired (404), match analysis and the assistant automatically try each fallback model in order. Each stored analysis records the model that actually produced it.
