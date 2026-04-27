import logging
from importlib import import_module
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


def _normalize_okr_data(data: Any) -> Any:
    if data is None:
        return None
    if isinstance(data, (str, int, float, bool)):
        return data
    if isinstance(data, list):
        return [_normalize_okr_data(item) for item in data]
    if isinstance(data, tuple):
        return [_normalize_okr_data(item) for item in data]
    if isinstance(data, dict):
        return {key: _normalize_okr_data(value) for key, value in data.items()}

    if hasattr(data, "__dict__"):
        normalized: dict[str, Any] = {}
        for key, value in vars(data).items():
            if key.startswith("_"):
                continue
            normalized[key] = _normalize_okr_data(value)
        if normalized:
            return normalized

    return str(data)


def _load_okr_request_class(module_name: str, class_name: str) -> type[Any]:
    module = import_module(module_name)
    return getattr(module, class_name)


def _list_user_okrs(client: Any, user_id: str, period_ids: list[str] | None = None) -> Any:
    ListUserOkrRequest = _load_okr_request_class("lark_oapi.api.okr.v1.model.list_user_okr_request", "ListUserOkrRequest")
    builder = ListUserOkrRequest.builder().user_id(user_id).user_id_type("open_id")
    if period_ids:
        builder = builder.period_ids(period_ids)
    request = builder.build()
    return client.okr.v1.user_okr.list(request)


@tool("feishu_okr_period_list", parse_docstring=True)
def feishu_okr_period_list(user_id: str | None = None) -> str:
    """List OKR periods from Feishu.

    Args:
        user_id: User ID to get periods for (optional).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    try:
        ListPeriodRequest = _load_okr_request_class("lark_oapi.api.okr.v1.model.list_period_request", "ListPeriodRequest")
        request = ListPeriodRequest.builder().build()
        response = client.okr.v1.period.list(request)
        if not response.success():
            return _error_response(f"Failed to list OKR periods: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        periods = _get_attr(data, "items", "periods") or []
        return _ok_response(
            {
                "user_id": user_id,
                "periods": _normalize_okr_data(periods),
                "count": len(periods),
            }
        )
    except Exception as e:
        logger.error("[Feishu OKR tools] failed to list periods user_id=%s: %s", user_id, e)
        return _error_response(f"Failed to list OKR periods: {str(e)}")


@tool("feishu_okr_get", parse_docstring=True)
def feishu_okr_get(user_id: str, period_id: str) -> str:
    """Get OKR data for a user in a specific period.

    Args:
        user_id: User ID (required).
        period_id: OKR period ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not user_id.strip():
        return _error_response("user_id is required.")
    if not period_id.strip():
        return _error_response("period_id is required.")

    try:
        response = _list_user_okrs(client, user_id, [period_id])
        if not response.success():
            return _error_response(f"Failed to get OKR data: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        okr_list = _get_attr(data, "okr_list", "items", "data") or []
        matched_okr = next(
            (item for item in okr_list if str(_get_attr(item, "period_id")) == period_id or str(_get_attr(item, "id", "okr_id")) == period_id),
            None,
        )
        return _ok_response(
            {
                "user_id": user_id,
                "period_id": period_id,
                "okr": _normalize_okr_data(matched_okr or okr_list or data),
            }
        )
    except Exception as e:
        logger.error("[Feishu OKR tools] failed to get OKR user_id=%s period_id=%s: %s", user_id, period_id, e)
        return _error_response(f"Failed to get OKR data: {str(e)}")


@tool("feishu_okr_progress", parse_docstring=True)
def feishu_okr_progress(user_id: str, period_ids: list[str]) -> str:
    """Get OKR progress for a user across multiple periods.

    Args:
        user_id: User ID (required).
        period_ids: List of period IDs (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available. Check channel configuration.")

    if not user_id.strip():
        return _error_response("user_id is required.")
    normalized_period_ids = [period_id.strip() for period_id in period_ids if isinstance(period_id, str) and period_id.strip()]
    if not normalized_period_ids:
        return _error_response("period_ids must be a non-empty list.")

    try:
        response = _list_user_okrs(client, user_id, normalized_period_ids)
        if not response.success():
            return _error_response(f"Failed to get OKR progress: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        progress_list = []
        for okr in _get_attr(data, "okr_list") or []:
            for objective in _get_attr(okr, "objective_list") or []:
                objective_progress = _normalize_okr_data(
                    {
                        "okr_id": _get_attr(okr, "id", "okr_id"),
                        "period_id": _get_attr(okr, "period_id"),
                        "objective_id": _get_attr(objective, "id"),
                        "objective_content": _get_attr(objective, "content"),
                        "progress_rate": _get_attr(objective, "progress_rate"),
                        "progress_report": _get_attr(objective, "progress_report"),
                        "progress_records": _get_attr(objective, "progress_record_list") or [],
                    }
                )
                progress_list.append(objective_progress)

                for kr in _get_attr(objective, "kr_list") or []:
                    progress_list.append(
                        _normalize_okr_data(
                            {
                                "okr_id": _get_attr(okr, "id", "okr_id"),
                                "period_id": _get_attr(okr, "period_id"),
                                "objective_id": _get_attr(objective, "id"),
                                "kr_id": _get_attr(kr, "id"),
                                "kr_content": _get_attr(kr, "content"),
                                "progress_rate": _get_attr(kr, "progress_rate"),
                                "progress_records": _get_attr(kr, "progress_record_list") or [],
                            }
                        )
                    )
        return _ok_response(
            {
                "user_id": user_id,
                "period_ids": normalized_period_ids,
                "progress": _normalize_okr_data(progress_list),
            }
        )
    except Exception as e:
        logger.error("[Feishu OKR tools] failed to get progress user_id=%s period_ids=%s: %s", user_id, normalized_period_ids, e)
        return _error_response(f"Failed to get OKR progress: {str(e)}")
