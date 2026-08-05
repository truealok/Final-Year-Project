"""Simulation endpoint tests (mock engine)."""


async def test_run_simulation(client, auth_headers):
    response = await client.post(
        "/api/v1/simulation/run",
        json={
            "simulation_type": "supplier_failure",
            "severity": "high",
            "duration_days": 14,
            "probability": 0.7,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert 0 <= body["resilience_score"] <= 100
    assert body["expected_cost"] > 0
    assert 0 <= body["stockout_probability"] <= 1
    assert body["risk_level"] in {"low", "medium", "high", "critical"}
    assert body["affected_nodes"]
    assert body["affected_routes"]


async def test_simulation_history_persists(client, auth_headers):
    await client.post(
        "/api/v1/simulation/run",
        json={"simulation_type": "flood", "severity": "medium"},
        headers=auth_headers,
    )
    response = await client.get(
        "/api/v1/simulation/history", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["simulation_type"] == "flood"


async def test_simulation_types_list(client, auth_headers):
    response = await client.get("/api/v1/simulation/types", headers=auth_headers)
    assert response.status_code == 200
    assert "supplier_failure" in response.json()
    assert len(response.json()) == 6


async def test_invalid_simulation_type_422(client, auth_headers):
    response = await client.post(
        "/api/v1/simulation/run",
        json={"simulation_type": "alien_invasion"},
        headers=auth_headers,
    )
    assert response.status_code == 422
