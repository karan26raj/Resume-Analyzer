# AI Resume Analyzer API

AI Resume Analyzer is a backend project built using FastAPI, PostgreSQL, Gemini API, and Qdrant Vector Database. The goal of this project is to analyze resumes against job descriptions, identify skill gaps, calculate match scores, and provide AI-powered recommendations using LLMs, embeddings, and Retrieval-Augmented Generation (RAG).

This project is being developed as a hands-on learning project to gain practical experience with Backend Development, Generative AI, Vector Databases, and AI-powered applications.

---

## Features Implemented

### Authentication & Security

* User Registration
* User Login
* JWT Authentication
* Protected API Routes
* Password Hashing

### Resume Management

* Upload PDF and DOCX resumes
* File validation
* Secure file storage
* Resume text extraction using PyMuPDF and python-docx
* Store extracted text in PostgreSQL
* View uploaded resumes
* Resume text retrieval

### Job Description Management

* Create job descriptions
* Store job descriptions in PostgreSQL
* View saved job descriptions
* Delete job descriptions

### Resume Analysis

* Resume vs Job Description matching
* AI-generated match score
* Matched skills identification
* Missing skills identification
* Strengths analysis
* Weakness analysis
* Personalized recommendations

### Embeddings & Vector Search

* Gemini Embedding API integration
* Resume chunking
* Vector generation
* Qdrant Vector Database integration
* Resume indexing
* Semantic similarity search
* Vector retrieval using embeddings

### Current AI Stack

* Gemini 2.5 Flash
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

## Project Architecture

```text
User
 │
 ▼
FastAPI Backend
 │
 ├── Authentication Layer
 │
 ├── Resume Upload Service
 │      ├── PDF Parser
 │      └── DOCX Parser
 │
 ├── Job Description Service
 │
 ├── Analysis Service
 │      └── Gemini API
 │
 ├── Embedding Service
 │      └── Gemini Embeddings
 │
 ├── Vector Store
 │      └── Qdrant
 │
 └── PostgreSQL Database
```

---

## Resume Processing Flow

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
```

---

## Tech Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* Alembic

### Database

* PostgreSQL
* Qdrant Vector Database

### AI & GenAI

* Gemini 2.5 Flash
* Gemini Embeddings
* Vector Search
* RAG Concepts

### Authentication

* JWT
* Password Hashing

### Dev Tools

* Docker
* Git
* GitHub
* Postman
* VS Code

---

## Setup

### Create Virtual Environment

```powershell
python -m venv venv

.\venv\Scripts\activate

pip install -r requirements.txt
```

---

### Create .env File

```env
APP_NAME=AI Resume Analyzer

DEBUG=True

DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/resume_analyzer

TEST_DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/resume_analyzer_test

JWT_SECRET_KEY=your_secret_key

JWT_ALGORITHM=HS256

JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

UPLOAD_DIR=uploads

MAX_UPLOAD_SIZE_BYTES=10485760

GEMINI_API_KEY=your_gemini_api_key

GEMINI_MODEL=gemini-2.5-flash

GEMINI_EMBEDDING_MODEL=gemini-embedding-001

EMBEDDING_CHUNK_SIZE_WORDS=500

EMBEDDING_CHUNK_OVERLAP_WORDS=50

QDRANT_HOST=localhost

QDRANT_PORT=6333

QDRANT_COLLECTION_NAME=resume_embeddings
```

---

## Start PostgreSQL

Make sure PostgreSQL is running locally.

---

## Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Verify:

```bash
http://localhost:6333/dashboard
```

---

## Run Migrations

```powershell
alembic upgrade head
```

---

## Start Server

```powershell
uvicorn app.main:app --reload
```

---

## API Documentation

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

## Main API Endpoints

### Authentication

| Method | Endpoint       |
| ------ | -------------- |
| POST   | /auth/register |
| POST   | /auth/login    |
| GET    | /auth/me       |

### Resume APIs

| Method | Endpoint                  |
| ------ | ------------------------- |
| POST   | /resumes/upload           |
| GET    | /resumes                  |
| GET    | /resumes/{resume_id}      |
| GET    | /resumes/{resume_id}/text |

### Job APIs

| Method | Endpoint       |
| ------ | -------------- |
| POST   | /jobs          |
| GET    | /jobs          |
| GET    | /jobs/{job_id} |
| DELETE | /jobs/{job_id} |

### Analysis APIs

| Method | Endpoint        |
| ------ | --------------- |
| POST   | /analysis/match |

### Embedding APIs

| Method | Endpoint           |
| ------ | ------------------ |
| POST   | /embeddings/index  |
| POST   | /embeddings/search |

---

## Current Progress

### Completed

* Authentication System
* Resume Upload System
* Resume Text Extraction
* Job Description Management
* AI Resume Matching
* Gemini Integration
* Embedding Generation
* Qdrant Integration
* Semantic Search

### Next Steps

* RAG Career Assistant
* Resume Q&A Chatbot
* AI Resume Rewriter
* Interview Preparation Assistant
* Vector-based Job Recommendations
* Frontend Integration
* Docker Compose Setup
* CI/CD Pipeline

---

## Learning Goals

This project is helping me gain hands-on experience with:

* FastAPI Development
* REST API Design
* PostgreSQL
* SQLAlchemy ORM
* JWT Authentication
* Generative AI
* LLM APIs
* Vector Embeddings
* Qdrant Vector Database
* Retrieval-Augmented Generation (RAG)
* Production Backend Development

---

## Author

Karan Raj Singh

Computer Science Engineering Graduate

Currently building Backend + GenAI projects and preparing for SDE-1 / AI Engineer roles.
