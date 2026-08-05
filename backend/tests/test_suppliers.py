"""Supplier CRUD tests."""

SUPPLIER = {
    "name": "Hamburg Components",
    "country": "Germany",
    "city": "Hamburg",
    "reliability_score": 92.5,
    "lead_time_days": 12,
    "risk_level": "low",
}


async def test_supplier_crud_cycle(client, auth_headers):
    # Create
    created = await client.post(
        "/api/v1/suppliers", json=SUPPLIER, headers=auth_headers
    )
    assert created.status_code == 201, created.text
    supplier_id = created.json()["id"]
    assert created.json()["name"] == SUPPLIER["name"]

    # List
    listed = await client.get("/api/v1/suppliers", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    # Get
    fetched = await client.get(
        f"/api/v1/suppliers/{supplier_id}", headers=auth_headers
    )
    assert fetched.status_code == 200
    assert fetched.json()["reliability_score"] == 92.5

    # Update
    updated = await client.put(
        f"/api/v1/suppliers/{supplier_id}",
        json={"reliability_score": 71.0, "risk_level": "high"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["risk_level"] == "high"

    # Delete
    deleted = await client.delete(
        f"/api/v1/suppliers/{supplier_id}", headers=auth_headers
    )
    assert deleted.status_code == 204

    # Gone
    missing = await client.get(
        f"/api/v1/suppliers/{supplier_id}", headers=auth_headers
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


async def test_supplier_create_requires_auth(client):
    response = await client.post("/api/v1/suppliers", json=SUPPLIER)
    assert response.status_code == 401


async def test_supplier_search_filter(client, auth_headers):
    await client.post("/api/v1/suppliers", json=SUPPLIER, headers=auth_headers)
    await client.post(
        "/api/v1/suppliers",
        json={**SUPPLIER, "name": "Osaka Materials", "country": "Japan"},
        headers=auth_headers,
    )
    response = await client.get(
        "/api/v1/suppliers", params={"search": "osaka"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Osaka Materials"


async def test_analyst_cannot_create_supplier(client, auth_headers):
    # First user (admin) exists via auth_headers; create an analyst.
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "analyst@test.com",
            "password": "Password123!",
            "full_name": "Analyst",
        },
    )
    analyst_token = signup.json()["tokens"]["access_token"]
    response = await client.post(
        "/api/v1/suppliers",
        json=SUPPLIER,
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
