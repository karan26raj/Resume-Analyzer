# AI Resume Analyzer API

A FastAPI backend for uploading PDF and DOCX resumes. It extracts text, stores files locally, and saves metadata in PostgreSQL.

## Current features

- User registration and JWT login
- PDF and DOCX uploads
- File validation and text extraction
- PostgreSQL metadata storage
- Per-user resume access

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the `server` directory. Do not commit it.

```env
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/resume_analyzer
TEST_DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/resume_analyzer_test
JWT_SECRET_KEY=replace_with_a_long_random_secret
DEBUG=true
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_BYTES=10485760
```

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Resume upload flow

```text
User
  ->
Upload PDF or DOCX
  ->
Validate filename, extension, size, and file contents
  ->
Extract text
  ->
Store the validated file with a generated filename
  ->
Store metadata and extracted text in PostgreSQL
  ->
Return the resume ID
```

## API routes

| Method | Route | Authentication | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | No | Create a user account |
| POST | `/auth/login` | No | Obtain a bearer token |
| GET | `/auth/me` | Yes | Get the authenticated user |
| GET | `/resumes/` | Yes | List the user's resumes |
| POST | `/resumes/upload` | Yes | Upload and process a resume |
| GET | `/resumes/{resume_id}/text` | Yes | Get extracted resume text |

## Tests

```powershell
python -m pytest
```

Use a separate test database for `TEST_DATABASE_URL`.
