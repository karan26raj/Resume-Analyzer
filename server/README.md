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

The backend has five parts, all defined in `docker-compose.yml`; the frontend (in `../client`) runs separately.

| Part | What it does | Port |
| ---- | ------------ | ---- |
| `postgres` | Users, resumes, jobs and analyses | 5432 |
| `qdrant` | Vectors of resume and job chunks (dashboard: http://localhost:6333/dashboard) | 6333 |
| `redis` | Cache and rate limits (database 0), Celery task queue (database 1) | 6379 |
| `api` | FastAPI backend (runs migrations first, via the one-off `migrate` service) | 8000 |
| `worker` | Celery worker that indexes uploaded resumes and jobs | — |
| Frontend | React app | 5173 |

**Requirements:** Docker Desktop, Node.js 20+, a Gemini API key. Python 3.12+ only if you run the backend outside Docker or run the tests.

---

## One-Time Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd <repository>/server
```

### 2. Create `server/.env`

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer
TEST_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/resume_analyzer_test

JWT_SECRET_KEY=replace_with_a_long_random_string
GEMINI_API_KEY=your_gemini_api_key

CORS_ORIGINS=["http://localhost:5173"]

POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=resume_analyzer
```

`POSTGRES_*` configure the PostgreSQL container and must match the user, password and database in `DATABASE_URL`. Choose your own password; the container only reads it the first time it creates its data volume. Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Everything else has defaults (see [Optional Settings](#optional-settings)). Inside Docker, the database, Qdrant, Redis and upload settings are set by `docker-compose.yml`, so the `localhost` values above are only used when you run the backend outside Docker.

### 3. Install the frontend

```powershell
cd ..\client
npm install
```

---

## Running with Docker (recommended)

### Step 1: Start the backend

From `server/`:

```powershell
docker compose up -d --build
```

This builds the image, starts PostgreSQL, Qdrant and Redis, waits until they are healthy, applies database migrations, then starts the API and the worker. Check with `docker compose ps`: every service should be `healthy` (and `migrate` `Exited (0)`).

`docker compose up` also applies `docker-compose.override.yml`, which runs the code from this folder and restarts the API and worker when you edit a file. For a production-like run without it: `docker compose -f docker-compose.yml up -d --build`.

### Step 2: Start the frontend

```powershell
cd client
npm run dev
```

### Step 3: Check and open

- http://127.0.0.1:8000/health should show `{"status": "healthy", "redis": "connected", "worker": "online"}`
- Open http://localhost:5173 and register an account. API docs: http://127.0.0.1:8000/docs

### Everyday commands

| Task | Command |
| ---- | ------- |
| Follow the API or worker logs | `docker compose logs -f api` / `docker compose logs -f worker` |
| Stop everything (data is kept) | `docker compose stop` |
| Start again | `docker compose up -d` |
| Rebuild after changing `requirements.txt` | `docker compose up -d --build` |
| Run a script in the container | `docker compose exec api python -m app.scripts.sync_index_status --queue` |
| Delete everything, including data | `docker compose down -v` |

Data lives in named volumes (`postgres_data`, `qdrant_data`, `redis_data`, `uploads`), so it survives restarts and rebuilds. In development, uploaded files are stored in `server/uploads` instead.

### Moving an existing local PostgreSQL into Docker

If your data lives in a PostgreSQL installed on your computer, copy it into the container once, then stop the local server so only one database uses port 5432:

```powershell
pg_dump -h localhost -U postgres -d resume_analyzer -Fc --no-owner --no-privileges -f resume_analyzer.dump
docker compose up -d postgres            # use $env:POSTGRES_PORT=55432 first if the local server still holds 5432
docker compose cp resume_analyzer.dump postgres:/tmp/resume_analyzer.dump
docker compose exec postgres pg_restore -U postgres -d resume_analyzer --no-owner --no-privileges /tmp/resume_analyzer.dump
docker compose exec postgres createdb -U postgres resume_analyzer_test
```

Then re-create the vectors in the container's Qdrant: `docker compose exec api python -m app.scripts.sync_index_status --queue`.

Host ports can be changed if something else already uses them, e.g. `$env:POSTGRES_PORT=5433; docker compose up -d` (also `QDRANT_PORT`, `REDIS_PORT`, `API_PORT`). To keep using a PostgreSQL installed on your computer instead of the container, set `DB_HOST=host.docker.internal` (and `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` to match).

---

## Running Without Docker (API and worker on your machine)

Useful for debugging with breakpoints. Use three terminals.

### One-time: virtual environment and database

From `server/`:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements-dev.txt
docker compose up -d postgres qdrant redis
alembic upgrade head
```

`requirements-dev.txt` adds the test tools to `requirements.txt`.

### Every time

1. `docker compose up -d postgres qdrant redis` (from `server/`)
2. Terminal 1, the API: `.\venv\Scripts\activate` then `uvicorn app.main:app --reload --no-access-log`
3. Terminal 2, the worker: `.\venv\Scripts\activate` then `celery -A app.worker.celery_app:celery_app worker --pool=threads --concurrency=4 --loglevel=info` (`--pool=threads` is required on Windows)
4. Terminal 3, the frontend: `cd client` then `npm run dev`

Don't run the Docker `api`/`worker` services and the local ones at the same time: both would use port 8000 and the same queue.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `port is already allocated` or `address already in use` | Another program or container uses that port (e.g. a PostgreSQL installed on Windows, or an older Qdrant container). Stop it, or change the host port (see above). |
| A service is `unhealthy` or keeps restarting | `docker compose logs <service>` shows why |
| `migrate` exited with an error | `docker compose logs migrate`; fix the cause, then `docker compose up -d` again |
| `/health` shows `"worker": "offline"` | The worker isn't running: `docker compose ps worker`, `docker compose logs worker`. The status is cached for 15 seconds. |
| `/health` shows `"redis": "unavailable"` | `docker compose up -d redis` |
| "Search is temporarily unavailable" | Qdrant isn't reachable: `docker compose ps qdrant` |
| New uploads stay "Queued" | The worker isn't running |
| "AI features are not configured on this server" | Set `GEMINI_API_KEY` in `server/.env`, then `docker compose up -d` to recreate the containers |
| The frontend says "Cannot reach the server" | The API isn't running on port 8000: `docker compose ps api` |
| `'celery'` / `'uvicorn'` is not recognized (without Docker) | Activate the virtual environment: `.\venv\Scripts\activate` |

### Upgrading an existing installation

After pulling new code: `docker compose up -d --build` (it applies new migrations automatically) and `npm install` in `client/`. Without Docker: `pip install -r requirements-dev.txt` and `alembic upgrade head`.

Documents created before background indexing existed start as `pending`. Reconcile them with Qdrant, and queue any that are missing, while the worker runs:

```powershell
docker compose exec api python -m app.scripts.sync_index_status --queue
```

---

# Deploying for Free

The app runs on free tiers of managed services. Free tiers change, so check each provider's current limits.

| Piece | Service | Free-tier behaviour |
| ----- | ------- | ------------------- |
| Frontend | Vercel | Always on |
| API | Render (Docker, from `render.yaml`) | Sleeps after ~15 minutes idle; the first request then takes 30-60 s |
| PostgreSQL | Neon | Suspends when idle and wakes on the next query |
| Redis (cache, rate limits) | Upstash | Command limits per day/month |
| Vectors | Qdrant Cloud | Free 1 GB cluster; may be suspended after long inactivity |
| AI | Google AI Studio (Gemini) | Free-tier request limits |

There is no worker on the free plan: `TASK_QUEUE_ENABLED=false` makes the API index documents itself, and `STORE_UPLOADED_FILES=false` keeps only the extracted text, because Render's free instances have no persistent disk.

## Step 1: Push the code to GitHub

Render and Vercel deploy from a GitHub repository. `.env` files are git-ignored, so secrets are not pushed.

## Step 2: Create the data services

1. **Neon** (https://neon.tech): create a project, then copy its connection string (`postgresql://…?sslmode=require`). Use the direct connection, not the `-pooler` one.
2. **Qdrant Cloud** (https://cloud.qdrant.io): create a free cluster, then copy its URL (`https://…cloud.qdrant.io:6333`) and create an API key.
3. **Upstash** (https://upstash.com): create a Redis database in the region closest to your Render region, then copy the `rediss://…` URL.
4. **Gemini**: create an API key at https://aistudio.google.com/apikey.

## Step 3: Deploy the API on Render

1. In Render, choose **New → Blueprint** and select your repository. Render reads `render.yaml`.
2. Enter the values it asks for:

   | Variable | Value |
   | -------- | ----- |
   | `DATABASE_URL` | The Neon connection string (the `postgres://` or `postgresql://` form works as given) |
   | `GEMINI_API_KEY` | Your Gemini key |
   | `QDRANT_URL` / `QDRANT_API_KEY` | From Qdrant Cloud |
   | `REDIS_URL` | The Upstash `rediss://` URL |
   | `CORS_ORIGINS` | `["https://your-project.vercel.app"]` (update it after step 4 if the name differs) |

   `JWT_SECRET_KEY` is generated by Render. The other settings come from `render.yaml`.
3. Deploy. Migrations run automatically on every start. Check `https://<your-api>.onrender.com/health`: it should show `"status": "healthy"`, `"redis": "connected"` and `"worker": "disabled"`.

## Step 4: Deploy the frontend on Vercel

1. In Vercel, choose **Add New → Project**, import the repository and set **Root Directory** to `client`. `client/vercel.json` configures the build.
2. Add the environment variable `VITE_API_BASE_URL` = `https://<your-api>.onrender.com`.
3. Deploy, then make sure the Vercel URL is in Render's `CORS_ORIGINS` (changing it redeploys the API).

Open the Vercel URL and register an account. The first visit after the API has slept takes up to a minute.

## Step 5 (optional): Move your existing data

```powershell
docker compose exec postgres pg_dump -U postgres -d resume_analyzer -Fc --no-owner --no-privileges -f /tmp/app.dump
docker compose cp postgres:/tmp/app.dump app.dump
pg_restore -d "<Neon connection string>" --no-owner --no-privileges app.dump
```

Then create the vectors in Qdrant Cloud by running the reconcile script on your computer against the cloud services (it indexes directly because the queue is disabled):

```powershell
$env:DATABASE_URL="<Neon connection string>"; $env:QDRANT_URL="<Qdrant URL>"; $env:QDRANT_API_KEY="<key>"; $env:TASK_QUEUE_ENABLED="false"
python -m app.scripts.sync_index_status --queue
```

Uploaded PDFs are not moved: with `STORE_UPLOADED_FILES=false` only the extracted text is kept, which is all the features need.

## Production settings

| Setting | Purpose |
| ------- | ------- |
| `ENVIRONMENT=production` | Refuses to start if `DEBUG` is on, `JWT_SECRET_KEY` is shorter than 32 characters, or `CORS_ORIGINS` is empty or `*` |
| `CORS_ORIGIN_REGEX` | Optional, to also allow Vercel preview URLs, which end with your Vercel username or team: e.g. `^https://your-project-[a-z0-9-]+-your-username\.vercel\.app$` |
| `TRUSTED_PROXY_COUNT` | How many proxies add to `X-Forwarded-For`; the rate limiter and the access log use the entry that many from the end. `render.yaml` sets 1; check the IP at the end of each access log line in Render's logs is your own, and adjust if not |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant Cloud (instead of `QDRANT_HOST` / `QDRANT_PORT`) |
| `STORE_UPLOADED_FILES` | `false` on hosts without a persistent disk |
| `TASK_QUEUE_ENABLED` | `false` when no Celery worker runs |
| `LOG_JSON` | One JSON object per log line |

Render's health check uses `/health/live`, which touches no other service, so health checks don't use up Upstash's free commands.

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

# Docker

* `Dockerfile`: one image (Python 3.13, non-root user) for the API, the worker and migrations. Secrets are never copied into it; `.env` is passed at runtime.
* `docker-compose.yml`: PostgreSQL, Qdrant, Redis, `migrate`, `api` and `worker`, with health checks and start order (migrations run before the API and worker start). Redis persists the task queue (append-only file), so queued indexing work survives a restart.
* `docker-compose.override.yml`: development only; mounts the source and reloads on changes.

---

# Running Tests

Install the test tools with `pip install -r requirements-dev.txt`. Tests use the `TEST_DATABASE_URL` database, an in-memory Qdrant and an in-memory Redis (fakeredis). Celery tasks run eagerly (in-process). Gemini is never called.

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
