import logging
from datetime import datetime
from importlib import import_module
from typing import Any

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _import_sdk_attr(module_name: str, attr_name: str) -> Any:
    return getattr(import_module(module_name), attr_name)


def _import_sdk_attr_optional(module_name: str, attr_name: str) -> Any | None:
    try:
        return _import_sdk_attr(module_name, attr_name)
    except (ImportError, AttributeError, ModuleNotFoundError):
        return None


def _builder_set(instance: Any, field: str, value: Any) -> Any:
    setter = getattr(instance, field, None)
    if callable(setter):
        updated = setter(value)
        return updated if updated is not None else instance
    setattr(instance, field, value)
    return instance


def _build_list_task_request(user_id: str | None, status: str | None) -> Any:
    request = _import_sdk_attr("lark_oapi.api.task.v1.model.list_task_request", "ListTaskRequest").builder()
    if user_id and hasattr(request, "user_id"):
        request = _builder_set(request, "user_id", user_id)

    if status:
        if hasattr(request, "status"):
            request = _builder_set(request, "status", status)
        elif hasattr(request, "task_completed"):
            if status == "completed":
                request = _builder_set(request, "task_completed", True)
            elif status == "open":
                request = _builder_set(request, "task_completed", False)

    return request.build()


def _build_create_task_request(title: str, due: str | None, user_id: str | None) -> Any:
    create_request_cls = _import_sdk_attr("lark_oapi.api.task.v1.model.create_task_request", "CreateTaskRequest")
    create_body_cls = _import_sdk_attr_optional("lark_oapi.api.task.v1.model.create_task_request_body", "CreateTaskRequestBody") or _import_sdk_attr("lark_oapi.api.task.v1.model.task", "Task")

    body_data: dict[str, Any] = {
        "summary": title.strip(),
        "origin": {
            "platform_i18n_name": '{"zh_cn":"DeerFlow","en_us":"DeerFlow"}',
        },
    }

    if due:
        body_data["due"] = {
            "time": _parse_due_to_timestamp(due),
            "timezone": "UTC",
            "is_all_day": False,
        }
    if user_id:
        body_data["collaborator_ids"] = [user_id]

    request_body = _build_sdk_model(create_body_cls, **body_data)
    request_builder = create_request_cls.builder()
    if hasattr(request_builder, "body"):
        request_builder = _builder_set(request_builder, "body", request_body)
    else:
        request_builder = _builder_set(request_builder, "request_body", request_body)
    return request_builder.build()


def _build_patch_task_request(task_guid: str) -> Any:
    patch_request_cls = _import_sdk_attr("lark_oapi.api.task.v1.model.patch_task_request", "PatchTaskRequest")
    patch_body_cls = _import_sdk_attr_optional("lark_oapi.api.task.v1.model.patch_task_request_body", "PatchTaskRequestBody") or _import_sdk_attr("lark_oapi.api.task.v1.model.patch_task_request", "PatchTaskRequestBody")

    request_body = _build_sdk_model(
        patch_body_cls,
        task={"status": "completed"},
        update_fields=["status"],
    )

    request_builder = patch_request_cls.builder()
    if hasattr(request_builder, "task_guid"):
        request_builder = _builder_set(request_builder, "task_guid", task_guid)
    else:
        request_builder = _builder_set(request_builder, "task_id", task_guid)

    if hasattr(request_builder, "body"):
        request_builder = _builder_set(request_builder, "body", request_body)
    else:
        request_builder = _builder_set(request_builder, "request_body", request_body)
    return request_builder.build()


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _normalize_task(task: Any) -> dict[str, Any]:
    due = _get_attr(task, "due")
    collaborators = _get_attr(task, "collaborators") or []
    followers = _get_attr(task, "followers") or []

    return {
        "task_guid": _get_attr(task, "guid", "task_guid", "id"),
        "summary": _get_attr(task, "summary", "title"),
        "description": _get_attr(task, "description"),
        "status": _get_attr(task, "status"),
        "completed_at": _get_attr(task, "completed_at", "complete_time"),
        "due": {
            "time": _get_attr(due, "time"),
            "timezone": _get_attr(due, "timezone"),
            "is_all_day": _get_attr(due, "is_all_day"),
        }
        if due
        else None,
        "user_ids": _get_attr(task, "user_ids", "collaborator_ids") or [_get_attr(item, "id") for item in collaborators if _get_attr(item, "id")],
        "follower_ids": _get_attr(task, "follower_ids") or [_get_attr(item, "id") for item in followers if _get_attr(item, "id")],
        "created_at": _get_attr(task, "created_at", "create_time"),
        "updated_at": _get_attr(task, "updated_at", "update_time"),
    }


