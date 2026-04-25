import logging
from importlib import import_module
from typing import Any

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _response_error(response: Any, action: str) -> str | None:
    if response is None:
        return f"Feishu client not available. Failed to {action}."
    if not response.success():
        return f"Failed to {action}: code={getattr(response, 'code', '?')}, msg={getattr(response, 'msg', '?')}"
    return None


def _load_attr(module_name: str, attr_name: str) -> Any:
    return getattr(import_module(module_name), attr_name)


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _normalize_table(table: Any) -> dict[str, Any]:
    return {
        "table_id": _get_attr(table, "table_id", "id"),
        "name": _get_attr(table, "name"),
    }


def _normalize_record(record: Any) -> dict[str, Any]:
    return {
        "record_id": _get_attr(record, "record_id", "id"),
        "fields": _get_attr(record, "fields") or {},
        "created_time": _get_attr(record, "created_time"),
        "last_modified_time": _get_attr(record, "last_modified_time"),
    }


@tool("feishu_bitable_read", parse_docstring=True)
def feishu_bitable_read(bitable_id: str, table_id: str | None = None, record_count: int = 100) -> str:
    """Read data from a Feishu multi-dimensional table (bitable).

    Args:
        bitable_id: The bitable ID (required).
        table_id: The table ID within the bitable (optional, reads first table if not provided).
        record_count: Number of records to read (1-500, default 100).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    record_count = max(1, min(record_count, 500))

    try:
        GetAppRequest = _load_attr("lark_oapi.api.bitable.v1.model.get_app_request", "GetAppRequest")
        ListAppTableRecordRequest = _load_attr("lark_oapi.api.bitable.v1.model.list_app_table_record_request", "ListAppTableRecordRequest")
        ListAppTableRequest = _load_attr("lark_oapi.api.bitable.v1.model.list_app_table_request", "ListAppTableRequest")

        app_resp = client.bitable.v1.app.get(GetAppRequest.builder().app_token(bitable_id).build())
        app_error = _response_error(app_resp, f"get bitable app info for {bitable_id}")
        if app_error:
            return _error_response(app_error)

        tables_resp = client.bitable.v1.app_table.list(ListAppTableRequest.builder().app_token(bitable_id).build())
        tables_error = _response_error(tables_resp, f"list bitable tables for {bitable_id}")
        if tables_error:
            return _error_response(tables_error)

        table_items = _get_attr(getattr(tables_resp, "data", None), "items") or []
        tables = [_normalize_table(item) for item in table_items]

        if not tables:
            return _error_response("No tables found in bitable.")

        selected_table_id = table_id or tables[0]["table_id"]
        if not selected_table_id:
            return _error_response("Table ID could not be determined.")

        if table_id and not any(table.get("table_id") == table_id for table in tables):
            return _error_response(f"Table not found in bitable: {table_id}")

        records_resp = client.bitable.v1.app_table_record.list(
            ListAppTableRecordRequest.builder().app_token(bitable_id).table_id(selected_table_id).page_size(record_count).build()
        )
        records_error = _response_error(records_resp, f"list bitable records for {bitable_id}/{selected_table_id}")
        if records_error:
            return _error_response(records_error)

        record_items = _get_attr(getattr(records_resp, "data", None), "items") or []
        records = [_normalize_record(item) for item in record_items]

        app_data = getattr(app_resp, "data", None)
        app_name = _get_attr(app_data, "name", "app_name")
        if app_name is None:
            app = _get_attr(app_data, "app")
            app_name = _get_attr(app, "name", "app_name")

        return _ok_response(
            {
                "bitable_id": bitable_id,
                "app_name": app_name,
                "selected_table_id": selected_table_id,
                "tables": tables,
                "records": records,
            }
        )
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to read bitable_id=%s table_id=%s: %s", bitable_id, table_id, e)
        return _error_response(f"Failed to read bitable: {str(e)}")


@tool("feishu_bitable_write", parse_docstring=True)
def feishu_bitable_write(bitable_id: str, table_id: str, action: str, records: list[dict]) -> str:
    """Write data to a Feishu multi-dimensional table (bitable).

    Args:
        bitable_id: The bitable ID (required).
        table_id: The table ID within the bitable (required).
        action: Action to perform - "create", "update", or "delete" (required).
        records: List of record data to write (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    normalized_action = action.lower().strip()
    if normalized_action not in {"create", "update", "delete"}:
        return _error_response("Invalid action. Must be one of: create, update, delete.")

    if not isinstance(records, list) or not records:
        return _error_response("records must be a non-empty list.")

    try:
        BatchCreateAppTableRecordRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.batch_create_app_table_record_request", "BatchCreateAppTableRecordRequest"
        )
        BatchCreateAppTableRecordRequestBody = _load_attr(
            "lark_oapi.api.bitable.v1.model.batch_create_app_table_record_request_body", "BatchCreateAppTableRecordRequestBody"
        )
        BatchDeleteAppTableRecordRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.batch_delete_app_table_record_request", "BatchDeleteAppTableRecordRequest"
        )
        BatchDeleteAppTableRecordRequestBody = _load_attr(
            "lark_oapi.api.bitable.v1.model.batch_delete_app_table_record_request_body", "BatchDeleteAppTableRecordRequestBody"
        )
        BatchUpdateAppTableRecordRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.batch_update_app_table_record_request", "BatchUpdateAppTableRecordRequest"
        )
        BatchUpdateAppTableRecordRequestBody = _load_attr(
            "lark_oapi.api.bitable.v1.model.batch_update_app_table_record_request_body", "BatchUpdateAppTableRecordRequestBody"
        )

        if normalized_action == "create":
            body = BatchCreateAppTableRecordRequestBody.builder().records(records).build()
            response = client.bitable.v1.app_table_record.batch_create(
                BatchCreateAppTableRecordRequest.builder().app_token(bitable_id).table_id(table_id).request_body(body).build()
            )
        elif normalized_action == "update":
            body = BatchUpdateAppTableRecordRequestBody.builder().records(records).build()
            response = client.bitable.v1.app_table_record.batch_update(
                BatchUpdateAppTableRecordRequest.builder().app_token(bitable_id).table_id(table_id).request_body(body).build()
            )
        else:
            body = BatchDeleteAppTableRecordRequestBody.builder().records(records).build()
            response = client.bitable.v1.app_table_record.batch_delete(
                BatchDeleteAppTableRecordRequest.builder().app_token(bitable_id).table_id(table_id).request_body(body).build()
            )

        response_error = _response_error(response, f"{normalized_action} bitable records for {bitable_id}/{table_id}")
        if response_error:
            return _error_response(response_error)

        return _ok_response(
            {
                "bitable_id": bitable_id,
                "table_id": table_id,
                "action": normalized_action,
                "record_count": len(records),
                "result": getattr(response, "data", None),
            }
        )
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to %s bitable_id=%s table_id=%s: %s", normalized_action, bitable_id, table_id, e)
        return _error_response(f"Failed to write bitable: {str(e)}")


