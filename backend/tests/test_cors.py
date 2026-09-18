from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


def test_cors_requires_explicit_origins():
    assert Settings(cors_allow_origins="https://app.example.com, http://localhost:3000").cors_origins == ["https://app.example.com", "http://localhost:3000"]


def test_cors_preflight_allows_configured_origin_only():
    client = TestClient(app)
    response = client.options("/documents", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_privacy_export_is_exposed_in_openapi():
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/privacy/export" in paths
    assert "get" in paths["/privacy/export"]
