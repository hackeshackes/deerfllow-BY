"""Verify rate limiting middleware is registered and functional."""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_rate_limit_middleware_registered():
    from app.gateway.app import app

    # Middleware classes are accessible via app.user_middleware
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert any("RateLimit" in name for name in middleware_classes), (
        f"RateLimitMiddleware not found in middleware stack. Got: {middleware_classes}"
    )


def test_rate_limit_returns_429_after_burst():
    from app.gateway.rate_limit import RateLimitMiddleware

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    response = client.get("/ping")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