def _parse_due_to_timestamp(due: str) -> str:
    normalized_due = due.strip()
    if normalized_due.endswith("Z"):
        normalized_due = normalized_due[:-1] + "+00:00"
    return str(int(datetime.fromisoformat(normalized_due).timestamp()))


def _build_sdk_model(model_cls: type[Any], **kwargs: Any) -> Any:
    try:
        return model_cls(**kwargs)
    except TypeError:
        pass

    builder = getattr(model_cls, "builder", None)
    if callable(builder):
        instance = builder()
        for key, value in kwargs.items():
            setter = getattr(instance, key, None)
            if callable(setter):
                instance = setter(value)
        build = getattr(instance, "build", None)
        if callable(build):
            return build()

    if len(kwargs) == 1:
        try:
            return model_cls(next(iter(kwargs.values())))
        except TypeError:
            pass

    raise TypeError(f"Unable to construct SDK model: {model_cls}")


@tool("feishu_task_list", parse_docstring=True)
def feishu_task_list(user_id: str | None = None, status: str | None = None) -> str:
    """List tasks from Feishu.

    Args:
        user_id: Filter by user ID (optional).
        status: Filter by status - "open", "completed", "cancelled" (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if status:
        normalized_status = status.strip().lower()
        if normalized_status not in {"open", "completed", "cancelled"}:
            return _error_response("Invalid status. Must be one of: open, completed, cancelled.")
        status = normalized_status

    try:
        request = _build_list_task_request(user_id, status)
        response = client.task.v1.task.list(request)
        if not response.success():
            return _error_response(f"Failed to list tasks: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        items = _get_attr(data, "items") or []
        tasks = [_normalize_task(item) for item in items]

        return _ok_response(
            {
                "count": len(tasks),
                "tasks": tasks,
            }
        )
    except Exception as e:
        logger.error("[Feishu task tools] failed to list tasks user_id=%s status=%s: %s", user_id, status, e)
        return _error_response(f"Failed to list tasks: {str(e)}")


@tool("feishu_task_add", parse_docstring=True)
def feishu_task_add(title: str, due: str | None = None, user_id: str | None = None) -> str:
    """Add a task in Feishu.

    Args:
        title: Task title (required).
        due: Due date in ISO format like "2024-12-31T23:59:59Z" (optional).
        user_id: User ID to assign task to (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not title.strip():
        return _error_response("title is required.")

    try:
        request = _build_create_task_request(title, due, user_id)
        response = client.task.v1.task.create(request)
        if not response.success():
            return _error_response(f"Failed to add task: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        task = _get_attr(data, "task") or data
        return _ok_response(_normalize_task(task))
    except ValueError as e:
        logger.error("[Feishu task tools] invalid due=%s: %s", due, e)
        return _error_response(f"Invalid due datetime: {str(e)}")
    except Exception as e:
        logger.error("[Feishu task tools] failed to add task title=%s user_id=%s: %s", title, user_id, e)
        return _error_response(f"Failed to add task: {str(e)}")


@tool("feishu_task_complete", parse_docstring=True)
def feishu_task_complete(task_guid: str) -> str:
    """Mark a Feishu task as completed.

    Args:
        task_guid: The task GUID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not task_guid.strip():
        return _error_response("task_guid is required.")

    try:
        request = _build_patch_task_request(task_guid)
        response = client.task.v1.task.patch(request)
        if not response.success():
            return _error_response(f"Failed to complete task: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        task = _get_attr(data, "task") or data
        return _ok_response(_normalize_task(task) if task else {"task_guid": task_guid, "status": "completed"})
    except Exception as e:
        logger.error("[Feishu task tools] failed to complete task_guid=%s: %s", task_guid, e)
        return _error_response(f"Failed to complete task: {str(e)}")


@tool("feishu_task_update", parse_docstring=True)
def feishu_task_update(task_guid: str, title: str | None = None, due: str | None = None) -> str:
    """Update a Feishu task.

    Args:
        task_guid: The task GUID (required).
        title: New task title (optional).
        due: New due date in ISO format (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not task_guid.strip():
        return _error_response("task_guid is required.")

    if not title and not due:
        return _error_response("At least one of title or due must be provided")

    try:
        update_fields = []
        task_data = {}

        if title:
            task_data["summary"] = title.strip()
            update_fields.append("summary")
        if due:
            task_data["due"] = {
                "time": _parse_due_to_timestamp(due),
                "timezone": "UTC",
                "is_all_day": False,
            }
            update_fields.append("due")

        patch_request_cls = _import_sdk_attr("lark_oapi.api.task.v1.model.patch_task_request", "PatchTaskRequest")
        patch_body_cls = _import_sdk_attr("lark_oapi.api.task.v1.model.task", "Task")

        task_obj = _build_sdk_model(patch_body_cls, **task_data)
        request_body = _build_sdk_model(patch_body_cls, task=task_obj, update_fields=update_fields)

        request_builder = patch_request_cls.builder()
        request_builder = _builder_set(request_builder, "task_guid", task_guid)
        if hasattr(request_builder, "body"):
            request_builder = _builder_set(request_builder, "body", request_body)
        else:
            request_builder = _builder_set(request_builder, "request_body", request_body)
        request = request_builder.build()

        response = client.task.v1.task.patch(request)
        if not response.success():
            return _error_response(f"Failed to update task: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        task = _get_attr(data, "task") or data
        return _ok_response(_normalize_task(task) if task else {"task_guid": task_guid})
    except Exception as e:
        logger.error("[Feishu task tools] failed to update task_guid=%s: %s", task_guid, e)
        return _error_response(f"Failed to update task: {str(e)}")


@tool("feishu_task_delete", parse_docstring=True)
def feishu_task_delete(task_guid: str) -> str:
    """Delete a Feishu task.

    Args:
        task_guid: The task GUID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not task_guid.strip():
        return _error_response("task_guid is required.")

    try:
        delete_request_cls = _import_sdk_attr("lark_oapi.api.task.v1.model.delete_task_request", "DeleteTaskRequest")
        request_builder = delete_request_cls.builder()
        if hasattr(request_builder, "task_guid"):
            request_builder = _builder_set(request_builder, "task_guid", task_guid)
        else:
            request_builder = _builder_set(request_builder, "task_id", task_guid)
        request = request_builder.build()

        response = client.task.v1.task.delete(request)
        if not response.success():
            return _error_response(f"Failed to delete task: code={response.code}, msg={response.msg}")

        return _ok_response({"task_guid": task_guid, "deleted": True})
    except Exception as e:
        logger.error("[Feishu task tools] failed to delete task_guid=%s: %s", task_guid, e)
        return _error_response(f"Failed to delete task: {str(e)}")


@tool("feishu_task_get", parse_docstring=True)
def feishu_task_get(task_guid: str) -> str:
    """Get a task by GUID from Feishu.

    Args:
        task_guid: The task GUID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not task_guid.strip():
        return _error_response("task_guid is required.")

    try:
        get_request_cls = _import_sdk_attr("lark_oapi.api.task.v1.model.get_task_request", "GetTaskRequest")
        request_builder = get_request_cls.builder()
        if hasattr(request_builder, "task_guid"):
            request_builder = _builder_set(request_builder, "task_guid", task_guid)
        else:
            request_builder = _builder_set(request_builder, "task_id", task_guid)
        request = request_builder.build()
        response = client.task.v1.task.get(request)
        if not response.success():
            return _error_response(f"Failed to get task: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        task = _get_attr(data, "task") or data
        return _ok_response(_normalize_task(task) if task else {"task_guid": task_guid})
    except Exception as e:
        logger.error("[Feishu task tools] failed to get task_guid=%s: %s", task_guid, e)
        return _error_response(f"Failed to get task: {str(e)}")
