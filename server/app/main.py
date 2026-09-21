from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.resumes import router as resumes_router
from app.api.jobs import router as jobs_router
from app.api.analysis import router as analysis_router
from app.api.recommendations import router as recommendations_router

app = FastAPI(
    title="AI Resume Analyzer"
)


app.include_router(auth_router)
app.include_router(resumes_router)
app.include_router(jobs_router)
app.include_router(analysis_router)
app.include_router(recommendations_router)


@app.get("/")
def root():
    return {
        "message": "AI Resume Analyzer API"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }