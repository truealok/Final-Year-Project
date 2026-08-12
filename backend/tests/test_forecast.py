"""Forecast endpoint tests (mock engine)."""


async def test_predict_creates_forecast(client, auth_headers, seeded_refs):
    response = await client.post(
        "/api/v1/forecast/predict",
        json={
            "product_id": seeded_refs["product_id"],
            "warehouse_id": seeded_refs["warehouse_id"],
            "start_date": "2026-09-01",
            "end_date": "2026-09-14",
            "model": "prophet",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["model_used"] == "prophet"
    assert len(body["points"]) == 14
    first = body["points"][0]
    assert first["lower_bound"] <= first["predicted_demand"] <= first["upper_bound"]
    # Core metrics always present; the engine adds provenance keys
    # ("engine": "ml"|"mock", "simulated" for mock runs, model metadata).
    assert {"mape", "rmse", "mae"} <= set(body["metrics"])
    assert body["metrics"]["engine"] in ("ml", "mock")

    # The run is persisted to history.
    history = await client.get("/api/v1/forecast/history", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["product"]["sku"] == "SKU-TEST-1"


async def test_predict_unknown_product_404(client, auth_headers, seeded_refs):
    response = await client.post(
        "/api/v1/forecast/predict",
        json={
            "product_id": "00000000-0000-0000-0000-000000000000",
            "warehouse_id": seeded_refs["warehouse_id"],
            "start_date": "2026-09-01",
            "end_date": "2026-09-07",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_predict_invalid_range_422(client, auth_headers, seeded_refs):
    response = await client.post(
        "/api/v1/forecast/predict",
        json={
            "product_id": seeded_refs["product_id"],
            "warehouse_id": seeded_refs["warehouse_id"],
            "start_date": "2026-09-14",
            "end_date": "2026-09-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_forecast_models_listed(client, auth_headers):
    response = await client.get("/api/v1/forecast/models", headers=auth_headers)
    assert response.status_code == 200
    names = {m["name"] for m in response.json()}
    assert names == {"prophet", "xgboost", "lstm"}
