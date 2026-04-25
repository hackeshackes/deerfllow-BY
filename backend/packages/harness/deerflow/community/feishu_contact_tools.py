import logging
from typing import Any

from langchain.tools import tool
from lark_oapi.api.contact.v3.model.batch_get_id_user_request import BatchGetIdUserRequest  # pyright: ignore[reportMissingImports]
from lark_oapi.api.contact.v3.model.get_department_request import GetDepartmentRequest  # pyright: ignore[reportMissingImports]
from lark_oapi.api.contact.v3.model.get_user_request import GetUserRequest  # pyright: ignore[reportMissingImports]

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


@tool("feishu_contact_user", parse_docstring=True)
def feishu_contact_user(user_id: str | None = None, email: str | None = None) -> str:
    """Get user info from Feishu address book.

    Args:
        user_id: User ID (open_id or union_id) (optional if email provided).
        email: User email (optional if user_id provided).
    """
    if not user_id and not email:
        return _error_response("Either user_id or email must be provided.")

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        resolved_user_id = user_id

        if not resolved_user_id and email:
            id_request = BatchGetIdUserRequest.builder().user_id_type("open_id").emails([email]).build()
            id_response = client.contact.v3.user.batch_get_id(id_request)
            if not id_response.success():
                return _error_response(f"Failed to get user ID: code={id_response.code}, msg={id_response.msg}")

            user_list = _get_attr(getattr(id_response, "data", None), "user_list") or []
            if not user_list:
                return _error_response(f"User not found for email: {email}")

            resolved_user_id = _get_attr(user_list[0], "user_id", "open_id")
            if not resolved_user_id:
                return _error_response(f"User ID not found for email: {email}")

        request = GetUserRequest.builder().user_id(resolved_user_id).user_id_type("open_id").build()
        response = client.contact.v3.user.get(request)
        if not response.success():
            return _error_response(f"Failed to get user info: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        user = _get_attr(data, "user") or data
        return _ok_response(
            {
                "user_id": resolved_user_id,
                "email": email or _get_attr(user, "email"),
                "user": user,
            }
        )
    except Exception as e:
        logger.error("[Feishu contact tools] failed to get user user_id=%s email=%s: %s", user_id, email, e)
        return _error_response(f"Failed to get user info: {str(e)}")


@tool("feishu_contact_dept", parse_docstring=True)
def feishu_contact_dept(department_id: str) -> str:
    """Get department info from Feishu.

    Args:
        department_id: Department ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        request = GetDepartmentRequest.builder().department_id(department_id).user_id_type("open_id").build()
        response = client.contact.v3.department.get(request)
        if not response.success():
            return _error_response(f"Failed to get department info: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        department = _get_attr(data, "department") or data
        return _ok_response(
            {
                "department_id": department_id,
                "department": department,
            }
        )
    except Exception as e:
        logger.error("[Feishu contact tools] failed to get department department_id=%s: %s", department_id, e)
        return _error_response(f"Failed to get department info: {str(e)}")
