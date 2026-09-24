from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Resume Analyzer"
    DEBUG: bool = True

    DATABASE_URL: str
    TEST_DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    MAX_ANALYSIS_TEXT_CHARACTERS: int = 24_000

    EMBEDDING_CHUNK_SIZE_WORDS: int = 300
    EMBEDDING_CHUNK_OVERLAP_WORDS: int = 50
    MAX_EMBEDDING_CHUNKS: int = 50

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "resume_embeddings"

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