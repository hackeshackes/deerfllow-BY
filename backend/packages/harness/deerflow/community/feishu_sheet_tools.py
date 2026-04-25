import logging
from typing import Any

import httpx
from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


def _get_attr(data: Any, *names: str) -> Any:
    for name in names:
        if "." in name:
            current = data
            for part in name.split("."):
                current = _get_attr(current, part)
                if current is None:
                    break
            if current is not None:
                return current
        if isinstance(data, dict) and name in data:
            return data[name]
        if hasattr(data, name):
            return getattr(data, name)
    return None


def _normalize_range(sheet_id: str, range_value: str) -> str:
    normalized_range = range_value.strip()
    if "!" in normalized_range:
        return normalized_range
    return f"{sheet_id}!{normalized_range}"


def _get_tenant_token(client) -> str | None:
    try:
        from lark_oapi.core.token.manager import TokenManager
        return TokenManager.get_self_tenant_token(client._config)
    except Exception as e:
        logger.error("[Feishu sheet] failed to get tenant token: %s", e)
        return None


def _sheets_values_get(client, spreadsheet_token: str, range: str) -> dict[str, Any]:
    token = _get_tenant_token(client)
    if not token:
        return {"error": "Failed to get access token"}

    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("[Feishu sheet] values get failed: %s", e)
        return {"error": str(e)}


