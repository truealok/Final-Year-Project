"""Dashboard, digital twin, analytics and recommendations smoke tests."""


async def test_dashboard_shape(client, auth_headers):
    response = await client.get("/api/v1/dashboard", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    for key in (
        "forecast_accuracy",
        "resilience_score",
        "expected_cost",
        "current_inventory",
        "stockout_probability",
        "recovery_time_days",
        "carbon_emissions",
        "latest_alerts",
        "recent_simulations",
    ):
        assert key in body, f"missing dashboard key: {key}"
    assert 0 <= body["forecast_accuracy"] <= 100


async def test_digital_twin_network(client, auth_headers, seeded_refs):
    response = await client.get(
        "/api/v1/digital-twin/network", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    # The seeded warehouse appears as a node.
    types = {node["type"] for node in body["nodes"]}
    assert "warehouse" in types
    assert body["summary"]["total_nodes"] == len(body["nodes"])


async def test_analytics_shape(client, auth_headers):
    response = await client.get("/api/v1/analytics", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["demand_trend"]) == 12  # mock series when no sales exist
    assert "warehouse_utilization" in body


async def test_recommendations_generate_and_update(client, auth_headers):
    generated = await client.post(
        "/api/v1/recommendations/generate", headers=auth_headers
    )
    assert generated.status_code == 201
    recs = generated.json()
    assert len(recs) == 3

    rec_id = recs[0]["id"]
    updated = await client.patch(
        f"/api/v1/recommendations/{rec_id}",
        json={"status": "applied"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "applied"


async def test_reports_generate_and_export_csv(client, auth_headers):
    generated = await client.post(
        "/api/v1/reports/generate",
        json={"report_type": "risk", "format": "json"},
        headers=auth_headers,
    )
    assert generated.status_code == 201
    report_id = generated.json()["id"]
    assert "columns" in generated.json()["content"]

    exported = await client.get(
        f"/api/v1/reports/{report_id}/export",
        params={"export_format": "csv"},
        headers=auth_headers,
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "Supplier" in exported.text


async def test_alerts_create_and_summary(client, auth_headers):
    created = await client.post(
        "/api/v1/alerts",
        json={
            "title": "Test alert",
            "message": "Something needs attention",
            "severity": "critical",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201

    summary = await client.get("/api/v1/alerts/summary", headers=auth_headers)
    assert summary.status_code == 200
    assert summary.json()["critical"] == 1
    assert summary.json()["unread"] == 1
