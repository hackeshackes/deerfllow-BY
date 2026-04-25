import logging
from datetime import UTC, datetime
from importlib import import_module
from typing import Any

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)

ListCalendarRequest = import_module("lark_oapi.api.calendar.v4.model.list_calendar_request").ListCalendarRequest
ListCalendarEventRequest = import_module("lark_oapi.api.calendar.v4.model.list_calendar_event_request").ListCalendarEventRequest
ListFreebusyRequest = import_module("lark_oapi.api.calendar.v4.model.list_freebusy_request").ListFreebusyRequest
ListFreebusyRequestBody = import_module("lark_oapi.api.calendar.v4.model.list_freebusy_request_body").ListFreebusyRequestBody
PrimarysCalendarRequest = import_module("lark_oapi.api.calendar.v4.model.primarys_calendar_request").PrimarysCalendarRequest
PrimarysCalendarRequestBody = import_module("lark_oapi.api.calendar.v4.model.primarys_calendar_request_body").PrimarysCalendarRequestBody
CreateCalendarEventRequest = import_module("lark_oapi.api.calendar.v4.model.create_calendar_event_request").CreateCalendarEventRequest
PatchCalendarEventRequest = import_module("lark_oapi.api.calendar.v4.model.patch_calendar_event_request").PatchCalendarEventRequest
DeleteCalendarEventRequest = import_module("lark_oapi.api.calendar.v4.model.delete_calendar_event_request").DeleteCalendarEventRequest
CalendarEvent = import_module("lark_oapi.api.calendar.v4.model.calendar_event").CalendarEvent
TimeInfo = import_module("lark_oapi.api.calendar.v4.model.time_info").TimeInfo


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _iso_to_time_info(value: str) -> dict[str, str]:
    normalized_value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized_value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt_utc = dt.astimezone(UTC)
    return {"timestamp": str(int(dt_utc.timestamp())), "timezone": "UTC"}


def _normalize_calendar(calendar: Any) -> dict[str, Any]:
    return {
        "calendar_id": _get_attr(calendar, "calendar_id"),
        "summary": _get_attr(calendar, "summary"),
        "description": _get_attr(calendar, "description"),
        "permissions": _get_attr(calendar, "permissions"),
        "color": _get_attr(calendar, "color"),
        "type": _get_attr(calendar, "type"),
        "summary_alias": _get_attr(calendar, "summary_alias"),
        "is_deleted": _get_attr(calendar, "is_deleted"),
        "is_third_party": _get_attr(calendar, "is_third_party"),
        "role": _get_attr(calendar, "role"),
    }


def _normalize_event(event: Any) -> dict[str, Any]:
    organizer = _get_attr(event, "event_organizer")
    return {
        "event_id": _get_attr(event, "event_id"),
        "organizer_calendar_id": _get_attr(event, "organizer_calendar_id"),
        "summary": _get_attr(event, "summary"),
        "description": _get_attr(event, "description"),
        "start_time": _get_attr(event, "start_time"),
        "end_time": _get_attr(event, "end_time"),
        "status": _get_attr(event, "status"),
        "visibility": _get_attr(event, "visibility"),
        "free_busy_status": _get_attr(event, "free_busy_status"),
        "app_link": _get_attr(event, "app_link"),
        "create_time": _get_attr(event, "create_time"),
        "event_organizer": {
            "user_id": _get_attr(organizer, "user_id"),
            "display_name": _get_attr(organizer, "display_name"),
        }
        if organizer
        else None,
    }