def _sheets_values_put(client, spreadsheet_token: str, sheet_id: str, range: str, values: list[list]) -> dict[str, Any]:
    token = _get_tenant_token(client)
    if not token:
        return {"error": "Failed to get access token"}

    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    full_range = f"{sheet_id}!{range}" if "!" not in range else range
    payload = {"valueRange": {"range": full_range, "values": values}}
    try:
        resp = httpx.put(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("[Feishu sheet] values put failed: %s", e)
        return {"error": str(e)}


@tool("feishu_sheet_read", parse_docstring=True)
def feishu_sheet_read(spreadsheet_token: str, sheet_id: str) -> str:
    """Read data from a Feishu spreadsheet.

    Args:
        spreadsheet_token: Spreadsheet token (required).
        sheet_id: Sheet ID within the spreadsheet (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not spreadsheet_token.strip():
        return _error_response("spreadsheet_token is required.")
    if not sheet_id.strip():
        return _error_response("sheet_id is required.")

    try:
        result = _sheets_values_get(client, spreadsheet_token, sheet_id)
        if "error" in result:
            return _error_response(f"Failed to read sheet values: {result['error']}")

        data = result.get("data", {})
        value_range = data.get("valueRange", {})

        return _ok_response(
            {
                "spreadsheet_token": spreadsheet_token,
                "sheet_id": sheet_id,
                "range": value_range.get("range"),
                "revision": data.get("revision"),
                "values": value_range.get("values") or [],
            }
        )
    except Exception as e:
        logger.error("[Feishu sheet tools] failed to read spreadsheet_token=%s sheet_id=%s: %s", spreadsheet_token, sheet_id, e)
        return _error_response(f"Failed to read sheet: {str(e)}")


@tool("feishu_sheet_write", parse_docstring=True)
def feishu_sheet_write(spreadsheet_token: str, sheet_id: str, range: str, values: list[list]) -> str:
    """Write data to a Feishu spreadsheet.

    Args:
        spreadsheet_token: Spreadsheet token (required).
        sheet_id: Sheet ID within the spreadsheet (required).
        range: Cell range to write to like "A1:C10" (required).
        values: 2D array of values to write (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not spreadsheet_token.strip():
        return _error_response("spreadsheet_token is required.")
    if not sheet_id.strip():
        return _error_response("sheet_id is required.")
    if not range.strip():
        return _error_response("range is required.")
    if not isinstance(values, list) or not values:
        return _error_response("values must be a non-empty 2D array.")

    try:
        result = _sheets_values_put(client, spreadsheet_token, sheet_id, range, values)
        if "error" in result:
            return _error_response(f"Failed to write sheet values: {result['error']}")

        data = result.get("data", {})
        return _ok_response(
            {
                "spreadsheet_token": spreadsheet_token,
                "sheet_id": sheet_id,
                "range": data.get("updatedRange"),
                "updated_rows": data.get("updatedRows"),
                "updated_columns": data.get("updatedColumns"),
                "updated_cells": data.get("updatedCells"),
                "revision": data.get("revision"),
            }
        )
    except Exception as e:
        logger.error("[Feishu sheet tools] failed to write spreadsheet_token=%s sheet_id=%s range=%s: %s", spreadsheet_token, sheet_id, range, e)
        return _error_response(f"Failed to write sheet: {str(e)}")


@tool("feishu_sheet_range", parse_docstring=True)
def feishu_sheet_range(spreadsheet_token: str, sheet_id: str, range: str) -> str:
    """Read a specific range from a Feishu spreadsheet.

    Args:
        spreadsheet_token: Spreadsheet token (required).
        sheet_id: Sheet ID within the spreadsheet (required).
        range: Cell range to read like "A1:C10" (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not spreadsheet_token.strip():
        return _error_response("spreadsheet_token is required.")
    if not sheet_id.strip():
        return _error_response("sheet_id is required.")
    if not range.strip():
        return _error_response("range is required.")

    try:
        full_range = _normalize_range(sheet_id, range)
        result = _sheets_values_get(client, spreadsheet_token, full_range)
        if "error" in result:
            return _error_response(f"Failed to read sheet range: {result['error']}")

        data = result.get("data", {})
        value_range = data.get("valueRange", {})
        return _ok_response(
            {
                "spreadsheet_token": spreadsheet_token,
                "sheet_id": sheet_id,
                "range": value_range.get("range") or full_range,
                "revision": data.get("revision"),
                "values": value_range.get("values") or [],
            }
        )
    except Exception as e:
        logger.error("[Feishu sheet tools] failed to read range spreadsheet_token=%s sheet_id=%s range=%s: %s", spreadsheet_token, sheet_id, range, e)
        return _error_response(f"Failed to read sheet range: {str(e)}")


@tool("feishu_sheet_create", parse_docstring=True)
def feishu_sheet_create(folder_token: str, title: str) -> str:
    """Create a new Feishu spreadsheet.

    Args:
        folder_token: The folder token to create spreadsheet in (required).
        title: Spreadsheet title (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not folder_token.strip():
        return _error_response("folder_token is required.")
    if not title.strip():
        return _error_response("title is required.")

    try:
        import lark_oapi as lark

        payload = {"title": title, "type": "sheet"}
        request = (
            lark.BaseRequest.builder()
            .http_method(lark.HttpMethod.POST)
            .uri(f"/open-apis/drive/explorer/v2/file/{folder_token}")
            .body(payload)
            .token_types({lark.AccessTokenType.TENANT})
            .build()
        )
        resp = client.request(request)
        if not resp.success():
            return _error_response(f"Failed to create spreadsheet: code={resp.code}, msg={resp.msg}")

        import json
        raw_data = json.loads(resp.raw.content)
        data = raw_data.get("data", {})
        spreadsheet_token = data.get("token", "")
        url = data.get("url", "")

        token = _get_tenant_token(client)
        if not token:
            return _error_response("Failed to get access token for reading sheet metadata.")

        meta_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
        meta_resp = httpx.get(meta_url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        sheets = []
        if meta_resp.status_code == 200:
            meta_data = meta_resp.json().get("data", {})
            sheets = meta_data.get("sheets", [])
        default_sheet_id = sheets[0].get("sheetId", "") if sheets else ""

        return _ok_response(
            {
                "spreadsheet_token": spreadsheet_token,
                "url": url,
                "sheet_id": default_sheet_id,
                "title": title,
            }
        )
    except Exception as e:
        logger.error("[Feishu sheet tools] failed to create spreadsheet: %s", e)
        return _error_response(f"Failed to create spreadsheet: {str(e)}")