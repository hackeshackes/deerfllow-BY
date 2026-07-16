import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.gateway.auth import get_default_workspace_id_for_user, get_workspace_membership, session_payload_from_request, session_user_from_request
from app.gateway.auth_context import current_user_email, current_user_id, current_user_role, current_workspace_id, current_workspace_role
from app.gateway.config import get_gateway_config
from app.gateway.deps import langgraph_runtime
from app.gateway.rate_limit import RateLimitMiddleware
from app.gateway.routers import (
    admin_config,
    admin_knowledge,
    admin_memory,
    admin_monitoring,
    admin_secrets,
    admin_token_usage,
    agents,
    artifacts,
    assistants_compat,
    channels,
    custom_skills,
    knowledge,
    mcp,
    memory,
    models,
    ppt,
    runs,
    skills,
    suggestions,
    tasks,
    thread_runs,
    threads,
    uploads,
    user_skills,
    users,
    voice,
)
from deerflow.config.app_config import get_app_config

# Request ID context variable for tracing
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add X-Request-ID header for request tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        request_id_ctx_var.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""

    # Load config and check necessary environment variables at startup
    try:
        get_app_config()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration during gateway startup: {e}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from e
    config = get_gateway_config()
    logger.info(f"Starting API Gateway on {config.host}:{config.port}")

    # v1.5.7: Auto-register connectors from MICX_CONNECTORS env (YAML body).
    # The env variable holds the same shape as the connector YAML files in
    # `app/gateway/connectors/*/yaml/*.example.yaml`. When the env is unset
    # or empty, no connectors are registered — the admin UI will simply
    # show an empty list, which is the right behavior for dev environments.
    try:
        import yaml

        from app.gateway.connectors.integrations.builtin import (
            register_builtin_connectors,
        )
        from app.gateway.connectors.registry import get_registry

        connectors_yaml = os.environ.get("MICX_CONNECTORS", "").strip()
        if connectors_yaml:
            parsed = yaml.safe_load(connectors_yaml) or {}
            register_builtin_connectors(
                registry=get_registry(),
                config=parsed,
            )
            logger.info("Connectors registered: %s", get_registry().list_names())
    except Exception:
        logger.exception("Failed to register connectors at startup")

    # Initialize LangGraph runtime components (StreamBridge, RunManager, checkpointer, store)
    async with langgraph_runtime(app):
        logger.info("LangGraph runtime initialised")

        # Start IM channel service if any channels are configured
        try:
            from app.channels.service import start_channel_service

            channel_service = await start_channel_service()
            logger.info("Channel service started: %s", channel_service.get_status())
        except Exception:
            logger.exception("No IM channels configured or channel service failed to start")

        try:
            from app.gateway.scheduler import load_scheduled_tasks_from_db, start_scheduler

            start_scheduler()
            await load_scheduled_tasks_from_db()
            logger.info("Scheduler started and existing tasks loaded")
        except Exception:
            logger.exception("Failed to start scheduler or load tasks")

        # v1.5.10 — wire multitenancy singletons + router.
        # Provides /api/admin/cost/summary, /api/admin/usage/{tenant_id},
        # and /api/admin/quota/{tenant_id} using the v1.5.8 data layer.
        try:
            from app.gateway.multitenancy.models import QuotaPeriod, ResourceQuota
            from app.gateway.multitenancy.quota import QuotaService
            from app.gateway.multitenancy.routers.api import (
                configure as configure_mt,
            )
            from app.gateway.multitenancy.routers.api import (
                router as multitenancy_router,
            )
            from app.gateway.multitenancy.usage_tracker import (
                InMemoryUsageTracker,
            )

            # Use a default quota for the dev tenant. Production reads from
            # a tenant-aware quota store (v1.6.0 work).
            default_quota = ResourceQuota(
                tenant_id="default",
                period=QuotaPeriod.MONTHLY,
                max_tokens=0,  # 0 = unlimited (advisory)
                max_rpm=0,
            )
            tracker = InMemoryUsageTracker()
            quota_svc = QuotaService(usage=tracker, quota=default_quota)
            configure_mt(tracker=tracker, quota_service=quota_svc)
            app.include_router(multitenancy_router)

            # v1.5.10 — Prometheus /metrics endpoint. Exposes the
            # in-process Counter / Gauge registry in text exposition
            # format. No prometheus-client dependency.
            from app.gateway.observability.routers.metrics import (
                router as metrics_router,
            )

            app.include_router(metrics_router)

            # v1.6.x — cross-workspace publish (B2). Wires PublishService
            # against the same Store that backs thread records, so
            # PublishButton on the frontend can target a workspace and
            # produce a real new thread + lineage event.
            from app.gateway.collaboration.publish import PublishService
            from app.gateway.collaboration.routers.publish import (
                configure as configure_publish,
            )
            from app.gateway.collaboration.routers.publish import (
                router as publish_router,
            )

            store = getattr(app.state, "store", None)
            if store is not None:
                configure_publish(PublishService(store=store))
                app.include_router(publish_router)
                logger.info("Collaboration publish router mounted")
            else:
                logger.warning("Store unavailable at lifespan; publish router not mounted")

            logger.info("Multitenancy admin router mounted")
        except Exception:
            logger.exception("Failed to mount multitenancy admin router; admin endpoints will return 503")

        yield

        # Stop channel service on shutdown
        try:
            from app.channels.service import stop_channel_service

            await stop_channel_service()
        except Exception:
            logger.exception("Failed to stop channel service")

    logger.info("Shutting down API Gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """

    app = FastAPI(
        title="DeerFlow API Gateway",
        description="""
## DeerFlow API Gateway

API Gateway for DeerFlow - A LangGraph-based AI agent backend with sandbox execution capabilities.

### Features

- **Models Management**: Query and retrieve available AI models
- **MCP Configuration**: Manage Model Context Protocol (MCP) server configurations
- **Memory Management**: Access and manage global memory data for personalized conversations
- **Skills Management**: Query and manage skills and their enabled status
- **Artifacts**: Access thread artifacts and generated files
- **Health Monitoring**: System health check endpoints

### Architecture

LangGraph requests are handled by nginx reverse proxy.
This gateway provides custom endpoints for models, MCP configuration, skills, and artifacts.
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "models",
                "description": "Operations for querying available AI models and their configurations",
            },
            {
                "name": "mcp",
                "description": "Manage Model Context Protocol (MCP) server configurations",
            },
            {
                "name": "memory",
                "description": "Access and manage global memory data for personalized conversations",
            },
            {
                "name": "skills",
                "description": "Manage skills and their configurations",
            },
            {
                "name": "artifacts",
                "description": "Access and download thread artifacts and generated files",
            },
            {
                "name": "uploads",
                "description": "Upload and manage user files for threads",
            },
            {
                "name": "threads",
                "description": "Manage DeerFlow thread-local filesystem data",
            },
            {
                "name": "agents",
                "description": "Create and manage custom agents with per-agent config and prompts",
            },
            {
                "name": "suggestions",
                "description": "Generate follow-up question suggestions for conversations",
            },
            {
                "name": "channels",
                "description": "Manage IM channel integrations (Feishu, Slack, Telegram)",
            },
            {
                "name": "assistants-compat",
                "description": "LangGraph Platform-compatible assistants API (stub)",
            },
            {
                "name": "runs",
                "description": "LangGraph Platform-compatible runs lifecycle (create, stream, cancel)",
            },
            {
                "name": "health",
                "description": "Health check and system status endpoints",
            },
        ],
    )

    # CORS is handled by nginx - no need for FastAPI middleware

    # Request ID middleware for tracing
    app.add_middleware(RequestIDMiddleware)

    # Per-IP rate limit (in-memory, sliding window). 120 req/min default.
    app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)

    # Audit middleware — auto-emit events for write requests. Skipped when
    # the audit subsystem is disabled in config. Idempotent: only added
    # once per process even if create_app() is called repeatedly (e.g. in
    # tests that build multiple FastAPI clients).
    from app.gateway.identity.audit.middleware import AuditMiddleware
    from app.gateway.identity.audit.models import ActorType
    from app.gateway.identity.audit.writer import get_audit_writer
    from app.gateway.identity.config import get_identity_config

    if get_identity_config().audit_enabled and not getattr(app.state, "audit_middleware_added", False):

        def _actor_resolver(request):
            user = getattr(request.state, "current_user", None)
            if user is None:
                return ("anonymous", ActorType.USER)
            return (str(user.id), ActorType.USER)

        app.add_middleware(
            AuditMiddleware,
            writer=get_audit_writer(),
            actor_resolver=_actor_resolver,
        )
        app.state.audit_middleware_added = True

    @app.middleware("http")
    async def attach_current_user(request, call_next):
        payload = session_payload_from_request(request)
        user = session_user_from_request(request)
        request.state.current_user = user
        active_workspace_id = None
        active_workspace_role_value = None
        if user is not None:
            requested_workspace_id = payload.get("active_workspace_id") if payload else None
            active_workspace_id = requested_workspace_id or get_default_workspace_id_for_user(user.id)
            membership = get_workspace_membership(user.id, active_workspace_id) if active_workspace_id else None
            if membership is None:
                active_workspace_id = get_default_workspace_id_for_user(user.id)
                membership = get_workspace_membership(user.id, active_workspace_id) if active_workspace_id else None
            active_workspace_role_value = membership.role if membership else None
        request.state.active_workspace_id = active_workspace_id
        request.state.active_workspace_role = active_workspace_role_value
        token_id = current_user_id.set(user.id if user else None)
        token_role = current_user_role.set(user.role if user else None)
        token_email = current_user_email.set(user.email if user else None)
        token_workspace_id = current_workspace_id.set(active_workspace_id)
        token_workspace_role = current_workspace_role.set(active_workspace_role_value)
        try:
            return await call_next(request)
        finally:
            current_user_id.reset(token_id)
            current_user_role.reset(token_role)
            current_user_email.reset(token_email)
            current_workspace_id.reset(token_workspace_id)
            current_workspace_role.reset(token_workspace_role)

    # Include routers
    app.include_router(admin_config.router)
    app.include_router(admin_knowledge.router)
    app.include_router(admin_memory.router)
    app.include_router(admin_monitoring.router)
    app.include_router(admin_secrets.router)
    app.include_router(admin_token_usage.router)

    # Models API is mounted at /api/models
    app.include_router(models.router)

    # PPT Generation API is mounted at /api/ppt
    app.include_router(ppt.router)

    # MCP API is mounted at /api/mcp
    app.include_router(mcp.router)

    # Memory API is mounted at /api/memory
    app.include_router(memory.router)

    # Skills API is mounted at /api/skills
    app.include_router(skills.router)

    # User Skills API is mounted at /api/user/skills
    app.include_router(user_skills.router)

    # Custom Skills CRUD API is mounted at /api/user/skills/custom
    app.include_router(custom_skills.router)

    # Artifacts API is mounted at /api/threads/{thread_id}/artifacts
    app.include_router(artifacts.router)

    # Uploads API is mounted at /api/threads/{thread_id}/uploads
    app.include_router(uploads.router)

    # Thread cleanup API is mounted at /api/threads/{thread_id}
    app.include_router(threads.router)

    # Agents API is mounted at /api/agents
    app.include_router(agents.router)

    app.include_router(users.router)

    # Tasks API is mounted at /api/tasks
    app.include_router(tasks.router)

    # Knowledge API is mounted at /api/knowledge
    app.include_router(knowledge.router)

    # Suggestions API is mounted at /api/threads/{thread_id}/suggestions
    app.include_router(suggestions.router)

    # Channels API is mounted at /api/channels
    app.include_router(channels.router)

    # Voice API is mounted at /api/voice (STT/TTS)
    app.include_router(voice.router)

    # Assistants compatibility API (LangGraph Platform stub)
    app.include_router(assistants_compat.router)

    # Thread Runs API (LangGraph Platform-compatible runs lifecycle)
    app.include_router(thread_runs.router)

    # Stateless Runs API (stream/wait without a pre-existing thread)
    app.include_router(runs.router)

    # OIDC identity routes (login/callback/logout)
    from app.gateway.identity.routers.oidc import router as oidc_router

    app.include_router(oidc_router)

    # RBAC admin API (role CRUD)
    from app.gateway.identity.routers.rbac import router as rbac_router

    app.include_router(rbac_router)

    # Audit query & export API
    from app.gateway.identity.routers.audit import router as audit_router

    app.include_router(audit_router)

    # SCIM admin API
    from app.gateway.identity.routers.scim import router as scim_router

    app.include_router(scim_router)

    # Connectors unified API (v1.5.5)
    from app.gateway.connectors.routers.connectors import router as connectors_router

    app.include_router(connectors_router)

    # Subscriptions API (v1.5.5)
    from app.gateway.subscriptions.routers.subscriptions import (
        router as subscriptions_router,
    )

    app.include_router(subscriptions_router)

    # Spaces API (v1.5.5)
    from app.gateway.spaces.api import router as spaces_router

    app.include_router(spaces_router)

    # Comments HTTP API (v1.5.8)
    from app.gateway.comments.routers.comments import router as comments_router

    app.include_router(comments_router)

    # Canvas workflows API (v1.6.x) mounted at /api/workflows.
    # Store backend is selected by MICX_CANVAS_STORE (memory | sqlite) —
    # see ``app.gateway.canvas.store_service.get_canvas_store_and_versions``.
    # Default memory preserves v1.6.0-canvas behaviour for cold-start.
    from app.gateway.canvas.routers.workflows import (
        configure as configure_canvas,
    )
    from app.gateway.canvas.routers.workflows import (
        router as canvas_router,
    )
    from app.gateway.canvas.store_service import get_canvas_store_and_versions

    wstore, vstore = get_canvas_store_and_versions()
    # VersionManager wraps both stores; without wiring it here, the
    # router would 503 on the first create/rollback attempt.
    from app.gateway.canvas.versions import VersionManager

    configure_canvas(wstore, VersionManager(wstore, vstore))
    app.include_router(canvas_router)
    app.state.canvas_store = wstore
    # v1.6.1 follow-up: execution-history store. None under memory
    # backend; the canvas router degrades to "executions: []" if
    # the attr is missing.
    from app.gateway.canvas.store_service import get_canvas_execution_store

    app.state.canvas_execution_store = get_canvas_execution_store()
    app.state.canvas_version_store = vstore
    # Wire a singleton store for the app's lifetime. Backend selected
    # by MICX_COMMENTS_STORE env (memory | sqlite). Tests can still
    # swap this out via app.state.comments_store before the first
    # request arrives — see ``service.get_comment_store``.
    from app.gateway.comments.service import get_comment_store

    app.state.comments_store = get_comment_store()

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint.

        Returns:
            Service health status information.
        """
        return {"status": "healthy", "service": "deer-flow-gateway"}

    return app


# Create app instance for uvicorn
app = create_app()
