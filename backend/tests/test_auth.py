"""Authentication flow tests."""

SIGNUP = {
    "email": "first@test.com",
    "password": "Password123!",
    "full_name": "First User",
}


async def test_signup_first_user_is_admin(client):
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "admin"
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]


async def test_signup_second_user_is_analyst(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "second@test.com",
            "password": "Password123!",
            "full_name": "Second User",
        },
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "analyst"


async def test_signup_duplicate_email_conflicts(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_login_and_me(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SIGNUP["email"], "password": SIGNUP["password"]},
    )
    assert response.status_code == 200
    token = response.json()["tokens"]["access_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == SIGNUP["email"]


async def test_login_wrong_password_unauthorized(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SIGNUP["email"], "password": "WrongPass99!"},
    )
    assert response.status_code == 401


async def test_refresh_rotates_tokens(client):
    signup = await client.post("/api/v1/auth/signup", json=SIGNUP)
    refresh_token = signup.json()["tokens"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]

    # The old refresh token was rotated out and must now be rejected.
    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reuse.status_code == 401


async def test_logout_revokes_refresh(client):
    signup = await client.post("/api/v1/auth/signup", json=SIGNUP)
    tokens = signup.json()["tokens"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


async def test_forgot_and_reset_password(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    forgot = await client.post(
        "/api/v1/auth/forgot-password", json={"email": SIGNUP["email"]}
    )
    assert forgot.status_code == 200
    reset_token = forgot.json()["reset_token"]
    assert reset_token  # returned directly in development mode

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewPassword123!"},
    )
    assert reset.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": SIGNUP["email"], "password": "NewPassword123!"},
    )
    assert login.status_code == 200


async def test_protected_route_requires_token(client):
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 401
