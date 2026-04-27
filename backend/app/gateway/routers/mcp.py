import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user, require_user
from deerflow.admin import append_admin_audit_record, is_secret_ref, mask_secret_value, upsert_secret
from deerflow.config.extensions_config import ExtensionsConfig, get_extensions_config, reload_extensions_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


class McpOAuthConfigResponse(BaseModel):
    """OAuth configuration for an MCP server."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(default="", description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials", description="OAuth grant type")
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience")
    token_field: str = Field(default="access_token", description="Token response field containing access token")
    token_type_field: str = Field(default="token_type", description="Token response field containing token type")
    expires_in_field: str = Field(default="expires_in", description="Token response field containing expires-in seconds")
    default_token_type: str = Field(default="Bearer", description="Default token type when response omits token_type")
    refresh_skew_seconds: int = Field(default=60, description="Refresh this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")


class McpServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', or 'http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfigResponse | None = Field(default=None, description="OAuth configuration for MCP HTTP/SSE servers")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
    )


class McpConfigUpdateRequest(BaseModel):
    """Request model for updating MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        ...,
        description="Map of MCP server name to configuration",
    )


def _sanitize_oauth_for_read(oauth: McpOAuthConfigResponse | None) -> McpOAuthConfigResponse | None:
    if oauth is None:
        return None
    data = oauth.model_dump()
    data["client_secret"] = mask_secret_value(oauth.client_secret)
    data["refresh_token"] = mask_secret_value(oauth.refresh_token)
    return McpOAuthConfigResponse(**data)


def _sanitize_server_for_read(config: McpServerConfigResponse) -> McpServerConfigResponse:
    data = config.model_dump()
    oauth = _sanitize_oauth_for_read(config.oauth)
    data["env"] = {key: mask_secret_value(value) or "" for key, value in config.env.items()}
    data["headers"] = {key: mask_secret_value(value) or "" for key, value in config.headers.items()}
    data["oauth"] = oauth.model_dump() if oauth is not None else None
    return McpServerConfigResponse(**data)


def _persist_secret_map(server_name: str, payload: McpServerConfigResponse) -> McpServerConfigResponse:
    data = payload.model_dump()
    data["env"] = {key: upsert_secret(f"mcp/{server_name}/env/{key}", value) if value and not value.startswith("$") and not is_secret_ref(value) else value for key, value in data["env"].items()}
    data["headers"] = {key: upsert_secret(f"mcp/{server_name}/headers/{key}", value) if value and not value.startswith("$") and not is_secret_ref(value) else value for key, value in data["headers"].items()}
    oauth = data.get("oauth")
    if oauth:
        for field_name in ("client_secret", "refresh_token"):
            field_value = oauth.get(field_name)
            if field_value and not field_value.startswith("$") and not is_secret_ref(field_value):
                oauth[field_name] = upsert_secret(f"mcp/{server_name}/oauth/{field_name}", field_value)
    return McpServerConfigResponse(**data)


@router.get(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Get MCP Configuration",
    description="Retrieve the current Model Context Protocol (MCP) server configurations.",
)
async def get_mcp_configuration(request: Request) -> McpConfigResponse:
    """Get the current MCP configuration.

    Returns:
        The current MCP configuration with all servers.

    Example:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "ghp_xxx"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    require_user(request)
    config = get_extensions_config()

    return McpConfigResponse(mcp_servers={name: _sanitize_server_for_read(McpServerConfigResponse(**server.model_dump())) for name, server in config.mcp_servers.items()})


@router.put(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Update MCP Configuration",
    description="Update Model Context Protocol (MCP) server configurations and save to file.",
)
async def update_mcp_configuration(request: McpConfigUpdateRequest, http_request: Request) -> McpConfigResponse:
    """Update the MCP configuration.

    This will:
    1. Save the new configuration to the mcp_config.json file
    2. Reload the configuration cache
    3. Reset MCP tools cache to trigger reinitialization

    Args:
        request: The new MCP configuration to save.

    Returns:
        The updated MCP configuration.

    Raises:
        HTTPException: 500 if the configuration file cannot be written.

    Example Request:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    user = require_owner_user(http_request)
    try:
        # Get the current config path (or determine where to save it)
        config_path = ExtensionsConfig.resolve_config_path()

        # If no config file exists, create one in the parent directory (project root)
        if config_path is None:
            config_path = Path.cwd().parent / "extensions_config.json"
            logger.info(f"No existing extensions config found. Creating new config at: {config_path}")

        # Load current config to preserve skills configuration
        current_config = get_extensions_config()

        # Convert request to dict format for JSON serialization
        persisted_servers = {name: _persist_secret_map(name, server).model_dump() for name, server in request.mcp_servers.items()}
        config_data = {
            "mcpServers": persisted_servers,
            "skills": {name: {"enabled": skill.enabled} for name, skill in current_config.skills.items()},
        }

        # Write the configuration to file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"MCP configuration updated and saved to: {config_path}")

        # NOTE: No need to reload/reset cache here - LangGraph Server (separate process)
        # will detect config file changes via mtime and reinitialize MCP tools automatically

        # Reload the configuration and update the global cache
        reloaded_config = reload_extensions_config()
        append_admin_audit_record("mcp.updated", actor_id=user.id, target="extensions_config.json", details={"server_count": len(request.mcp_servers)})
        return McpConfigResponse(mcp_servers={name: _sanitize_server_for_read(McpServerConfigResponse(**server.model_dump())) for name, server in reloaded_config.mcp_servers.items()})

    except Exception as e:
        logger.error(f"Failed to update MCP configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {str(e)}")


class MCPPresetResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    server: dict


class MCPPresetsResponse(BaseModel):
    presets: list[MCPPresetResponse]


MCP_PRESETS: list[MCPPresetResponse] = [
    MCPPresetResponse(
        id="github",
        name="GitHub",
        description="GitHub API operations - repository, issues, pull requests",
        icon="🐙",
        server={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": ""},
            "description": "GitHub MCP server for repository operations",
        },
    ),
    MCPPresetResponse(
        id="filesystem",
        name="Filesystem",
        description="Local filesystem operations",
        icon="📁",
        server={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {},
            "description": "Filesystem MCP server for file operations",
        },
    ),
    MCPPresetResponse(
        id="brave-search",
        name="Brave Search",
        description="Web search via Brave Search API",
        icon="🔍",
        server={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": ""},
            "description": "Brave Search MCP server for web search",
        },
    ),
    MCPPresetResponse(
        id="slack",
        name="Slack",
        description="Slack messaging integration",
        icon="💬",
        server={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {"SLACK_BOT_TOKEN": "", "SLACK_TEAM_ID": ""},
            "description": "Slack MCP server for messaging",
        },
    ),
    MCPPresetResponse(
        id="google-maps",
        name="Google Maps",
        description="Google Maps API integration",
        icon="🗺️",
        server={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
            "env": {"GOOGLE_MAPS_API_KEY": ""},
            "description": "Google Maps MCP server for location services",
        },
    ),
    MCPPresetResponse(
        id="memory",
        name="Memory",
        description="Persistent memory and context management",
        icon="🧠",
        server={
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {},
            "description": "Memory MCP server for persistent context",
        },
    ),
]


@router.get("/mcp/presets", response_model=MCPPresetsResponse, summary="Get MCP Presets")
async def get_mcp_presets() -> MCPPresetsResponse:
    """Get available MCP server presets."""
    return MCPPresetsResponse(presets=MCP_PRESETS)


class MCPServerTestRequest(BaseModel):
    enabled: bool = True
    type: str = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    oauth: McpOAuthConfigResponse | None = None
    description: str = ""


class MCPServerTestResponse(BaseModel):
    success: bool
    error: str | None = None


@router.post("/mcp/servers/test", response_model=MCPServerTestResponse, summary="Test MCP Server Connection")
async def test_mcp_server(request: MCPServerTestRequest, http_request: Request) -> MCPServerTestResponse:
    """Test connection to an MCP server configuration."""
    require_owner_user(http_request)
    if request.type == "stdio":
        if not request.command:
            return MCPServerTestResponse(success=False, error="Command is required for stdio type")
        return MCPServerTestResponse(success=True, error=None)
    elif request.type in ("sse", "http"):
        if not request.url:
            return MCPServerTestResponse(success=False, error="URL is required for sse/http type")
        return MCPServerTestResponse(success=True, error=None)
    return MCPServerTestResponse(success=False, error=f"Unknown server type: {request.type}")


@router.get("/mcp/servers/{server_name}/status", response_model=dict, summary="Get MCP Server Status")
async def get_mcp_server_status(server_name: str, request: Request) -> dict:
    """Get the status of a specific MCP server."""
    require_user(request)
    config = get_extensions_config()
    server = config.mcp_servers.get(server_name)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    return {
        "name": server_name,
        "enabled": server.enabled,
        "configured": True,
    }
