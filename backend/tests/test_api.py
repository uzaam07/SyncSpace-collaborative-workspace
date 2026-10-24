import os, tempfile
_fd, _path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_path}"
os.environ["SECRET_KEY"] = "test-secret-key-for-syncspace-tests"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

Base.metadata.create_all(bind=engine)
client = TestClient(app)

def register(email, name="Tester", password="Passw0rd!123"):
    return client.post("/api/v1/auth/register", json={"email": email, "display_name": name, "password": password})

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_register_login_me():
    response = register("one@example.com")
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "Passw0rd!123"})
    assert login.status_code == 200

def test_workspace_project_task_flow_and_isolation():
    r1, r2 = register("owner@example.com", "Owner"), register("outsider@example.com", "Outsider")
    token1, token2 = r1.json()["access_token"], r2.json()["access_token"]
    workspace = client.post("/api/v1/workspaces", headers=auth(token1), json={"name": "Engineering"})
    assert workspace.status_code == 201, workspace.text
    wid = workspace.json()["id"]
    project = client.post(f"/api/v1/workspaces/{wid}/projects", headers=auth(token1), json={"name": "Launch", "description": "Ship SyncSpace"})
    assert project.status_code == 201, project.text
    pid = project.json()["id"]
    task = client.post(f"/api/v1/projects/{pid}/tasks", headers=auth(token1), json={"title": "Build API", "description": "Implement endpoints"})
    assert task.status_code == 201, task.text
    tid = task.json()["id"]
    assert client.get(f"/api/v1/projects/{pid}/tasks", headers=auth(token2)).status_code == 404
    update = client.patch(f"/api/v1/tasks/{tid}", headers=auth(token1), json={"status": "done", "version": 1})
    assert update.status_code == 200, update.text
    assert update.json()["version"] == 2
    stale = client.patch(f"/api/v1/tasks/{tid}", headers=auth(token1), json={"status": "todo", "version": 1})
    assert stale.status_code == 409

def test_invalid_login():
    response = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert response.status_code == 401