@tool("feishu_calendar_list", parse_docstring=True)
def feishu_calendar_list(user_id: str | None = None) -> str:
    """List Feishu calendars.

    Args:
        user_id: User ID to get calendar for (optional, uses primary calendar if not provided).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        if user_id:
            request = (
                PrimarysCalendarRequest.builder()
                .user_id_type("open_id")
                .request_body(PrimarysCalendarRequestBody.builder().user_ids([user_id]).build())
                .build()
            )
            resp = client.calendar.v4.calendar.primarys(request)
            if not resp.success():
                return _error_response(f"Failed to get calendar: code={resp.code}, msg={resp.msg}")

            calendars = _get_attr(resp.data, "calendars") or []
            calendar = calendars[0] if calendars else None
            if calendar is None:
                return _error_response(f"No calendar found for user_id={user_id}")
            return _ok_response({"calendar": _normalize_calendar(calendar)})

        request = ListCalendarRequest.builder().build()
        resp = client.calendar.v4.calendar.list(request)
        if not resp.success():
            return _error_response(f"Failed to list calendars: code={resp.code}, msg={resp.msg}")

        data = resp.data
        calendar_list = _get_attr(data, "calendar_list") or []
        return _ok_response(
            {
                "has_more": _get_attr(data, "has_more"),
                "page_token": _get_attr(data, "page_token"),
                "sync_token": _get_attr(data, "sync_token"),
                "calendars": [_normalize_calendar(item) for item in calendar_list],
            }
        )
    except Exception as e:
        logger.error("[feishu_calendar_list] error: %s", e)
        return _error_response(str(e))


@tool("feishu_calendar_event_list", parse_docstring=True)
def feishu_calendar_event_list(calendar_id: str, start_time: str, end_time: str) -> str:
    """List events in a Feishu calendar.

    Args:
        calendar_id: Calendar ID (required).
        start_time: Start time in ISO format like "2024-01-01T00:00:00Z" (required).
        end_time: End time in ISO format (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        request = ListCalendarEventRequest.builder().calendar_id(calendar_id).start_time(start_time).end_time(end_time).build()
        resp = client.calendar.v4.calendar_event.list(request)
        if not resp.success():
            return _error_response(f"Failed to list events: code={resp.code}, msg={resp.msg}")

        data = resp.data
        items = _get_attr(data, "items") or []
        return _ok_response(
            {
                "calendar_id": calendar_id,
                "start_time": start_time,
                "end_time": end_time,
                "has_more": _get_attr(data, "has_more"),
                "page_token": _get_attr(data, "page_token"),
                "sync_token": _get_attr(data, "sync_token"),
                "events": [_normalize_event(item) for item in items],
            }
        )
    except Exception as e:
        logger.error("[feishu_calendar_event_list] error: %s", e)
        return _error_response(str(e))


@tool("feishu_calendar_event_create", parse_docstring=True)
def feishu_calendar_event_create(
    calendar_id: str,
    title: str,
    start_time: str,
    end_time: str,
    attendees: list[str] | None = None,
) -> str:
    """Create a calendar event in Feishu.

    Args:
        calendar_id: Calendar ID (required).
        title: Event title (required).
        start_time: Start time in ISO format (required).
        end_time: End time in ISO format (required).
        attendees: List of user IDs to invite (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        summary = title
        if attendees:
            summary = f"{title} [attendees: {', '.join(attendees)}]"

        start_time_info = TimeInfo.builder().timestamp(_iso_to_time_info(start_time)["timestamp"]).timezone("UTC").build()
        end_time_info = TimeInfo.builder().timestamp(_iso_to_time_info(end_time)["timestamp"]).timezone("UTC").build()
        body = CalendarEvent.builder().summary(summary).start_time(start_time_info).end_time(end_time_info).build()
        request = CreateCalendarEventRequest.builder().calendar_id(calendar_id).request_body(body).build()
        resp = client.calendar.v4.calendar_event.create(request)
        if not resp.success():
            return _error_response(f"Failed to create event: code={resp.code}, msg={resp.msg}")

        event = _get_attr(resp.data, "event") or resp.data
        return _ok_response(
            {
                "calendar_id": calendar_id,
                "requested_attendees": attendees or [],
                "event": _normalize_event(event),
            }
        )
    except Exception as e:
        logger.error("[feishu_calendar_event_create] error: %s", e)
        return _error_response(str(e))


@tool("feishu_calendar_freebusy", parse_docstring=True)
def feishu_calendar_freebusy(user_ids: list[str], start_time: str, end_time: str) -> str:
    """Query free/busy time for users.

    Args:
        user_ids: List of user IDs (required).
        start_time: Start time in ISO format (required).
        end_time: End time in ISO format (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not user_ids:
        return _error_response("user_ids must be a non-empty list")

    try:
        results: list[dict[str, Any]] = []
        for user_id in user_ids:
            request = (
                ListFreebusyRequest.builder()
                .user_id_type("open_id")
                .request_body(ListFreebusyRequestBody.builder().time_min(start_time).time_max(end_time).user_id(user_id).build())
                .build()
            )
            resp = client.calendar.v4.freebusy.list(request)
            if not resp.success():
                return _error_response(f"Failed to query freebusy for {user_id}: code={resp.code}, msg={resp.msg}")

            data = resp.data
            freebusy_list = _get_attr(data, "freebusy_list") or _get_attr(data, "freebusy_items") or []
            results.append(
                {
                    "user_id": user_id,
                    "freebusy": [
                        {
                            "start_time": _get_attr(item, "start_time"),
                            "end_time": _get_attr(item, "end_time"),
                        }
                        for item in freebusy_list
                    ],
                }
            )

        return _ok_response(
            {
                "start_time": start_time,
                "end_time": end_time,
                "results": results,
            }
        )
    except Exception as e:
        logger.error("[feishu_calendar_freebusy] error: %s", e)
        return _error_response(str(e))


@tool("feishu_calendar_event_update", parse_docstring=True)
def feishu_calendar_event_update(calendar_id: str, event_id: str, title: str | None = None, start_time: str | None = None, end_time: str | None = None) -> str:
    """Update a calendar event in Feishu.

    Args:
        calendar_id: Calendar ID (required).
        event_id: Event ID to update (required).
        title: New event title (optional).
        start_time: New start time in ISO format (optional).
        end_time: New end time in ISO format (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not calendar_id.strip():
        return _error_response("calendar_id is required")
    if not event_id.strip():
        return _error_response("event_id is required")

    try:
        body = CalendarEvent.builder()
        if title:
            body = body.summary(title)
        if start_time:
            body = body.start_time(TimeInfo.builder().timestamp(_iso_to_time_info(start_time)["timestamp"]).timezone("UTC").build())
        if end_time:
            body = body.end_time(TimeInfo.builder().timestamp(_iso_to_time_info(end_time)["timestamp"]).timezone("UTC").build())
        body = body.build()

        request = PatchCalendarEventRequest.builder().calendar_id(calendar_id).event_id(event_id).request_body(body).build()
        resp = client.calendar.v4.calendar_event.patch(request)
        if not resp.success():
            return _error_response(f"Failed to update event: code={resp.code}, msg={resp.msg}")

        event = _get_attr(resp.data, "event") or resp.data
        return _ok_response(
            {
                "calendar_id": calendar_id,
                "event_id": event_id,
                "event": _normalize_event(event),
            }
        )
    except Exception as e:
        logger.error("[feishu_calendar_event_update] error: %s", e)
        return _error_response(str(e))


@tool("feishu_calendar_event_get", parse_docstring=True)
def feishu_calendar_event_get(calendar_id: str, event_id: str) -> str:
    """Get a calendar event by ID from Feishu.

    Args:
        calendar_id: Calendar ID (required).
        event_id: Event ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not calendar_id.strip():
        return _error_response("calendar_id is required")
    if not event_id.strip():
        return _error_response("event_id is required")

    try:
        GetCalendarEventRequest = import_module("lark_oapi.api.calendar.v4.model.get_calendar_event_request").GetCalendarEventRequest
        request = GetCalendarEventRequest.builder().calendar_id(calendar_id).event_id(event_id).build()
        resp = client.calendar.v4.calendar_event.get(request)
        if not resp.success():
            return _error_response(f"Failed to get event: code={resp.code}, msg={resp.msg}")

        event = _get_attr(resp.data, "event") or resp.data
        return _ok_response({"calendar_id": calendar_id, "event": _normalize_event(event)})
    except Exception as e:
        logger.error("[feishu_calendar_event_get] error: %s", e)
        return _error_response(str(e))


@tool("feishu_calendar_event_delete", parse_docstring=True)
def feishu_calendar_event_delete(calendar_id: str, event_id: str) -> str:
    """Delete a calendar event from Feishu.

    Args:
        calendar_id: Calendar ID (required).
        event_id: Event ID to delete (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not calendar_id.strip():
        return _error_response("calendar_id is required")
    if not event_id.strip():
        return _error_response("event_id is required")

    try:
        request = DeleteCalendarEventRequest.builder().calendar_id(calendar_id).event_id(event_id).build()
        resp = client.calendar.v4.calendar_event.delete(request)
        if not resp.success():
            return _error_response(f"Failed to delete event: code={resp.code}, msg={resp.msg}")

        return _ok_response({"calendar_id": calendar_id, "event_id": event_id, "deleted": True})
    except Exception as e:
        logger.error("[feishu_calendar_event_delete] error: %s", e)
        return _error_response(str(e))
