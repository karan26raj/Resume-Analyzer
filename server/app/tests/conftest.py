import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from app.core.config import settings

# Tests must never reach real external services: use an in-memory Qdrant,
# skip background indexing and make any accidental Gemini call fail fast.
settings.QDRANT_LOCATION = ":memory:"
settings.AUTO_INDEX_DOCUMENTS = False
settings.GEMINI_API_KEY = None

from app.ai.gemini import get_gemini_client  # noqa: E402
from app.ai.qdrant_client import ensure_collection, get_qdrant_client  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

get_qdrant_client.cache_clear()
get_gemini_client.cache_clear()

TEST_DATABASE_URL = settings.TEST_DATABASE_URL

engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def qdrant():
    """A fresh in-memory Qdrant collection for each test."""
    get_qdrant_client.cache_clear()
    ensure_collection()

    yield get_qdrant_client()

    get_qdrant_client.cache_clear()


@pytest.fixture
def db_session():

    connection = engine.connect()
    transaction = connection.begin()

    db = TestingSessionLocal(bind=connection)

    yield db

    db.close()

    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session, qdrant):

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
