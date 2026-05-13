"""Feishu Chat (Group) management tools."""

import logging

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


@tool("feishu_chat_list", parse_docstring=True)
def feishu_chat_list(
    page_size: int = 20,
    page_token: str = "",
) -> str:
    """List all groups the bot has joined.

    Args:
        page_size: Number of results per page (default 20, max 50).
        page_token: Pagination token from previous response.
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        import lark_oapi as lark

        request = lark.im.v1.ChatListRequest.builder().page_size(page_size)
        if page_token:
            request.page_token(page_token)

        response = client.im.v1.ChatList(request.build())
        if not response.success():
            return _error_response(f"feishu_chat_list failed: code={response.code}, msg={response.msg}")

        data = response.data or {}
        items = []
        for item in data.get("items", []):
            items.append(
                {
                    "chat_id": item.chat_id,
                    "name": item.name,
                    "description": item.description or "",
                    "owner_id": item.owner_id or "",
                    "member_count": getattr(item, "member_count", 0),
                }
            )

        result = {
            "items": items,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token", ""),
        }
        return _ok_response(result)
    except Exception as e:
        logger.error("[feishu_chat_list] error: %s", e)
        return _error_response(str(e))


@tool("feishu_chat_get", parse_docstring=True)
def feishu_chat_get(chat_id: str) -> str:
    """Get detailed information about a specific group.

    Args:
        chat_id: The unique identifier of the group (required).
    """
    if not chat_id:
        return _error_response("chat_id is required")

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        import lark_oapi as lark

        request = lark.im.v1.ChatGetRequest.builder().chat_id(chat_id)
        response = client.im.v1.ChatGet(request.build())
        if not response.success():
            return _error_response(f"feishu_chat_get failed: code={response.code}, msg={response.msg}")

        data = response.data
        if data is None:
            return _error_response(f"Group {chat_id} not found")

        result = {
            "chat_id": data.chat_id,
            "name": data.name,
            "description": data.description or "",
            "owner_id": data.owner_id or "",
            "created_at": data.created_at or 0,
            "member_count": getattr(data, "member_count", 0),
        }
        return _ok_response(result)
    except Exception as e:
        logger.error("[feishu_chat_get] error: %s", e)
        return _error_response(str(e))


@tool("feishu_chat_members", parse_docstring=True)
def feishu_chat_members(
    chat_id: str,
    page_size: int = 50,
    page_token: str = "",
) -> str:
    """List all members of a specific group.

    Args:
        chat_id: The unique identifier of the group (required).
        page_size: Number of results per page (default 50, max 100).
        page_token: Pagination token from previous response.
    """
    if not chat_id:
        return _error_response("chat_id is required")

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        import lark_oapi as lark

        request = lark.im.v1.ChatMemberListRequest.builder().chat_id(chat_id).page_size(page_size)
        if page_token:
            request.page_token(page_token)

        response = client.im.v1.ChatMemberList(request.build())
        if not response.success():
            return _error_response(f"feishu_chat_members failed: code={response.code}, msg={response.msg}")

        data = response.data or {}
        items = []
        for item in data.get("items", []):
            items.append(
                {
                    "member_id": getattr(item, "member_id", "") or getattr(item, "open_id", ""),
                    "name": getattr(item, "name", "") or getattr(item, "member_id", ""),
                    "member_id_type": getattr(item, "member_id_type", "open_id"),
                }
            )

        result = {
            "items": items,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token", ""),
        }
        return _ok_response(result)
    except Exception as e:
        logger.error("[feishu_chat_members] error: %s", e)
        return _error_response(str(e))


@tool("feishu_chat_create", parse_docstring=True)
def feishu_chat_create(
    name: str,
    description: str = "",
    user_id_list: list[str] | None = None,
    bot_notification: bool = True,
) -> str:
    """Create a new group chat.

    Args:
        name: Name of the group (required, max 50 characters).
        description: Group description (optional).
        user_id_list: List of user IDs to add as initial members (optional).
        bot_notification: Whether to send bot join notification (default True).
    """
    if not name:
        return _error_response("name is required")

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        import lark_oapi as lark

        request = lark.im.v1.ChatCreateRequest.builder()
        request.name(name)
        request.description(description) if description else None
        request.user_id_list(user_id_list) if user_id_list else None
        request.bot_notification(bot_notification)

        response = client.im.v1.ChatCreate(request.build())
        if not response.success():
            return _error_response(f"feishu_chat_create failed: code={response.code}, msg={response.msg}")

        data = response.data
        if data is None:
            return _error_response("Failed to create group: no response data")

        result = {
            "chat_id": data.chat_id,
            "name": name,
        }
        return _ok_response(result)
    except Exception as e:
        logger.error("[feishu_chat_create] error: %s", e)
        return _error_response(str(e))
