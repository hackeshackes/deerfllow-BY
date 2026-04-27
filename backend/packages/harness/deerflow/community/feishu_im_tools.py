import base64
import importlib
import json
import logging

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)

_SUPPORTED_MESSAGE_TYPES = {"text", "post", "image", "file"}
_SUPPORTED_FILE_TYPES = {"file", "image", "audio", "video"}


def _get_feishu_im_request_models():
    module = importlib.import_module("lark_oapi.api.im.v1")
    return module.CreateMessageRequest, module.CreateMessageRequestBody, module.GetMessageResourceRequest


def _build_message_content(content: str, msg_type: str) -> str:
    if msg_type == "text":
        return json.dumps({"text": content}, ensure_ascii=False)
    if msg_type == "post":
        return json.dumps(
            {"zh_cn": {"title": "Message", "content": [[{"tag": "text", "text": content}]]}},
            ensure_ascii=False,
        )

    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            return json.dumps(payload, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    key_name = "image_key" if msg_type == "image" else "file_key"
    return json.dumps({key_name: content}, ensure_ascii=False)


@tool("feishu_send_message", parse_docstring=True)
def feishu_send_message(chat_id: str, content: str, msg_type: str = "text") -> str:
    """Send a message in Feishu.

    Args:
        chat_id: Chat ID to send to (required).
        content: Message content (required).
        msg_type: Message type - "text", "post", "image", "file" (default "text").
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not chat_id:
        return _error_response("chat_id is required")
    if not content:
        return _error_response("content is required")
    if msg_type not in _SUPPORTED_MESSAGE_TYPES:
        return _error_response("msg_type must be one of: text, post, image, file")

    try:
        CreateMessageRequest, CreateMessageRequestBody, _ = _get_feishu_im_request_models()
        body = CreateMessageRequestBody.builder().receive_id(chat_id).msg_type(msg_type).content(_build_message_content(content, msg_type)).build()
        request = CreateMessageRequest.builder().receive_id_type("chat_id").request_body(body).build()
        response = client.im.v1.message.create(request)

        if not response.success():
            return _error_response(f"Failed to send message: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "chat_id": chat_id,
                "msg_type": msg_type,
                "message_id": getattr(data, "message_id", "") if data else "",
                "root_id": getattr(data, "root_id", "") if data else "",
                "parent_id": getattr(data, "parent_id", "") if data else "",
            }
        )
    except Exception as e:
        logger.error("[Feishu tools] failed to send message to chat_id=%s: %s", chat_id, e)
        return _error_response(f"Failed to send message: {e}")


@tool("feishu_download_file", parse_docstring=True)
def feishu_download_file(message_id: str, file_key: str, file_type: str) -> str:
    """Download a file from Feishu message.

    Args:
        message_id: Message ID containing the file (required).
        file_key: File key from the message (required).
        file_type: File type - "file", "image", "audio", "video" (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not message_id:
        return _error_response("message_id is required")
    if not file_key:
        return _error_response("file_key is required")
    if file_type not in _SUPPORTED_FILE_TYPES:
        return _error_response("file_type must be one of: file, image, audio, video")

    try:
        _, _, GetMessageResourceRequest = _get_feishu_im_request_models()
        request = GetMessageResourceRequest.builder().message_id(message_id).file_key(file_key).type(file_type).build()
        response = client.im.v1.message_resource.get(request)

        if not response.success():
            return _error_response(f"Failed to download file: code={response.code}, msg={response.msg}")

        file_bytes = None
        if hasattr(response, "file") and response.file is not None:
            file_bytes = response.file
        elif hasattr(response, "raw") and getattr(response.raw, "content", None) is not None:
            file_bytes = response.raw.content

        result = {
            "message_id": message_id,
            "file_key": file_key,
            "file_type": file_type,
            "file_name": getattr(response, "file_name", "") or getattr(getattr(response, "data", None), "file_name", ""),
            "content_type": getattr(response, "content_type", "") or getattr(getattr(response, "raw", None), "headers", {}).get("Content-Type", ""),
            "download_url": getattr(response, "download_url", "") or getattr(getattr(response, "data", None), "download_url", ""),
        }
        if file_bytes is not None:
            result["content_base64"] = base64.b64encode(file_bytes).decode("utf-8")

        return _ok_response(result)
    except Exception as e:
        logger.error("[Feishu tools] failed to download file message_id=%s file_key=%s: %s", message_id, file_key, e)
        return _error_response(f"Failed to download file: {e}")


@tool("feishu_message_get", parse_docstring=True)
def feishu_message_get(message_id: str) -> str:
    """Get a message by ID from Feishu.

    Args:
        message_id: The message ID to retrieve (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not message_id.strip():
        return _error_response("message_id is required")

    try:
        GetMessageRequest = importlib.import_module("lark_oapi.api.im.v1.model.get_message_request").GetMessageRequest
        request = GetMessageRequest.builder().message_id(message_id).build()
        response = client.im.v1.message.get(request)

        if not response.success():
            return _error_response(f"Failed to get message: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "message_id": message_id,
                "msg_type": getattr(data, "msg_type", ""),
                "content": getattr(data, "body", {}).get("content", "") if hasattr(getattr(data, "body", None), "get") else getattr(data, "content", ""),
                "create_time": getattr(data, "create_time", ""),
                "sender": {
                    "id": getattr(data, "sender", {}).get("id", "") if isinstance(getattr(data, "sender", None), dict) else getattr(getattr(data, "sender", None), "id", ""),
                    "type": getattr(data, "sender", {}).get("type", "") if isinstance(getattr(data, "sender", None), dict) else getattr(getattr(data, "sender", None), "type", ""),
                },
            }
        )
    except Exception as e:
        logger.error("[Feishu tools] failed to get message message_id=%s: %s", message_id, e)
        return _error_response(f"Failed to get message: {e}")
