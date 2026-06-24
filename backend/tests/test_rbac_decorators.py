import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.gateway.identity.rbac.decorators import require_permission

app = FastAPI()


@app.get("/admin/test")
@require_permission(obj="config/*", act="read")
def admin_test(user_roles: list[str] = Depends(lambda: ["role:admin"])):
    return {"ok": True}


client = TestClient(app)


def test_admin_can_access():
    resp = client.get("/admin/test")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_member_cannot_access():
    app2 = FastAPI()

    @app2.get("/admin/test")
    @require_permission(obj="config/*", act="read")
    def view(user_roles: list[str] = Depends(lambda: ["role:member"])):
        return {"ok": True}

    c2 = TestClient(app2)
    resp = c2.get("/admin/test")
    assert resp.status_code == 403
