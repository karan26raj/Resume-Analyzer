from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.qdrant_client import ensure_collection
from app.api.analysis import router as analysis_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.embeddings import router as embeddings_router
from app.api.interview import router as interview_router
from app.api.jobs import router as jobs_router
from app.api.recommendations import router as recommendations_router
from app.api.resumes import router as resumes_router
from app.api.rewrite import router as rewrite_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import redis_status
from app.worker.health import worker_status


configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_collection()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

register_exception_handlers(app)

# Added before CORS so CORS wraps it: error responses (including 500s) still carry CORS headers,
# letting the browser read the error and its request ID.
app.add_middleware(RequestContextMiddleware)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )


app.include_router(auth_router)
app.include_router(resumes_router)
app.include_router(rewrite_router)
app.include_router(jobs_router)
app.include_router(analysis_router)
app.include_router(recommendations_router)
app.include_router(embeddings_router)
app.include_router(assistant_router)
app.include_router(interview_router)


@app.get("/")
def root():
    return {
        "message": "AI Resume Analyzer API"
    }


@app.get("/health")
def health_check():
    redis_state = redis_status()
    return {
        "status": "healthy",
        "redis": redis_state,
        "worker": worker_status(redis_state),
    }
