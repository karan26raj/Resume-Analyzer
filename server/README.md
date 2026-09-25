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

## Interview Coach

* 4-5 likely interview questions for each technology the job cares about
* Covers technologies missing from the resume, so gaps can be prepared for
* Question type (conceptual, practical, scenario, experience) and difficulty
* Answer guide: what the interviewer looks for and the points a strong answer covers
* Questions about the candidate's experience quote the resume, verified in code

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

# Getting Started

The application has four parts that run side by side:

| Part | What it does | Runs as |
| ---- | ------------ | ------- |
| Infrastructure | PostgreSQL (data), Qdrant (vectors), Redis (cache, rate limits, task queue) | Docker containers |
| API | FastAPI backend on http://127.0.0.1:8000 | `uvicorn` |
| Worker | Indexes uploaded resumes and jobs for search | `celery` |
| Frontend | React app on http://localhost:5173 (in `../client`) | `npm run dev` |

**Requirements:** Python 3.12+, Node.js 20+, Docker Desktop and a Gemini API key.

---

## One-Time Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd <repository>/server
```

### 2. Create the virtual environment and install the backend

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create `server/.env`

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer
TEST_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer_test

JWT_SECRET_KEY=replace_with_a_long_random_string
GEMINI_API_KEY=your_gemini_api_key

CORS_ORIGINS=["http://localhost:5173"]
```

Everything else has sensible defaults (see [Optional Settings](#optional-settings)). The credentials above match `docker-compose.yml`. Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

### 4. Start the infrastructure

```powershell
docker compose up -d
```

This starts PostgreSQL (5432), Qdrant (6333, dashboard at http://localhost:6333/dashboard) and Redis (6379). Create the test database once, for `pytest`:

```powershell
docker compose exec postgres createdb -U postgres resume_analyzer_test
```

### 5. Create the database tables

```powershell
alembic upgrade head
```

### 6. Install the frontend

```powershell
cd ..\client
npm install
```

---

## Running the Application

Do this every time. Use three terminals.

### Step 1: Start Docker Desktop and the containers

From `server/`:

```powershell
docker compose up -d
```

Check with `docker ps` that the `postgres`, `qdrant` and `redis` containers are running.

### Step 2: Start the API (terminal 1)

```powershell
cd server
.\venv\Scripts\activate
uvicorn app.main:app --reload --no-access-log
```

Wait for `Application startup complete`. `--no-access-log` is optional: the API writes its own access log line, with the request ID, for every request.

### Step 3: Start the background worker (terminal 2)

```powershell
cd server
.\venv\Scripts\activate
celery -A app.worker.celery_app:celery_app worker --pool=threads --concurrency=4 --loglevel=info
```

Wait for `celery@<computer-name> ready`. `--pool=threads` is required on Windows.

### Step 4: Start the frontend (terminal 3)

```powershell
cd client
npm run dev
```

### Step 5: Check that everything is connected

Open http://127.0.0.1:8000/health:

```json
{"status": "healthy", "redis": "connected", "worker": "online"}
```

### Step 6: Open the app

Go to http://localhost:5173 and register an account. The API documentation is at http://127.0.0.1:8000/docs.

### Stopping

Press `Ctrl + C` in each terminal, then optionally stop the containers from `server/` with `docker compose stop`. Data is kept; `docker compose down -v` would delete it.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `/health` shows `"worker": "offline"` | Start the worker (step 3). The status is cached, so it can take up to 15 seconds to change. |
| `/health` shows `"redis": "unavailable"` | `docker compose up -d redis` |
| The API fails to start with a database connection error | `docker compose up -d postgres`, and check `DATABASE_URL` |
| "Search is temporarily unavailable" | Qdrant isn't running: `docker compose up -d qdrant` |
| New uploads stay "Queued" | The worker isn't running (step 3) |
| "AI features are not configured on this server" | Set `GEMINI_API_KEY` in `server/.env` and restart the API and worker |
| The frontend says "Cannot reach the server" | The API isn't running, or crashed: check terminal 1 |
| `'celery' is not recognized` or `'uvicorn' is not recognized` | Activate the virtual environment first: `.\venv\Scripts\activate` |
| `port is already allocated` from Docker | Another container or program uses that port: `docker ps` shows which; stop it |

The worker is optional: without it the API still works, new documents simply stay `queued` until a worker starts (the queue lives in Redis, so nothing is lost), and match analysis indexes a resume on the fly when it needs it. Set `TASK_QUEUE_ENABLED=False` to index in the API process instead.

### Upgrading an existing installation

After pulling new code, run `pip install -r requirements.txt`, `alembic upgrade head` and (in `client/`) `npm install`. Documents created before background indexing existed start as `pending`; reconcile them with Qdrant, and queue any that are missing, while the worker is running:

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

## Interview Coach API

| Method | Endpoint             | Notes                                                                                  |
| ------ | -------------------- | -------------------------------------------------------------------------------------- |
| POST   | /interview/questions | `{resume_id, job_id, force?}` → questions grouped by technology, 4-5 per technology    |

Gemini picks the technologies and writes the questions; the result is then verified in code:

* A technology is kept only if it is mentioned in the job description or the resume (spelling variants such as "React.js" / "React" count; different technologies such as "Java" / "JavaScript" don't). Whether it appears in both, only the job (`"source": "job"`, a gap to prepare for) or only the resume is decided in code, not by the model.
* A resume quote attached to a question must really be in the resume, otherwise it is removed.
* Duplicate questions are dropped, each technology keeps at most 5 questions and needs at least 4, and at most 8 technologies are covered. Anything removed is listed under `skipped` with the reason.

Results are cached for 24 hours per resume/job pair (`"cached": true`; send `"force": true` to regenerate) and count towards the `ai-generate` rate limit.

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
| Interview questions | `interview:{user}:r{resume}:j{job}` → full response | 24 h | the resume or job is deleted |
| `GET /recommendations`, `GET /recommendations/jobs` | `recs:{user}:v{version}:…` | 10 min | anything the user changes (upload, new job, delete, new analysis) bumps `{version}` |

* Repeating `POST /analysis/match` or `POST /resumes/rewrite` for the same pair returns the earlier result with `"cached": true` (analysis: status 200 instead of 201) and makes no Gemini call. Send `"force": true` to run a new one.
* Resumes and jobs can't be edited, so a pair's cached result stays valid until one of them is deleted. A cached analysis ID is re-checked in PostgreSQL before it is returned.
* Rate limits (fixed window, `429 Too Many Requests` with a `Retry-After` header):

| Bucket | Applies to | Default |
| ------ | ---------- | ------- |
| `login` | `POST /auth/login`, per client IP | 10 per 5 min |
| `register` | `POST /auth/register`, per client IP | 5 per hour |
| `ai-generate` | analysis, rewrite, interview questions and assistant (Gemini text generation), per user | 20 per 10 min |
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

# Error Handling and Logging

Every response has an `X-Request-ID` header (a caller-supplied ID is kept if it is short and safe). Every error has the same shape:

```json
{"detail": "Resume not found", "code": "not_found", "request_id": "1dedd32d86fd42ee9b32e914c3b04d50"}
```

| Status | `code` | When |
| ------ | ------ | ---- |
| 400 | `bad_request` | Invalid upload (wrong type, empty file) |
| 401 | `not_authenticated` | Missing, invalid or expired token |
| 404 | `not_found` | Resource doesn't exist or belongs to another user |
| 409 | `conflict` | Email already registered |
| 413 | `payload_too_large` | Upload over `MAX_UPLOAD_SIZE_BYTES` |
| 422 | `validation_error` | Invalid request body (`detail` lists the fields; submitted values are never echoed) |
| 429 | `rate_limited` | Rate limit hit (`Retry-After` header) |
| 500 | `internal_error` | A bug: generic message, full traceback in the log under the same request ID |
| 502 | `upstream_error` | Gemini returned something unusable |
| 503 | `ai_unavailable`, `ai_rate_limited`, `ai_not_configured`, `vector_store_unavailable`, `database_unavailable` | A dependency is down or overloaded (`Retry-After` header) |

Raw errors from Gemini, Qdrant and PostgreSQL are logged in full but never sent to clients. Log lines carry the request ID, including lines written by the Celery worker for a task that request queued:

```text
2026-09-25 11:33:29,363 INFO [1dedd32d86fd42ee9b32e914c3b04d50] app.access: GET /resumes/999 404 16ms
```

The frontend shows the first 8 characters of the request ID with server errors (`… (ref 1dedd32d)`), so a reported problem can be found in the log.

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
LOG_LEVEL=INFO
LOG_JSON=False

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

INTERVIEW_MIN_QUESTIONS=4
INTERVIEW_MAX_QUESTIONS=5
INTERVIEW_MAX_TECHNOLOGIES=8

TASK_QUEUE_ENABLED=True
CELERY_BROKER_URL=redis://localhost:6379/1
INDEX_TASK_MAX_RETRIES=3
INDEX_TASK_RETRY_BASE_SECONDS=10
```

If `GEMINI_MODEL` is overloaded (503), rate limited (429) or retired (404), match analysis and the assistant automatically try each fallback model in order. Each stored analysis records the model that actually produced it.
