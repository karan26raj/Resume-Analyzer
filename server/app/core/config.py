from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Resume Analyzer"
    DEBUG: bool = False

    DATABASE_URL: str
    TEST_DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # JSON list in .env, e.g. CORS_ORIGINS=["http://localhost:5173"]
    CORS_ORIGINS: list[str] = []

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    # Tried in order when GEMINI_MODEL is overloaded, rate limited or unavailable.
    # JSON list in .env, e.g. GEMINI_FALLBACK_MODELS=["gemini-3.6-flash","gemini-3.5-flash"]
    # Full-size models first; the lite models come last because they are the most consistently available.
    GEMINI_FALLBACK_MODELS: list[str] = [
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
    ]
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TIMEOUT_SECONDS: int = 60
    # Attempts per model before moving to the next fallback model.
    GEMINI_MAX_RETRIES: int = 2

    MAX_ANALYSIS_TEXT_CHARACTERS: int = 24_000

    # Phase 9: resume passages retrieved for each match analysis.
    ANALYSIS_EVIDENCE_CHUNKS: int = 5
    # Search queries are embedded with the Gemini API, which rejects over-long input.
    MAX_QUERY_EMBED_CHARACTERS: int = 6_000

    # Phase 10: weights of the explainable match score (redistributed when a component is unavailable).
    SCORE_WEIGHT_SKILLS: float = 0.40
    SCORE_WEIGHT_EXPERIENCE: float = 0.25
    SCORE_WEIGHT_EDUCATION: float = 0.10
    SCORE_WEIGHT_SEMANTIC: float = 0.25
    # Cosine similarity calibration: at or below FLOOR scores 0, at or above CEILING scores 100.
    SEMANTIC_SIMILARITY_FLOOR: float = 0.45
    SEMANTIC_SIMILARITY_CEILING: float = 0.85

    # Phase 11: job recommendations compare resume passages with job passages directly. Passage-to-passage
    # similarity runs higher than the query-to-passage similarity above, so it has its own calibration.
    RECOMMENDATION_SIMILARITY_FLOOR: float = 0.70
    RECOMMENDATION_SIMILARITY_CEILING: float = 0.85

    # Phase 12: resume rewriting.
    MAX_REWRITE_SUGGESTIONS: int = 8

    EMBEDDING_DIMENSIONS: int = 3072
    EMBEDDING_CHUNK_SIZE_WORDS: int = 300
    EMBEDDING_CHUNK_OVERLAP_WORDS: int = 50
    MAX_EMBEDDING_CHUNKS: int = 50
    # Embed and index resumes/jobs in the background as soon as they are created.
    AUTO_INDEX_DOCUMENTS: bool = True

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    # Overrides host/port when set, e.g. ":memory:" for tests.
    QDRANT_LOCATION: str | None = None
    QDRANT_COLLECTION_NAME: str = "resume_embeddings"

    # Phase 14: Redis for caching and rate limiting. Leave empty to disable both.
    # When Redis is configured but unreachable the API keeps working, just without cache and limits.
    REDIS_URL: str | None = "redis://localhost:6379/0"
    REDIS_TIMEOUT_SECONDS: float = 0.5
    # After a connection failure Redis is skipped for this long instead of slowing every request.
    REDIS_RETRY_AFTER_SECONDS: int = 30

    CACHE_TTL_ANALYSIS_SECONDS: int = 24 * 60 * 60
    CACHE_TTL_REWRITE_SECONDS: int = 24 * 60 * 60
    CACHE_TTL_RECOMMENDATIONS_SECONDS: int = 10 * 60

    # Fixed-window limits: at most LIMIT requests per WINDOW seconds.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: int = 10  # per client IP
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 5 * 60
    RATE_LIMIT_REGISTER: int = 5  # per client IP
    RATE_LIMIT_REGISTER_WINDOW_SECONDS: int = 60 * 60
    RATE_LIMIT_AI_GENERATE: int = 20  # per user: analysis, rewrite, assistant (Gemini text generation)
    RATE_LIMIT_AI_GENERATE_WINDOW_SECONDS: int = 10 * 60
    RATE_LIMIT_AI_EMBED: int = 60  # per user: semantic search and manual indexing (Gemini embeddings)
    RATE_LIMIT_AI_EMBED_WINDOW_SECONDS: int = 10 * 60

    # Phase 15: document indexing runs on a Celery worker (`celery -A app.worker.celery_app:celery_app worker`).
    # When disabled, or when the broker is unreachable, indexing runs in-process after the response instead.
    TASK_QUEUE_ENABLED: bool = True
    # A separate Redis database from the cache, so flushing the cache never drops queued work.
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    # Retries for transient failures (Gemini 429/503, Qdrant hiccups), with exponential backoff.
    INDEX_TASK_MAX_RETRIES: int = 3
    INDEX_TASK_RETRY_BASE_SECONDS: int = 10

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        if isinstance(value, str) and value.lower() in {
            "release",
            "production",
            "prod",
        }:
            return False
        return value

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()
