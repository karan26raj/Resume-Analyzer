from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Resume Analyzer"
    DEBUG: bool = False

    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CORS_ORIGINS: list[str] = []

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODELS: list[str] = [
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
    ]
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TIMEOUT_SECONDS: int = 60
    GEMINI_MAX_RETRIES: int = 2

    MAX_ANALYSIS_TEXT_CHARACTERS: int = 24_000

    ANALYSIS_EVIDENCE_CHUNKS: int = 5
    MAX_QUERY_EMBED_CHARACTERS: int = 6_000

    SCORE_WEIGHT_SKILLS: float = 0.40
    SCORE_WEIGHT_EXPERIENCE: float = 0.25
    SCORE_WEIGHT_EDUCATION: float = 0.10
    SCORE_WEIGHT_SEMANTIC: float = 0.25
    SEMANTIC_SIMILARITY_FLOOR: float = 0.45
    SEMANTIC_SIMILARITY_CEILING: float = 0.85

    RECOMMENDATION_SIMILARITY_FLOOR: float = 0.70
    RECOMMENDATION_SIMILARITY_CEILING: float = 0.85

    MAX_REWRITE_SUGGESTIONS: int = 8

    INTERVIEW_MIN_QUESTIONS: int = 4
    INTERVIEW_MAX_QUESTIONS: int = 5
    INTERVIEW_MAX_TECHNOLOGIES: int = 8

    EMBEDDING_DIMENSIONS: int = 3072
    EMBEDDING_CHUNK_SIZE_WORDS: int = 300
    EMBEDDING_CHUNK_OVERLAP_WORDS: int = 50
    MAX_EMBEDDING_CHUNKS: int = 50
    AUTO_INDEX_DOCUMENTS: bool = True

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_LOCATION: str | None = None
    QDRANT_COLLECTION_NAME: str = "resume_embeddings"

    REDIS_URL: str | None = "redis://localhost:6379/0"
    REDIS_TIMEOUT_SECONDS: float = 0.5
    REDIS_RETRY_AFTER_SECONDS: int = 30

    CACHE_TTL_ANALYSIS_SECONDS: int = 24 * 60 * 60
    CACHE_TTL_REWRITE_SECONDS: int = 24 * 60 * 60
    CACHE_TTL_RECOMMENDATIONS_SECONDS: int = 10 * 60

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: int = 10
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 5 * 60
    RATE_LIMIT_REGISTER: int = 5
    RATE_LIMIT_REGISTER_WINDOW_SECONDS: int = 60 * 60
    RATE_LIMIT_AI_GENERATE: int = 20
    RATE_LIMIT_AI_GENERATE_WINDOW_SECONDS: int = 10 * 60
    RATE_LIMIT_AI_EMBED: int = 60
    RATE_LIMIT_AI_EMBED_WINDOW_SECONDS: int = 10 * 60

    TASK_QUEUE_ENABLED: bool = True
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
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
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
