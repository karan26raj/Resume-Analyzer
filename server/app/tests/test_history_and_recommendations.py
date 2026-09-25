from app.tests.helpers import (
    create_analysis,
    create_job,
    create_resume,
    create_user_and_headers,
)


def test_list_and_get_analyses_for_current_user_only(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    job_a = create_job(db_session, user, title="A")
    job_b = create_job(db_session, user, title="B")
    first = create_analysis(db_session, user, resume, job_a, match_score=60)
    second = create_analysis(db_session, user, resume, job_b, match_score=80)

    other_user, other_headers = create_user_and_headers(client, db_session)
    other_resume = create_resume(db_session, other_user)
    other_job = create_job(db_session, other_user)
    create_analysis(db_session, other_user, other_resume, other_job)

    response = client.get("/analysis", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second.id, first.id]

    filtered = client.get(f"/analysis?job_id={job_a.id}", headers=headers)
    assert [item["id"] for item in filtered.json()] == [first.id]

    detail = client.get(f"/analysis/{first.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["match_score"] == 60

    assert client.get(f"/analysis/{first.id}", headers=other_headers).status_code == 404


def test_recommendations_aggregate_skill_gaps(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    job_a = create_job(db_session, user, title="A")
    job_b = create_job(db_session, user, title="B")
    create_analysis(
        db_session, user, resume, job_a,
        match_score=60,
        missing_skills=["docker", "AWS", "AWS"],
        recommendations=["Learn Docker"],
    )
    create_analysis(
        db_session, user, resume, job_b,
        match_score=81,
        missing_skills=["Docker", "Kubernetes"],
        recommendations=["Add AWS projects", "learn docker"],
    )

    response = client.get("/recommendations", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_count"] == 2
    assert data["average_match_score"] == 70.5
    assert data["top_missing_skills"][0] == {"skill": "Docker", "count": 2}
    assert {"skill": "AWS", "count": 1} in data["top_missing_skills"]
    assert {"skill": "Kubernetes", "count": 1} in data["top_missing_skills"]
    assert data["recommendations"] == ["Add AWS projects", "learn docker"]


def test_recommendations_without_analyses(client, db_session):
    _, headers = create_user_and_headers(client, db_session)

    response = client.get("/recommendations", headers=headers)

    assert response.json() == {
        "analysis_count": 0,
        "average_match_score": None,
        "top_missing_skills": [],
        "recommendations": [],
    }
