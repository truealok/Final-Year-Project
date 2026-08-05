"""Test fixtures - in-memory SQLite database and an ASGI test client."""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Category, Product, Warehouse


@pytest_asyncio.fixture
async def db_engine():
    """Fresh in-memory SQLite database per test."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory):
    """HTTP client wired to the test database via dependency override."""

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register the first user (becomes admin) and return auth headers."""
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "admin@test.com",
            "password": "Password123!",
            "full_name": "Test Admin",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seeded_refs(session_factory):
    """Insert a category, product and warehouse; return their ids."""
    async with session_factory() as session:
        category = Category(name="Electronics", description="Test category")
        session.add(category)
        await session.flush()

        product = Product(
            sku="SKU-TEST-1",
            name="Test Sensor Array",
            category_id=category.id,
            unit_cost=25.0,
            unit_price=40.0,
        )
        warehouse = Warehouse(
            name="Test DC", country="Germany", city="Berlin", capacity=50_000
        )
        session.add_all([product, warehouse])
        await session.commit()
        return {
            "product_id": str(product.id),
            "warehouse_id": str(warehouse.id),
            "category_id": str(category.id),
        }


@pytest_asyncio.fixture
def unique_email():
    return f"user-{uuid.uuid4().hex[:8]}@test.com"