@tool("feishu_bitable_record_create", parse_docstring=True)
def feishu_bitable_record_create(bitable_id: str, table_id: str, fields: dict) -> str:
    """Create a single record in a Feishu bitable table.

    Args:
        bitable_id: The bitable ID (required).
        table_id: The table ID within the bitable (required).
        fields: Fields data as dict {field_name: value} (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not bitable_id.strip():
        return _error_response("bitable_id is required.")
    if not table_id.strip():
        return _error_response("table_id is required.")
    if not fields:
        return _error_response("fields is required and must not be empty.")

    try:
        CreateAppTableRecordRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.create_app_table_record_request", "CreateAppTableRecordRequest"
        )
        CreateAppTableRecordRequestBody = _load_attr(
            "lark_oapi.api.bitable.v1.model.create_app_table_record_request_body", "CreateAppTableRecordRequestBody"
        )
        body = CreateAppTableRecordRequestBody.builder().fields(fields).build()
        request = CreateAppTableRecordRequest.builder().app_token(bitable_id).table_id(table_id).request_body(body).build()
        response = client.bitable.v1.app_table_record.create(request)

        response_error = _response_error(response, f"create record in {bitable_id}/{table_id}")
        if response_error:
            return _error_response(response_error)

        data = getattr(response, "data", None)
        return _ok_response({
            "bitable_id": bitable_id,
            "table_id": table_id,
            "record_id": _get_attr(data, "record_id"),
            "fields": fields,
        })
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to create record bitable_id=%s table_id=%s: %s", bitable_id, table_id, e)
        return _error_response(f"Failed to create record: {str(e)}")


@tool("feishu_bitable_record_update", parse_docstring=True)
def feishu_bitable_record_update(bitable_id: str, table_id: str, record_id: str, fields: dict) -> str:
    """Update a single record in a Feishu bitable table.

    Args:
        bitable_id: The bitable ID (required).
        table_id: The table ID within the bitable (required).
        record_id: The record ID to update (required).
        fields: Fields data as dict {field_name: value} (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not bitable_id.strip():
        return _error_response("bitable_id is required.")
    if not table_id.strip():
        return _error_response("table_id is required.")
    if not record_id.strip():
        return _error_response("record_id is required.")
    if not fields:
        return _error_response("fields is required and must not be empty.")

    try:
        UpdateAppTableRecordRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.update_app_table_record_request", "UpdateAppTableRecordRequest"
        )
        UpdateAppTableRecordRequestBody = _load_attr(
            "lark_oapi.api.bitable.v1.model.update_app_table_record_request_body", "UpdateAppTableRecordRequestBody"
        )
        body = UpdateAppTableRecordRequestBody.builder().fields(fields).build()
        request = UpdateAppTableRecordRequest.builder().app_token(bitable_id).table_id(table_id).record_id(record_id).request_body(body).build()
        response = client.bitable.v1.app_table_record.update(request)

        response_error = _response_error(response, f"update record {record_id} in {bitable_id}/{table_id}")
        if response_error:
            return _error_response(response_error)

        return _ok_response({
            "bitable_id": bitable_id,
            "table_id": table_id,
            "record_id": record_id,
            "fields": fields,
            "updated": True,
        })
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to update record bitable_id=%s table_id=%s record_id=%s: %s", bitable_id, table_id, record_id, e)
        return _error_response(f"Failed to update record: {str(e)}")


