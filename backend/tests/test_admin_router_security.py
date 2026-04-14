from __future__ import annotations

from app.gateway.routers.mcp import McpOAuthConfigResponse, McpServerConfigResponse, _persist_secret_map, _sanitize_server_for_read
from app.gateway.routers.models import ModelMutationRequest, _model_to_response, _normalize_model_record
from deerflow.config.model_config import ModelConfig


def test_model_response_hides_sensitive_fields_for_non_admin(monkeypatch):
    model = ModelConfig(
        name="demo",
        display_name="Demo",
        description="desc",
        use="langchain_openai:ChatOpenAI",
        model="gpt-4",
        api_key="secret://models/demo/api_key",
        base_url="https://api.example.com",
    )

    response = _model_to_response(model, include_sensitive=False)

    assert response.api_key is None
    assert response.use is None
    assert response.base_url is None
    assert response.api_key_configured is True


def test_model_normalize_encrypts_plain_api_key(monkeypatch):
    monkeypatch.setattr("app.gateway.routers.models.upsert_secret", lambda key, value: f"secret://{key}")

    payload = ModelMutationRequest(name="demo", use="langchain_openai:ChatOpenAI", model="gpt-4", api_key="raw-secret")
    record = _normalize_model_record(payload)

    assert record["api_key"] == "secret://models/demo/api_key"


def test_mcp_sanitize_masks_sensitive_fields():
    server = McpServerConfigResponse(
        enabled=True,
        type="http",
        env={"TOKEN": "secret://mcp/github/env/TOKEN"},
        headers={"Authorization": "secret://mcp/github/headers/Authorization"},
        oauth=McpOAuthConfigResponse(client_secret="secret://mcp/github/oauth/client_secret", refresh_token="secret://mcp/github/oauth/refresh_token"),
        description="GitHub",
    )

    sanitized = _sanitize_server_for_read(server)

    assert sanitized.env["TOKEN"] == "••••••••"
    assert sanitized.headers["Authorization"] == "••••••••"
    assert sanitized.oauth is not None
    assert sanitized.oauth.client_secret == "••••••••"
    assert sanitized.oauth.refresh_token == "••••••••"


def test_mcp_persist_encrypts_sensitive_fields(monkeypatch):
    monkeypatch.setattr("app.gateway.routers.mcp.upsert_secret", lambda key, value: f"secret://{key}")

    payload = McpServerConfigResponse(
        enabled=True,
        type="http",
        env={"TOKEN": "raw-token"},
        headers={"Authorization": "raw-header"},
        oauth=McpOAuthConfigResponse(client_secret="raw-secret", refresh_token="raw-refresh"),
        description="GitHub",
    )

    persisted = _persist_secret_map("github", payload)

    assert persisted.env["TOKEN"] == "secret://mcp/github/env/TOKEN"
    assert persisted.headers["Authorization"] == "secret://mcp/github/headers/Authorization"
    assert persisted.oauth is not None
    assert persisted.oauth.client_secret == "secret://mcp/github/oauth/client_secret"
    assert persisted.oauth.refresh_token == "secret://mcp/github/oauth/refresh_token"
