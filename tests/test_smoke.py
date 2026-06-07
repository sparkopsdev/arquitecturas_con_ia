from __future__ import annotations

from fastapi.testclient import TestClient

from pares_ai.main import app, db, settings
from pares_ai.ingestion import seed_samples


client = TestClient(app)


def auth(role: str = "admin") -> dict[str, str]:
    response = client.post("/api/auth/demo-login", json={"role": role})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_and_query():
    db.init_schema()
    seed_samples(db, settings.data_dir / "samples")
    response = client.post(
        "/api/query",
        headers=auth("admin"),
        json={"question": "Que naves participaron en San Miguel?", "output_format": "text"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "San" in payload["answer"] or payload["sources"]
