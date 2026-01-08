import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, get_db, User
from main import app
from services.auth_service import get_password_hash
from config import settings

# Test database (SQLite in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override database dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database"""
    Base.metadata.create_all(bind=engine)

    # Security knobs for tests
    settings.DEVICE_REGISTRATION_MODE = "token"
    settings.DEVICE_REGISTRATION_REQUIRE_TOKEN = True
    settings.DEVICE_REGISTRATION_TOKEN = secrets.token_hex(32)
    settings.DEVICE_HEARTBEAT_REQUIRE_TOKEN = True

    # Seed default admin user for auth tests
    db = TestingSessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            db.add(User(username="admin", password_hash=get_password_hash("admin123"), role="admin"))
            db.commit()
    finally:
        db.close()

    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Direct DB session fixture for tests that need DB access."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def authenticated_client(client):
    """Create authenticated test client"""
    # Login with default admin user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    tokens = response.json()
    
    # Set auth header
    client.headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    client.refresh_token = tokens["refresh_token"]
    
    return client
