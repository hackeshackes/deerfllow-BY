"""End-to-end smoke: admin role can read, guest cannot."""
from fastapi.testclient import TestClient
from app.gateway.app import create_app
from app.gateway.identity.rbac.decorators import require_permission
from fastapi import FastAPI, Depends

# Build a tiny app to verify decorator+enforcer integration
app = FastAPI()


@app.get("/admin-only")
@require_permission(obj="config/*", act="read")
def admin_endpoint(user_roles: list[str] = Depends(lambda: ["role:guest"])):
    return {"ok": True}


def test_guest_blocked():
    c = TestClient(app)
    assert c.get("/admin-only").status_code == 403


# Same handler with admin role
app_admin = FastAPI()


@app_admin.get("/admin-only")
@require_permission(obj="config/*", act="read")
def admin_endpoint(user_roles: list[str] = Depends(lambda: ["role:admin"])):
    return {"ok": True}


def test_admin_allowed():
    c = TestClient(app_admin)
    assert c.get("/admin-only").status_code == 200
