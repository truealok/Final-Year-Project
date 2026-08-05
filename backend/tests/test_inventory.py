"""Inventory CRUD tests."""


async def make_inventory(client, auth_headers, seeded_refs, quantity=500):
    return await client.post(
        "/api/v1/inventory",
        json={
            "product_id": seeded_refs["product_id"],
            "warehouse_id": seeded_refs["warehouse_id"],
            "quantity": quantity,
            "reorder_point": 100,
            "safety_stock": 50,
            "unit_cost": 25.0,
        },
        headers=auth_headers,
    )


async def test_inventory_crud_and_status_derivation(
    client, auth_headers, seeded_refs
):
    created = await make_inventory(client, auth_headers, seeded_refs)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "in_stock"
    assert body["total_value"] == 500 * 25.0
    inventory_id = body["id"]

    # Dropping quantity below the reorder point flips status to low_stock.
    updated = await client.put(
        f"/api/v1/inventory/{inventory_id}",
        json={"quantity": 80},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "low_stock"

    # Zero quantity -> out_of_stock.
    updated = await client.put(
        f"/api/v1/inventory/{inventory_id}",
        json={"quantity": 0},
        headers=auth_headers,
    )
    assert updated.json()["status"] == "out_of_stock"

    deleted = await client.delete(
        f"/api/v1/inventory/{inventory_id}", headers=auth_headers
    )
    assert deleted.status_code == 204


async def test_duplicate_inventory_conflicts(client, auth_headers, seeded_refs):
    first = await make_inventory(client, auth_headers, seeded_refs)
    assert first.status_code == 201
    second = await make_inventory(client, auth_headers, seeded_refs)
    assert second.status_code == 409


async def test_inventory_summary(client, auth_headers, seeded_refs):
    await make_inventory(client, auth_headers, seeded_refs)
    response = await client.get("/api/v1/inventory/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    assert body["total_units"] == 500
    assert body["total_value"] == 12_500.0


async def test_products_reference_endpoint(client, auth_headers, seeded_refs):
    response = await client.get("/api/v1/inventory/products", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["sku"] == "SKU-TEST-1"
