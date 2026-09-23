import uuid


def _auth_headers(client) -> dict[str, str]:
    email = f"job-user-{uuid.uuid4()}@example.com"
    password = "password123"
    register_response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login_response.status_code == 200
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def _job_payload(title: str = "Backend Developer") -> dict[str, str]:
    return {
        "title": title,
        "company": "Example",
        "description": "Looking for a Python backend developer.",
    }


def test_create_job(client):
    response = client.post("/jobs", headers=_auth_headers(client), json=_job_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["title"] == "Backend Developer"
    assert data["company"] == "Example"
    assert data["description"] == "Looking for a Python backend developer."
    assert "created_at" in data


def test_list_jobs_returns_only_current_users_jobs(client):
    owner_headers = _auth_headers(client)
    other_headers = _auth_headers(client)
    client.post("/jobs", headers=owner_headers, json=_job_payload("Python Developer"))
    client.post("/jobs", headers=owner_headers, json=_job_payload("API Developer"))
    client.post("/jobs", headers=other_headers, json=_job_payload("Private Job"))

    response = client.get("/jobs", headers=owner_headers)

    assert response.status_code == 200
    assert [job["title"] for job in response.json()] == ["API Developer", "Python Developer"]


def test_get_job_and_prevent_access_by_another_user(client):
    owner_headers = _auth_headers(client)
    create_response = client.post("/jobs", headers=owner_headers, json=_job_payload())
    job_id = create_response.json()["id"]

    response = client.get(f"/jobs/{job_id}", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["id"] == job_id

    other_response = client.get(f"/jobs/{job_id}", headers=_auth_headers(client))
    assert other_response.status_code == 404
    assert other_response.json()["detail"] == "Job not found"


def test_delete_job(client):
    headers = _auth_headers(client)
    create_response = client.post("/jobs", headers=headers, json=_job_payload())
    job_id = create_response.json()["id"]

    delete_response = client.delete(f"/jobs/{job_id}", headers=headers)
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = client.get(f"/jobs/{job_id}", headers=headers)
    assert get_response.status_code == 404


def test_create_job_requires_all_fields(client):
    response = client.post(
        "/jobs",
        headers=_auth_headers(client),
        json={"title": "Backend Developer", "company": "Example"},
    )

    assert response.status_code == 422
