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
* Redis (caching, rate limiting and the task queue broker)
* Celery (background worker)
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
Store Resume  ──►  201 response (index_status: "queued")
      │
      ▼
Celery task on Redis
      │
      ▼
Worker: chunk → embed (Gemini) → store vectors in Qdrant
      │
      ▼
index_status: "indexed" (or "failed", with the reason)
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
* Redis

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

## Start the Background Worker

In a second terminal (Redis must be running):

```powershell
celery -A app.worker.celery_app:celery_app worker --pool=threads --concurrency=4 --loglevel=info
```

`--pool=threads` is required on Windows. Without a worker the API still works: new documents stay `queued` until a worker starts (the queue lives in Redis, so nothing is lost), and match analysis indexes a resume on the fly when it needs it. Set `TASK_QUEUE_ENABLED=False` to index in the API process instead.

Documents created before phase 15 start as `pending`. To reconcile them with Qdrant (and queue any that are missing):

```powershell
python -m app.scripts.sync_index_status --queue
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

Uploading a resume queues it for indexing on the background worker (`AUTO_INDEX_DOCUMENTS`). Resume and job responses include `index_status` (`pending`, `queued`, `processing`, `indexed`, `failed`), `index_error`, `indexed_at` and `chunk_count`. Deleting a resume also removes its stored file, analyses and vectors.

## Job APIs

| Method | Endpoint       |
| ------ | -------------- |
| POST   | /jobs          |
| GET    | /jobs          |
| GET    | /jobs/{job_id} |
| DELETE | /jobs/{job_id} |

Creating a job queues it for indexing the same way; deleting a job removes its analyses and vectors.

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

# Caching and Rate Limiting (Redis)

PostgreSQL is always the source of truth; Redis only saves repeated work.

| What | Key | TTL | Invalidated when |
| ---- | --- | --- | ---------------- |
| Match analysis | `analysis:{user}:r{resume}:j{job}` → analysis ID | 24 h | the resume or job is deleted |
| Resume rewrite | `rewrite:{user}:r{resume}:j{job}` → full response | 24 h | the resume or job is deleted |
| `GET /recommendations`, `GET /recommendations/jobs` | `recs:{user}:v{version}:…` | 10 min | anything the user changes (upload, new job, delete, new analysis) bumps `{version}` |

* Repeating `POST /analysis/match` or `POST /resumes/rewrite` for the same pair returns the earlier result with `"cached": true` (analysis: status 200 instead of 201) and makes no Gemini call. Send `"force": true` to run a new one.
* Resumes and jobs can't be edited, so a pair's cached result stays valid until one of them is deleted. A cached analysis ID is re-checked in PostgreSQL before it is returned.
* Rate limits (fixed window, `429 Too Many Requests` with a `Retry-After` header):

| Bucket | Applies to | Default |
| ------ | ---------- | ------- |
| `login` | `POST /auth/login`, per client IP | 10 per 5 min |
| `register` | `POST /auth/register`, per client IP | 5 per hour |
| `ai-generate` | analysis, rewrite and assistant (Gemini text generation), per user | 20 per 10 min |
| `ai-embed` | `POST /embeddings/search` and `/embeddings/index`, per user | 60 per 10 min |

  Cache hits don't count towards `ai-generate`.
* **Redis is optional.** If it is down, the API keeps working without cache or limits, skips Redis for 30 seconds after a failure, and `GET /health` reports `"redis": "unavailable"`. Set `REDIS_URL=` (empty) to disable it.

---

# Background Processing (Celery)

Embedding a document calls the Gemini API and can take seconds, so it runs on a Celery worker instead of inside the upload request.

* **Durable:** tasks wait in Redis (database 1, separate from the cache), so they survive API restarts and run as soon as a worker is available.
* **Retries:** transient failures (Gemini 429/503, Qdrant hiccups) are retried 3 times with exponential backoff (10 s, 20 s, 40 s); the document shows `queued` with the last error meanwhile. An empty document fails immediately.
* **At-least-once:** tasks are acknowledged only after they finish, so a crashed worker's task is redelivered. Indexing is idempotent (it replaces the document's vectors), so running it twice is harmless.
* **Deletes are safe:** a document deleted while it is being embedded has its new vectors removed.
* **Fallback:** if the broker is unreachable when a document is created, the API indexes it in-process after the response and skips the queue for 30 seconds.
* `GET /health` reports the worker: `online`, `offline` (no worker running), `unavailable` (broker down) or `disabled`.

---

# Local Infrastructure

`docker-compose.yml` starts PostgreSQL, Qdrant and Redis (cache in database 0, Celery broker in database 1):

```bash
docker compose up -d
```

---

# Running Tests

Tests use the `TEST_DATABASE_URL` database, an in-memory Qdrant and an in-memory Redis (fakeredis). Celery tasks run eagerly (in-process). Gemini is never called.

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

REDIS_URL=redis://localhost:6379/0
CACHE_TTL_ANALYSIS_SECONDS=86400
CACHE_TTL_REWRITE_SECONDS=86400
CACHE_TTL_RECOMMENDATIONS_SECONDS=600
RATE_LIMIT_ENABLED=True
RATE_LIMIT_LOGIN=10
RATE_LIMIT_AI_GENERATE=20

TASK_QUEUE_ENABLED=True
CELERY_BROKER_URL=redis://localhost:6379/1
INDEX_TASK_MAX_RETRIES=3
INDEX_TASK_RETRY_BASE_SECONDS=10
```

If `GEMINI_MODEL` is overloaded (503), rate limited (429) or retired (404), match analysis and the assistant automatically try each fallback model in order. Each stored analysis records the model that actually produced it.
