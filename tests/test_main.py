import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def client():
    test_engine = create_async_engine(TEST_DATABASE_URL)
    TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await test_engine.dispose()


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_shorten_valid_url(client):
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["code"]) == 6
    assert data["short_url"].endswith(data["code"])
    assert data["original_url"] == "https://example.com/"


async def test_shorten_invalid_url(client):
    resp = await client.post("/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 422


async def test_redirect(client):
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["code"]
    resp2 = await client.get(f"/{code}", follow_redirects=False)
    assert resp2.status_code == 302
    assert "example.com" in resp2.headers["location"]


async def test_redirect_not_found(client):
    resp = await client.get("/notfound", follow_redirects=False)
    assert resp.status_code == 404


async def test_stats(client):
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["code"]
    resp2 = await client.get(f"/stats/{code}")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["code"] == code
    assert data["click_count"] == 0


async def test_click_count_increments(client):
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["code"]
    await client.get(f"/{code}", follow_redirects=False)
    await client.get(f"/{code}", follow_redirects=False)
    resp2 = await client.get(f"/stats/{code}")
    assert resp2.json()["click_count"] == 2


async def test_shorten_with_ttl(client):
    resp = await client.post("/shorten", json={"url": "https://example.com", "ttl_days": 7})
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None


async def test_stats_not_found(client):
    resp = await client.get("/stats/xxxxxx")
    assert resp.status_code == 404


async def test_shorten_missing_body(client):
    resp = await client.post("/shorten", json={})
    assert resp.status_code == 422