@tool("feishu_bitable_record_delete", parse_docstring=True)
def feishu_bitable_record_delete(bitable_id: str, table_id: str, record_id: str) -> str:
    """Delete a single record from a Feishu bitable table.

    Args:
        bitable_id: The bitable ID (required).
        table_id: The table ID within the bitable (required).
        record_id: The record ID to delete (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not bitable_id.strip():
        return _error_response("bitable_id is required.")
    if not table_id.strip():
        return _error_response("table_id is required.")
    if not record_id.strip():
        return _error_response("record_id is required.")

    try:
        DeleteAppTableRecordRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.delete_app_table_record_request", "DeleteAppTableRecordRequest"
        )
        request = DeleteAppTableRecordRequest.builder().app_token(bitable_id).table_id(table_id).record_id(record_id).build()
        response = client.bitable.v1.app_table_record.delete(request)

        response_error = _response_error(response, f"delete record {record_id} from {bitable_id}/{table_id}")
        if response_error:
            return _error_response(response_error)

        return _ok_response({
            "bitable_id": bitable_id,
            "table_id": table_id,
            "record_id": record_id,
            "deleted": True,
        })
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to delete record bitable_id=%s table_id=%s record_id=%s: %s", bitable_id, table_id, record_id, e)
        return _error_response(f"Failed to delete record: {str(e)}")


@tool("feishu_bitable_table_list", parse_docstring=True)
def feishu_bitable_table_list(bitable_id: str) -> str:
    """List all tables in a Feishu bitable.

    Args:
        bitable_id: The bitable ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not bitable_id.strip():
        return _error_response("bitable_id is required.")

    try:
        ListAppTableRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.list_app_table_request", "ListAppTableRequest"
        )
        request = ListAppTableRequest.builder().app_token(bitable_id).build()
        response = client.bitable.v1.app_table.list(request)

        response_error = _response_error(response, f"list tables for {bitable_id}")
        if response_error:
            return _error_response(response_error)

        items = _get_attr(getattr(response, "data", None), "items") or []
        tables = [_normalize_table(item) for item in items]
        return _ok_response({
            "bitable_id": bitable_id,
            "tables": tables,
        })
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to list tables bitable_id=%s: %s", bitable_id, e)
        return _error_response(f"Failed to list tables: {str(e)}")


@tool("feishu_bitable_field_list", parse_docstring=True)
def feishu_bitable_field_list(bitable_id: str, table_id: str) -> str:
    """List all fields in a Feishu bitable table.

    Args:
        bitable_id: The bitable ID (required).
        table_id: The table ID within the bitable (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not bitable_id.strip():
        return _error_response("bitable_id is required.")
    if not table_id.strip():
        return _error_response("table_id is required.")

    try:
        ListAppTableFieldRequest = _load_attr(
            "lark_oapi.api.bitable.v1.model.list_app_table_field_request", "ListAppTableFieldRequest"
        )
        request = ListAppTableFieldRequest.builder().app_token(bitable_id).table_id(table_id).build()
        response = client.bitable.v1.app_table_field.list(request)

        response_error = _response_error(response, f"list fields for {bitable_id}/{table_id}")
        if response_error:
            return _error_response(response_error)

        items = _get_attr(getattr(response, "data", None), "items") or []
        fields = [{"field_id": _get_attr(item, "field_id", "id"), "field_name": _get_attr(item, "field_name", "name"), "type": _get_attr(item, "type")} for item in items]
        return _ok_response({
            "bitable_id": bitable_id,
            "table_id": table_id,
            "fields": fields,
        })
    except Exception as e:
        logger.error("[Feishu bitable tools] failed to list fields bitable_id=%s table_id=%s: %s", bitable_id, table_id, e)
        return _error_response(f"Failed to list fields: {str(e)}")
