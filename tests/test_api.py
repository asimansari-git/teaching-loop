from fastapi.testclient import TestClient
from backend.main import app
from backend import models

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Teaching Platform API"}

def test_register_teacher():
    response = client.post(
        "/auth/register",
        json={"username": "testteacher", "password": "password123", "role": "teacher", "new_organization_name": "TestOrg"},
    )
    assert response.status_code in [200, 400]

def test_login_teacher():
    response = client.post(
        "/auth/token",
        data={"username": "testteacher", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return token

def test_register_student():
    org_res = client.get("/auth/organizations")
    org_id = org_res.json()[0]["id"] if org_res.json() else 1
    response = client.post(
        "/auth/register",
        json={"username": "teststudent", "password": "password123", "role": "student", "organization_id": org_id},
    )
    # 200 if new, 400 if exists (re-run support)
    assert response.status_code in [200, 400] 

def test_login_student():
    response = client.post(
        "/auth/token",
        data={"username": "teststudent", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_get_students_as_teacher():
    token = test_login_teacher()
    response = client.get(
        "/reports/students",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
