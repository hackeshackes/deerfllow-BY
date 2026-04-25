import logging
from importlib import import_module

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)

QueryUserStatsDataRequest = import_module("lark_oapi.api.attendance.v1.model.query_user_stats_data_request").QueryUserStatsDataRequest
QueryUserStatsDataRequestBody = import_module("lark_oapi.api.attendance.v1.model.query_user_stats_data_request_body").QueryUserStatsDataRequestBody
GetGroupRequest = import_module("lark_oapi.api.attendance.v1.model.get_group_request").GetGroupRequest


def _normalize_attendance_date(value: str) -> int:
    return int(value.replace("-", ""))


@tool("feishu_attendance_record", parse_docstring=True)
def feishu_attendance_record(user_id: str, start_date: str, end_date: str) -> str:
    """Get attendance records for a user.

    Args:
        user_id: User ID (required).
        start_date: Start date in format "2024-01-01" (required).
        end_date: End date in format "2024-01-31" (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        request = (
            QueryUserStatsDataRequest.builder()
            .employee_type("employee_id")
            .request_body(
                QueryUserStatsDataRequestBody.builder()
                .user_id(user_id)
                .start_date(_normalize_attendance_date(start_date))
                .end_date(_normalize_attendance_date(end_date))
                .build()
            )
            .build()
        )
        user_stats_service = getattr(client.attendance.v1, "user_stats_data", None)
        if user_stats_service is None:
            return _error_response("Feishu attendance service user_stats_data is not available")

        request_method = getattr(user_stats_service, "query", None) or getattr(user_stats_service, "get", None) or getattr(user_stats_service, "list", None)
        if request_method is None:
            return _error_response("Feishu attendance service user_stats_data does not support query/get/list requests")

        response = request_method(request)
        if not response.success():
            return _error_response(f"Failed to get attendance records: code={response.code}, msg={response.msg}")

        return _ok_response(
            {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "data": getattr(response, "data", None),
            }
        )
    except Exception as e:
        logger.error("[feishu_attendance_record] error user_id=%s start_date=%s end_date=%s: %s", user_id, start_date, end_date, e)
        return _error_response(str(e))


@tool("feishu_attendance_group", parse_docstring=True)
def feishu_attendance_group(group_id: str) -> str:
    """Get attendance group info.

    Args:
        group_id: Attendance group ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        request = GetGroupRequest.builder().group_id(group_id).build()
        response = client.attendance.v1.group.get(request)
        if not response.success():
            return _error_response(f"Failed to get attendance group: code={response.code}, msg={response.msg}")

        return _ok_response(
            {
                "group_id": group_id,
                "data": getattr(response, "data", None),
            }
        )
    except Exception as e:
        logger.error("[feishu_attendance_group] error group_id=%s: %s", group_id, e)
        return _error_response(str(e))
