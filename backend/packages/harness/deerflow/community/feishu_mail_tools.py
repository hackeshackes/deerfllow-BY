import logging
from typing import Any

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple | set):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if hasattr(value, "__dict__"):
        return {key: _serialize_value(item) for key, item in vars(value).items() if not key.startswith("_") and not callable(item)}
    return str(value)


@tool("feishu_mail_list", parse_docstring=True)
def feishu_mail_list(user_mailbox_id: str, folder_id: str = "INBOX", page_size: int = 20) -> str:
    """List emails from Feishu mailbox.

    Args:
        user_mailbox_id: User mailbox ID (required).
        folder_id: Folder ID - "INBOX" or "SENT" (default "INBOX").
        page_size: Number of emails to return (1-50, default 20).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not user_mailbox_id.strip():
        return _error_response("user_mailbox_id is required")
    if not 1 <= page_size <= 50:
        return _error_response("page_size must be between 1 and 50")

    try:
        from lark_oapi.api.mail.v1.model.list_user_mailbox_message_request import ListUserMailboxMessageRequest

        request = ListUserMailboxMessageRequest.builder().user_mailbox_id(user_mailbox_id).folder_id(folder_id).page_size(page_size).build()
        response = client.mail.v1.user_mailbox_message.list(request)
        if not response.success():
            return _error_response(f"Failed to list emails: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        messages = _get_attr(data, "items", "messages", "message_list") or []
        return _ok_response(
            {
                "user_mailbox_id": user_mailbox_id,
                "folder_id": folder_id,
                "page_size": page_size,
                "has_more": _get_attr(data, "has_more"),
                "page_token": _get_attr(data, "page_token"),
                "messages": [_serialize_value(item) for item in messages],
            }
        )
    except Exception as e:
        logger.error("[feishu_mail_list] error: %s", e)
        return _error_response(f"Failed to list emails: {e}")


@tool("feishu_mail_get", parse_docstring=True)
def feishu_mail_get(user_mailbox_id: str, message_id: str) -> str:
    """Get email content from Feishu.

    Args:
        user_mailbox_id: User mailbox ID (required).
        message_id: Email message ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not user_mailbox_id.strip():
        return _error_response("user_mailbox_id is required")
    if not message_id.strip():
        return _error_response("message_id is required")

    try:
        from lark_oapi.api.mail.v1.model.get_user_mailbox_message_request import GetUserMailboxMessageRequest

        request = GetUserMailboxMessageRequest.builder().user_mailbox_id(user_mailbox_id).message_id(message_id).build()
        response = client.mail.v1.user_mailbox_message.get(request)
        if not response.success():
            return _error_response(f"Failed to get email: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "user_mailbox_id": user_mailbox_id,
                "message_id": message_id,
                "message": _serialize_value(_get_attr(data, "message") or data),
            }
        )
    except Exception as e:
        logger.error("[feishu_mail_get] error user_mailbox_id=%s message_id=%s: %s", user_mailbox_id, message_id, e)
        return _error_response(f"Failed to get email: {e}")


@tool("feishu_mail_send", parse_docstring=True)
def feishu_mail_send(user_mailbox_id: str, to: list[str], subject: str, content: str, cc: list[str] | None = None) -> str:
    """Send an email via Feishu.

    Args:
        user_mailbox_id: User mailbox ID (required).
        to: List of recipient email addresses (required).
        subject: Email subject (required).
        content: Email body content (required).
        cc: List of CC email addresses (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    recipients = [email.strip() for email in to if email and email.strip()]
    cc_recipients = [email.strip() for email in (cc or []) if email and email.strip()]
    normalized_subject = subject.strip()

    if not user_mailbox_id.strip():
        return _error_response("user_mailbox_id is required")
    if not recipients:
        return _error_response("to must be a non-empty list")
    if not normalized_subject:
        return _error_response("subject is required")
    if not content.strip():
        return _error_response("content is required")

    try:
        from lark_oapi.api.mail.v1.model.mail_address import MailAddress
        from lark_oapi.api.mail.v1.model.send_user_mailbox_message_request import SendUserMailboxMessageRequest
        from lark_oapi.api.mail.v1.model.send_user_mailbox_message_request_body import SendUserMailboxMessageRequestBody

        to_addresses = [MailAddress(email=addr) for addr in recipients]
        cc_addresses = [MailAddress(email=addr) for addr in cc_recipients] if cc_recipients else None

        body = SendUserMailboxMessageRequestBody.builder().subject(normalized_subject).to(to_addresses).body_plain_text(content)
        if cc_addresses:
            body = body.cc(cc_addresses)
        body = body.build()

        request = SendUserMailboxMessageRequest.builder().user_mailbox_id(user_mailbox_id).request_body(body).build()
        response = client.mail.v1.user_mailbox_message.send(request)
        if not response.success():
            return _error_response(f"Failed to send email: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "user_mailbox_id": user_mailbox_id,
                "to": recipients,
                "cc": cc_recipients,
                "subject": normalized_subject,
                "message": _serialize_value(_get_attr(data, "message") or data),
            }
        )
    except Exception as e:
        logger.error("[feishu_mail_send] error user_mailbox_id=%s to=%s cc=%s: %s", user_mailbox_id, recipients, cc_recipients, e)
        return _error_response(f"Failed to send email: {e}")


@tool("feishu_mail_create_draft", parse_docstring=True)
def feishu_mail_create_draft(user_mailbox_id: str, to: list[str], subject: str, content: str, cc: list[str] | None = None) -> str:
    """Create a mail draft in Feishu.

    Args:
        user_mailbox_id: User mailbox ID (required).
        to: List of recipient emails (required).
        subject: Email subject (required).
        content: Email body content (required).
        cc: List of CC emails (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    recipients = [email.strip() for email in to if email and email.strip()]
    cc_recipients = [email.strip() for email in (cc or []) if email and email.strip()]

    if not user_mailbox_id.strip():
        return _error_response("user_mailbox_id is required")
    if not recipients:
        return _error_response("to must be a non-empty list")
    if not subject.strip():
        return _error_response("subject is required")

    try:
        payload = {
            "subject": subject.strip(),
            "to": recipients,
        }
        if cc_recipients:
            payload["cc"] = cc_recipients
        if content.strip():
            payload["body_plain_text"] = content.strip()

        resp = client.http.post(
            f"/open-apis/mail/v1/user_mailbox/{user_mailbox_id}/drafts",
            payload,
        )
        if not resp.success():
            return _error_response(f"Failed to create draft: code={resp.code}, msg={resp.msg}")

        data = getattr(resp, "data", None) or {}
        return _ok_response(
            {
                "user_mailbox_id": user_mailbox_id,
                "draft_id": _get_attr(data, "draft_id") or _get_attr(data, "id"),
                "subject": subject.strip(),
                "to": recipients,
                "cc": cc_recipients,
            }
        )
    except Exception as e:
        logger.error("[feishu_mail_create_draft] error user_mailbox_id=%s: %s", user_mailbox_id, e)
        return _error_response(f"Failed to create draft: {e}")
