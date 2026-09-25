import fakeredis
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from app.core.config import settings

settings.QDRANT_LOCATION = ":memory:"
settings.AUTO_INDEX_DOCUMENTS = False
settings.GEMINI_API_KEY = None
settings.TASK_QUEUE_ENABLED = False

from app.ai.gemini import get_gemini_client
from app.ai.qdrant_client import ensure_collection, get_qdrant_client
from app.core.database import Base, get_db
from app.core.redis import set_redis_client
from app.main import app
from app.services import indexing as indexing_service
from app.worker.celery_app import celery_app

get_qdrant_client.cache_clear()
get_gemini_client.cache_clear()

TEST_DATABASE_URL = settings.TEST_DATABASE_URL
assert TEST_DATABASE_URL, "Set TEST_DATABASE_URL (a separate database) to run the tests"

engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

indexing_service.SessionLocal = TestingSessionLocal
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    set_redis_client(client)

    yield client

    set_redis_client(None)


@pytest.fixture
def qdrant():
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
def worker_sessions(db_session, monkeypatch):
    connection = db_session.get_bind()
    monkeypatch.setattr(indexing_service, "SessionLocal", lambda: TestingSessionLocal(bind=connection))


@pytest.fixture
def client(db_session, qdrant):

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
