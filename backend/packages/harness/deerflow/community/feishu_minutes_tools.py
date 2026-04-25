import logging
from importlib import import_module
from typing import Any

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _build_get_minute_request(minutes_id: str) -> Any:
    request_cls = getattr(import_module("lark_oapi.api.minutes.v1.model.get_minute_request"), "GetMinuteRequest")
    builder = request_cls.builder()

    if hasattr(builder, "minutes_id"):
        builder = builder.minutes_id(minutes_id)
    elif hasattr(builder, "minute_token"):
        builder = builder.minute_token(minutes_id)
    else:
        raise AttributeError("GetMinuteRequest builder does not support minutes_id or minute_token")

    return builder.build()


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _normalize_participant(participant: Any) -> dict[str, Any]:
    return {
        "user_id": _get_attr(participant, "user_id"),
        "open_id": _get_attr(participant, "open_id"),
        "union_id": _get_attr(participant, "union_id"),
        "name": _get_attr(participant, "name", "display_name", "user_name"),
        "avatar_url": _get_attr(participant, "avatar_url", "avatar"),
        "department_name": _get_attr(participant, "department_name", "department"),
    }


def _extract_transcript(data: Any) -> Any:
    for name in ("transcript", "transcripts", "paragraphs", "contents", "content"):
        value = _get_attr(data, name)
        if value:
            return value
    minutes = _get_attr(data, "minutes")
    if minutes:
        for name in ("transcript", "transcripts", "paragraphs", "contents", "content"):
            value = _get_attr(minutes, name)
            if value:
                return value
    return []


def _normalize_minutes(data: Any, minutes_id: str) -> dict[str, Any]:
    minutes = _get_attr(data, "minutes") or data
    return {
        "minutes_id": _get_attr(minutes, "minutes_id", "id") or minutes_id,
        "topic": _get_attr(minutes, "topic", "title", "name"),
        "owner_id": _get_attr(minutes, "owner_id"),
        "status": _get_attr(minutes, "status"),
        "url": _get_attr(minutes, "url", "minute_url"),
        "duration": _get_attr(minutes, "duration", "duration_ms"),
        "start_time": _get_attr(minutes, "start_time"),
        "end_time": _get_attr(minutes, "end_time"),
        "create_time": _get_attr(minutes, "create_time", "created_time"),
        "update_time": _get_attr(minutes, "update_time", "updated_time"),
    }


@tool("feishu_minutes_get", parse_docstring=True)
def feishu_minutes_get(minutes_id: str) -> str:
    """Get basic info of a Feishu minutes.

    Args:
        minutes_id: Minutes ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        request = _build_get_minute_request(minutes_id)
        response = client.minutes.v1.minute.get(request)
        if not response.success():
            return _error_response(f"Failed to get minutes: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(_normalize_minutes(data, minutes_id))
    except Exception as e:
        logger.error("[feishu_minutes_get] error minutes_id=%s: %s", minutes_id, e)
        return _error_response(str(e))


@tool("feishu_minutes_content", parse_docstring=True)
def feishu_minutes_content(minutes_id: str) -> str:
    """Get transcript/content of a Feishu minutes.

    Args:
        minutes_id: Minutes ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        request = _build_get_minute_request(minutes_id)
        response = client.minutes.v1.minute.get(request)
        if not response.success():
            return _error_response(f"Failed to get minutes content: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        participants = _get_attr(data, "participants") or _get_attr(_get_attr(data, "minutes"), "participants") or []
        return _ok_response(
            {
                "meeting_info": _normalize_minutes(data, minutes_id),
                "transcript": _extract_transcript(data),
                "participants": [_normalize_participant(participant) for participant in participants],
            }
        )
    except Exception as e:
        logger.error("[feishu_minutes_content] error minutes_id=%s: %s", minutes_id, e)
        return _error_response(str(e))
