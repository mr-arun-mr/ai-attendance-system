"""
Integration test fixtures.

Architecture
------------
* test_engine  (session-scoped) – creates all tables once; drops them at the end.
* client       (session-scoped) – single HTTPX AsyncClient for the whole suite.
                                   get_db is overridden to use test_engine.
* clean_tables (function-scoped, autouse) – truncates every table after each test
                                             so tests are fully isolated.
* admin_user / admin_headers / regular_user / user_headers – recreated per test
  (they need the database to be clean, so they must be function-scoped).
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://attendance:attendance_secret@localhost:5432/attendance_test",
)


# ── Engine & schema ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    from app.core.database import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── HTTP client (session-scoped, lifespan skipped) ────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def client(test_engine):
    from app.main import app
    from app.core.database import get_db

    async def _override_get_db():
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    # Use lifespan=False so the app engine is never disposed mid-suite
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


# ── Table cleanup between tests ───────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_engine):
    yield
    from app.core.database import Base

    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(test_engine):
    from app.models.user import User
    from app.core.security import hash_password

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        user = User(
            email="admin@test.local",
            full_name="Test Admin",
            employee_id="ADMIN001",
            hashed_password=hash_password("testpass123"),
            is_admin=True,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def admin_headers(admin_user):
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def regular_user(test_engine):
    from app.models.user import User
    from app.core.security import hash_password

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        user = User(
            email="user@test.local",
            full_name="Regular User",
            employee_id="USER001",
            hashed_password=hash_password("testpass123"),
            is_admin=False,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def user_headers(regular_user):
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(regular_user.id)})
    return {"Authorization": f"Bearer {token}"}
