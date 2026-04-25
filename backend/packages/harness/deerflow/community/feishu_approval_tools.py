import logging
from importlib import import_module

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _get_attr(data, *names: str):
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _extract_instance_tasks(data) -> list:
    tasks = _get_attr(data, "task_list", "tasks", "task_infos", "items") or []
    if isinstance(tasks, list):
        return tasks
    return []


def _extract_task_id(data) -> str | None:
    for task in _extract_instance_tasks(data):
        task_id = _get_attr(task, "task_id", "id")
        if task_id:
            return str(task_id)
    return None


@tool("feishu_approval_list", parse_docstring=True)
def feishu_approval_list(user_id_type: str = "open_id") -> str:
    """List approval instances from Feishu.

    Args:
        user_id_type: ID type - "open_id", "union_id", "user_id" (default "open_id").
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    normalized_user_id_type = user_id_type.strip()
    if normalized_user_id_type not in {"open_id", "union_id", "user_id"}:
        return _error_response('Invalid user_id_type. Must be one of: "open_id", "union_id", "user_id".')

    try:
        ListInstanceRequest = import_module("lark_oapi.api.approval.v4.model.list_instance_request").ListInstanceRequest

        request_builder = ListInstanceRequest.builder()
        if hasattr(request_builder, "user_id_type"):
            request_builder = request_builder.user_id_type(normalized_user_id_type)
        request = request_builder.build()
        if not hasattr(request_builder, "user_id_type"):
            request.add_query("user_id_type", normalized_user_id_type)
        response = client.approval.v4.instance.list(request)
        if not response.success():
            return _error_response(f"Failed to list approval instances: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "user_id_type": normalized_user_id_type,
                "instances": _get_attr(data, "items", "instance_list") or [],
                "page_token": _get_attr(data, "page_token"),
                "has_more": bool(_get_attr(data, "has_more")),
            }
        )
    except Exception as e:
        logger.error("[Feishu approval tools] failed to list approval instances: %s", e)
        return _error_response(f"Failed to list approval instances: {str(e)}")


@tool("feishu_approval_get", parse_docstring=True)
def feishu_approval_get(instance_id: str) -> str:
    """Get details of an approval instance.

    Args:
        instance_id: Approval instance ID (required).
    """
    if not instance_id.strip():
        return _error_response("instance_id is required.")

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        GetInstanceRequest = import_module("lark_oapi.api.approval.v4.model.get_instance_request").GetInstanceRequest

        request = GetInstanceRequest.builder().instance_id(instance_id).build()
        response = client.approval.v4.instance.get(request)
        if not response.success():
            return _error_response(f"Failed to get approval instance: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "instance_id": instance_id,
                "instance": data,
                "task_id": _extract_task_id(data),
            }
        )
    except Exception as e:
        logger.error("[Feishu approval tools] failed to get approval instance %s: %s", instance_id, e)
        return _error_response(f"Failed to get approval instance: {str(e)}")


@tool("feishu_approval_action", parse_docstring=True)
def feishu_approval_action(instance_id: str, action: str, comment: str | None = None) -> str:
    """Take action on an approval instance.

    Args:
        instance_id: Approval instance ID (required).
        action: Action to take - "approve", "reject", or "transfer" (required).
        comment: Comment for the action (optional).
    """
    if not instance_id.strip():
        return _error_response("instance_id is required.")

    normalized_action = action.strip().lower()
    if normalized_action not in {"approve", "reject", "transfer"}:
        return _error_response('Invalid action. Must be one of: "approve", "reject", "transfer".')

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        ApproveTaskRequest = import_module("lark_oapi.api.approval.v4.model.approve_task_request").ApproveTaskRequest
        GetInstanceRequest = import_module("lark_oapi.api.approval.v4.model.get_instance_request").GetInstanceRequest
        RejectTaskRequest = import_module("lark_oapi.api.approval.v4.model.reject_task_request").RejectTaskRequest
        TaskApprove = import_module("lark_oapi.api.approval.v4.model.task_approve").TaskApprove

        get_request = GetInstanceRequest.builder().instance_id(instance_id).build()
        instance_response = client.approval.v4.instance.get(get_request)
        if not instance_response.success():
            return _error_response(f"Failed to get approval instance: code={instance_response.code}, msg={instance_response.msg}")

        instance_data = getattr(instance_response, "data", None)
        task_id = _extract_task_id(instance_data)
        if not task_id:
            return _error_response("No task_id found for the approval instance.")

        method = getattr(client.approval.v4.task, normalized_action, None)
        if method is None:
            return _error_response(f"Feishu client does not support action: {normalized_action}")

        normalized_comment = comment or ""
        if normalized_action == "approve":
            body = TaskApprove.builder().instance_code(instance_id).task_id(task_id).comment(normalized_comment).build()
            request = ApproveTaskRequest.builder().request_body(body).build()
        elif normalized_action == "reject":
            body = TaskApprove.builder().instance_code(instance_id).task_id(task_id).comment(normalized_comment).build()
            request = RejectTaskRequest.builder().request_body(body).build()
        else:
            return _error_response("Transfer action requires transfer target user information, which this tool does not currently collect.")

        response = method(request)
        if not response.success():
            return _error_response(f"Failed to {normalized_action} approval instance: code={response.code}, msg={response.msg}")

        return _ok_response(
            {
                "instance_id": instance_id,
                "action": normalized_action,
                "task_id": task_id,
                "comment": comment,
                "result": getattr(response, "data", None),
            }
        )
    except Exception as e:
        logger.error("[Feishu approval tools] failed to %s approval instance %s: %s", normalized_action, instance_id, e)
        return _error_response(f"Failed to {normalized_action} approval instance: {str(e)}")
