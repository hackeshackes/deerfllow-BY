"""
Feishu Message Tools - Read messages and files from Feishu channels.

Configuration keys (in config.yaml under channels.feishu):
    - app_id: Feishu app ID.
    - app_secret: Feishu app secret.
    - domain: (optional) API domain, defaults to https://open.feishu.cn

Requires lark-oapi package. Install with: uv add lark-oapi
"""

import json
import logging
from typing import Any

from langchain.tools import tool

from deerflow.config import get_app_config

logger = logging.getLogger(__name__)


def _get_feishu_config() -> dict[str, Any] | None:
    config = get_app_config()
    channels = config.model_config.get("channels", {})
    feishu_cfg = channels.get("feishu", {}) if isinstance(channels, dict) else None
    return feishu_cfg if isinstance(feishu_cfg, dict) else None


def _get_feishu_client():
    feishu_cfg = _get_feishu_config()
    if feishu_cfg is None:
        logger.warning("[Feishu tools] feishu channel not configured in config.yaml")
        return None

    app_id = feishu_cfg.get("app_id", "")
    app_secret = feishu_cfg.get("app_secret", "")
    domain = feishu_cfg.get("domain", "https://open.feishu.cn")

    if not app_id or not app_secret:
        logger.warning("[Feishu tools] app_id or app_secret not configured")
        return None

    try:
        import lark_oapi as lark

        client = lark.Client.builder().app_id(app_id).app_secret(app_secret).domain(domain).build()
        return client
    except ImportError:
        logger.warning("[Feishu tools] lark-oapi not installed. Install with: uv add lark-oapi")
        return None
    except Exception as e:
        logger.error("[Feishu tools] failed to create client: %s", e)
        return None


@tool("feishu_get_messages", parse_docstring=True)
def feishu_get_messages(
    chat_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    page_size: int = 20,
) -> str:
    """Retrieve message history from a Feishu chat/群组.

    Args:
        chat_id: The chat ID to retrieve messages from (required).
        start_time: Start time in ISO format (e.g. "2024-01-01T00:00:00Z"), optional.
        end_time: End time in ISO format, optional.
        page_size: Number of messages to retrieve (1-100), default 20.
    """
    client = _get_feishu_client()
    if client is None:
        return json.dumps({"error": "Feishu client not available. Check channel configuration."}, ensure_ascii=False)

    page_size = max(1, min(page_size, 100))

    try:
        from lark_oapi.api.im.v1 import ListMessageRequest

        request = ListMessageRequest.builder().receive_id_type("chat_id").request_body({"receive_id": chat_id, "container": {"type": "chat", "chat_id": chat_id}, "page_size": page_size}).build()

        if start_time:
            request.start_time = start_time
        if end_time:
            request.end_time = end_time

        response = client.im.v1.message.list(request)

        if not response.success():
            return json.dumps({"error": f"Failed to get messages: code={response.code}, msg={response.msg}"}, ensure_ascii=False)

        messages = []
        if response.data and hasattr(response.data, "items") and response.data.items:
            for msg in response.data.items:
                content = {}
                try:
                    content = json.loads(msg.content)
                except Exception:
                    pass

                messages.append(
                    {
                        "message_id": getattr(msg, "message_id", ""),
                        "msg_type": getattr(msg, "msg_type", ""),
                        "sender_id": getattr(msg, "sender", {}).get("id", "") if hasattr(msg, "sender") else "",
                        "content": content,
                        "create_time": getattr(msg, "create_time", ""),
                        "update_time": getattr(msg, "update_time", ""),
                    }
                )

        return json.dumps(
            {
                "chat_id": chat_id,
                "total": len(messages),
                "messages": messages,
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.exception("[Feishu tools] failed to get messages for chat_id=%s", chat_id)
        return json.dumps({"error": f"Failed to get messages: {str(e)}"}, ensure_ascii=False)


@tool("feishu_get_message_by_id", parse_docstring=True)
def feishu_get_message_by_id(message_id: str) -> str:
    """Retrieve a single message by its message_id from Feishu.

    Args:
        message_id: The message ID to retrieve (required).
    """
    client = _get_feishu_client()
    if client is None:
        return json.dumps({"error": "Feishu client not available. Check channel configuration."}, ensure_ascii=False)

    try:
        from lark_oapi.api.im.v1 import GetMessageRequest

        request = GetMessageRequest.builder().message_id(message_id).build()
        response = client.im.v1.message.get(request)

        if not response.success():
            return json.dumps({"error": f"Failed to get message: code={response.code}, msg={response.msg}"}, ensure_ascii=False)

        msg = response.data if hasattr(response, "data") else None
        if msg is None:
            return json.dumps({"error": "Message not found"}, ensure_ascii=False)

        content = {}
        try:
            content = json.loads(msg.content)
        except Exception:
            pass

        result = {
            "message_id": getattr(msg, "message_id", ""),
            "msg_type": getattr(msg, "msg_type", ""),
            "chat_id": getattr(msg, "chat_id", ""),
            "sender_id": getattr(msg, "sender", {}).get("id", "") if hasattr(msg, "sender") else "",
            "content": content,
            "create_time": getattr(msg, "create_time", ""),
            "update_time": getattr(msg, "update_time", ""),
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.exception("[Feishu tools] failed to get message_id=%s", message_id)
        return json.dumps({"error": f"Failed to get message: {str(e)}"}, ensure_ascii=False)


@tool("feishu_search_messages", parse_docstring=True)
def feishu_search_messages(
    query: str,
    chat_id: str | None = None,
    page_size: int = 20,
) -> str:
    """Search messages in Feishu by keyword.

    Args:
        query: Search keyword (required).
        chat_id: Filter by chat ID, optional.
        page_size: Number of results (1-50), default 20.
    """
    client = _get_feishu_client()
    if client is None:
        return json.dumps({"error": "Feishu client not available. Check channel configuration."}, ensure_ascii=False)

    page_size = max(1, min(page_size, 50))

    try:
        from lark_oapi.api.search.v1 import CreateSearchRequest

        request_body = {
            "query": query,
            "message_type": ["text", "post"],
            "page_size": page_size,
        }
        if chat_id:
            request_body["chat_ids"] = [chat_id]

        request = CreateSearchRequest.builder().request_body(request_body).build()
        response = client.search.v1.message.create(request)

        if not response.success():
            return json.dumps({"error": f"Failed to search messages: code={response.code}, msg={response.msg}"}, ensure_ascii=False)

        results = []
        if response.data and hasattr(response.data, "messages") and response.data.messages:
            for msg in response.data.messages:
                content = {}
                try:
                    content = json.loads(msg.content)
                except Exception:
                    pass

                results.append(
                    {
                        "message_id": getattr(msg, "message_id", ""),
                        "chat_id": getattr(msg, "chat_id", ""),
                        "sender_id": getattr(msg, "sender_id", ""),
                        "content": content,
                        "create_time": getattr(msg, "create_time", ""),
                    }
                )

        return json.dumps(
            {
                "query": query,
                "total": len(results),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.exception("[Feishu tools] failed to search messages query=%s", query)
        return json.dumps({"error": f"Failed to search messages: {str(e)}"}, ensure_ascii=False)
