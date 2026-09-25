def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "redis": "connected",
        "worker": "disabled",
    }

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "pytest_new@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "pytest_new@example.com"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data

def test_duplicate_email(client):

    email = "duplicate@example.com"

    first_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123"
        }
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123"
        }
    )

    assert second_response.status_code == 409

def test_login(client):

    email = "login@example.com"
    password = "password123"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password
        }
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):

    email = "wrong-password@example.com"

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401

def test_get_current_user(client):

    email = "current-user@example.com"
    password = "password123"

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password
        }
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200
    assert response.json()["email"] == email

def test_get_current_user_without_token(client):

    response = client.get("/auth/me")

    assert response.status_code == 401 

def test_protected_resumes_without_token(client):
    response = client.get("/resumes/")

    assert response.status_code == 401


def test_protected_jobs_without_token(client):
    response = client.get("/jobs/")

    assert response.status_code == 401


def test_protected_analysis_without_token(client):
    response = client.get("/analysis/")

    assert response.status_code == 401


def test_protected_recommendations_without_token(client):
    response = client.get("/recommendations/")

    assert response.status_code == 401
