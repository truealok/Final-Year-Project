"""Health and root endpoint tests."""


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root_metadata(client):
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ResiliChain AI"
    assert body["docs"] == "/docs"


async def test_timing_header_present(client):
    response = await client.get("/health")
    assert "X-Process-Time-Ms" in response.headers
