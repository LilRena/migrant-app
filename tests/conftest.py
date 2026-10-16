import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import get_upload_dir
from app.db import Base, get_db
from app.main import app as fastapi_app

import app.models.user   # noqa: F401
import app.models.profile  # noqa: F401
import app.models.steps  # noqa: F401

_test_url = os.environ.get("TEST_DATABASE_URL", "")
_main_url = os.environ.get("DATABASE_URL", "")

if not _test_url:
    print(
        "ERROR: TEST_DATABASE_URL is not set. Set it in .env before running tests.",
        file=sys.stderr,
    )
    sys.exit(1)

if _test_url == _main_url:
    print(
        "ERROR: TEST_DATABASE_URL must differ from DATABASE_URL. "
        "Tests must not run on the main database.",
        file=sys.stderr,
    )
    sys.exit(1)

test_engine = create_engine(_test_url)
TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture()
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSession(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db, tmp_path):
    test_upload_dir = tmp_path / "uploads"
    test_upload_dir.mkdir()

    def override_get_db():
        yield db

    def override_upload_dir():
        return test_upload_dir

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_upload_dir] = override_upload_dir
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
