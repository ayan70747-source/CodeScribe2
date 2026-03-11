import importlib
import os
import re
import sys

import pytest
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def app_module():
    os.environ["GEMINI_API_KEY"] = "test-key"
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
    os.environ["APP_ADMIN_USERNAME"] = "admin"
    os.environ["APP_ADMIN_PASSWORD_HASH"] = generate_password_hash("admin-password")
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:8080"

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True
    module.app.config["WTF_CSRF_ENABLED"] = False
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def extract_csrf_token(html_text: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    assert match, "Expected CSRF token in form"
    return match.group(1)


def login(client):
    get_response = client.get("/login")
    token = extract_csrf_token(get_response.get_data(as_text=True))
    return client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin-password",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.get_json()["ready"] is True


def test_analyze_requires_authentication(client):
    response = client.post("/analyze-all", json={"code": "print('hi')"})
    assert response.status_code == 401


def test_login_success(client):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_live_metrics_with_auth(client):
    login_response = login(client)
    assert login_response.status_code == 302

    response = client.post("/live-metrics", json={"code": "def add(a, b):\n    return a + b"})
    assert response.status_code == 200
    data = response.get_json()
    assert "loc" in data
    assert "maintainability_index" in data


def test_analyze_returns_400_for_missing_code(client):
    login_response = login(client)
    assert login_response.status_code == 302

    response = client.post("/analyze-all", json={"code": ""})
    assert response.status_code == 400
    assert response.get_json()["error"] == "No code provided"
