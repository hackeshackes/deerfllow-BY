"""ASGI middleware that auto-emits AuditEvents for write requests.

Configurable actor_resolver extracts (actor_id, actor_type) from the request
(typically from a JWT/session set by upstream auth middleware).
"""
from __future__ import annotations

import re
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .models import ActorType, AuditEvent
from .writer import AuditWriter

ActorResolver = Callable[[Request], tuple[str, ActorType]]


_VERB_TO_ACTION = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

# Match FastAPI path parameters like {tid}, {user_id}, etc.
_PATH_PARAM_RE = re.compile(r"\{[^}]+\}")


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, writer: AuditWriter, actor_resolver: ActorResolver):
        super().__init__(app)
        self._writer = writer
        self._actor_resolver = actor_resolver

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        # Only audit write operations
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and 200 <= response.status_code < 400:
            try:
                actor_id, actor_type = self._actor_resolver(request)
            except Exception:
                actor_id, actor_type = "anonymous", ActorType.SYSTEM

            # Prefer the route template (e.g. "/threads/{tid}") over the
            # concrete URL so the action stays stable across parameter
            # values. Fall back to url.path for un-matched requests (404s).
            route = request.scope.get("route")
            template = getattr(route, "path", None) or request.url.path
            # Strip path parameters so the action is stable across values.
            template = _PATH_PARAM_RE.sub("", template)
            segments = [s for s in template.strip("/").split("/") if s]
            verb_action = _VERB_TO_ACTION.get(request.method, request.method.lower())
            resource_segment = segments[0] if segments else "unknown"
            action = f"{resource_segment}.{verb_action}"
            resource_id = None
            if request.path_params:
                # Prefer common path-parameter names; fall back to the first
                for key in ("id", "tid", "uid", "rid"):
                    if key in request.path_params:
                        resource_id = request.path_params[key]
                        break
                if resource_id is None:
                    resource_id = request.path_params[list(request.path_params.keys())[0]]
            event = AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                action=action,
                resource_type=resource_segment,
                resource_id=resource_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=response.status_code < 400,
            )
            await self._writer.write(event)
        return response