from app.core.config import Settings


def test_keys_meant_for_other_tools_are_ignored():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+psycopg2://user:secret@db:5432/app",
        JWT_SECRET_KEY="test",
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="secret",
        POSTGRES_DB="app",
    )

    assert settings.DATABASE_URL.endswith("@db:5432/app")
    assert not hasattr(settings, "POSTGRES_PASSWORD")


def test_test_database_is_optional():
    settings = Settings(_env_file=None, DATABASE_URL="postgresql+psycopg2://u:p@db/app", JWT_SECRET_KEY="test")

    assert settings.TEST_DATABASE_URL is None
