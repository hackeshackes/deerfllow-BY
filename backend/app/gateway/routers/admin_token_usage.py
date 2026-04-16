from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.gateway.auth import list_users, require_owner_user
from deerflow.admin.token_usage import get_token_usage_store

router = APIRouter(prefix="/api/admin/token-usage", tags=["admin-token-usage"])


class TokenUsageSummary(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0


class UserTokenUsage(BaseModel):
    user_id: str
    email: str | None = None
    name: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0


class ModelTokenUsage(BaseModel):
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0


class TokenUsageResponse(BaseModel):
    period_start: str | None = None
    period_end: str | None = None
    total: TokenUsageSummary
    by_user: list[UserTokenUsage]
    by_model: list[ModelTokenUsage]


@router.get("", response_model=TokenUsageResponse)
async def get_token_usage(
    request: Request,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> TokenUsageResponse:
    require_owner_user(request)
    store = get_token_usage_store()
    since = datetime.now(UTC) - timedelta(days=days)
    since_iso = since.isoformat()

    users = {u.id: u for u in list_users()}

    total = store.total(since=since)
    by_user_raw = store.aggregate_by_user(since=since)
    by_model_raw = store.aggregate_by_model(since=since)

    by_user = [
        UserTokenUsage(
            user_id=uid,
            email=users[uid].email if uid in users else None,
            name=users[uid].name if uid in users else None,
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            total_tokens=data["total_tokens"],
            request_count=data["request_count"],
        )
        for uid, data in by_user_raw.items()
    ]
    by_user.sort(key=lambda x: x.total_tokens, reverse=True)

    by_model = [
        ModelTokenUsage(
            model_name=name,
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            total_tokens=data["total_tokens"],
            request_count=data["request_count"],
        )
        for name, data in by_model_raw.items()
    ]
    by_model.sort(key=lambda x: x.total_tokens, reverse=True)

    return TokenUsageResponse(
        period_start=since_iso,
        period_end=datetime.now(UTC).isoformat(),
        total=TokenUsageSummary(**total),
        by_user=by_user,
        by_model=by_model,
    )
