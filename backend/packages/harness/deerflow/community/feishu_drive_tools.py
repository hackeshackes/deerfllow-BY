import importlib
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


def _to_jsonable(data: Any) -> Any:
    if data is None or isinstance(data, str | int | float | bool):
        return data
    if isinstance(data, list | tuple | set):
        return [_to_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {str(key): _to_jsonable(value) for key, value in data.items()}

    result: dict[str, Any] = {}
    for name in dir(data):
        if name.startswith("_"):
            continue
        try:
            value = getattr(data, name)
        except Exception:
            continue
        if callable(value):
            continue
        result[name] = _to_jsonable(value)

    return result or str(data)


def _normalize_file(file_data: Any) -> dict[str, Any]:
    return {
        "token": _get_attr(file_data, "token", "file_token"),
        "name": _get_attr(file_data, "name"),
        "type": _get_attr(file_data, "type"),
        "parent_token": _get_attr(file_data, "parent_token", "folder_token"),
        "url": _get_attr(file_data, "url"),
        "size": _get_attr(file_data, "size"),
        "owner_id": _get_attr(file_data, "owner_id"),
        "create_time": _get_attr(file_data, "create_time"),
        "modified_time": _get_attr(file_data, "modified_time", "update_time"),
    }


def _load_drive_model(module_name: str, class_name: str) -> Any:
    module = importlib.import_module(f"lark_oapi.api.drive.v1.model.{module_name}")
    return getattr(module, class_name)


@tool("feishu_drive_file_list", parse_docstring=True)
def feishu_drive_file_list(folder_token: str | None = None, page_size: int = 50) -> str:
    """List files in Feishu drive or a specific folder.

    Args:
        folder_token: Folder token to list within (optional, root folder if not provided).
        page_size: Number of files to return (1-100, default 50).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    page_size = max(1, min(page_size, 100))

    try:
        ListFileRequest = _load_drive_model("list_file_request", "ListFileRequest")
        request = ListFileRequest.builder().folder_token(folder_token or "").page_size(page_size).build()
        response = client.drive.v1.file.list(request)
        if not response.success():
            return _error_response(f"Failed to list drive files: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        files = _get_attr(data, "files", "items") or []
        return _ok_response(
            {
                "folder_token": folder_token,
                "page_size": page_size,
                "has_more": _get_attr(data, "has_more"),
                "next_page_token": _get_attr(data, "next_page_token", "page_token"),
                "files": [_normalize_file(file_data) for file_data in files],
            }
        )
    except Exception as e:
        logger.error("[feishu_drive_file_list] error: %s", e)
        return _error_response(f"Failed to list drive files: {str(e)}")


@tool("feishu_drive_file_meta", parse_docstring=True)
def feishu_drive_file_meta(file_token: str) -> str:
    """Get metadata for a Feishu drive file.

    Args:
        file_token: File token (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not file_token.strip():
        return _error_response("file_token is required.")

    try:
        BatchQueryMetaRequest = _load_drive_model("batch_query_meta_request", "BatchQueryMetaRequest")
        MetaRequest = _load_drive_model("meta_request", "MetaRequest")
        RequestDoc = _load_drive_model("request_doc", "RequestDoc")
        request = (
            BatchQueryMetaRequest.builder()
            .request_body(
                MetaRequest.builder()
                .request_docs([RequestDoc.builder().doc_token(file_token).doc_type("file").build()])
                .with_url(True)
                .build()
            )
            .build()
        )
        response = client.drive.v1.meta.batch_query(request)
        if not response.success():
            return _error_response(f"Failed to get drive file metadata: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        metas = _get_attr(data, "metas") or []
        file_data = _get_attr(data, "file", "data") or (metas[0] if metas else data)
        return _ok_response(
            {
                "file_token": file_token,
                "file": _to_jsonable(file_data),
            }
        )
    except Exception as e:
        logger.error("[feishu_drive_file_meta] error: %s", e)
        return _error_response(f"Failed to get drive file metadata: {str(e)}")


@tool("feishu_drive_file_download", parse_docstring=True)
def feishu_drive_file_download(file_token: str) -> str:
    """Download a Feishu drive file.

    Args:
        file_token: File token (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not file_token.strip():
        return _error_response("file_token is required.")

    try:
        DownloadFileRequest = _load_drive_model("download_file_request", "DownloadFileRequest")
        request = DownloadFileRequest.builder().file_token(file_token).build()
        response = client.drive.v1.file.download(request)
        if not response.success():
            return _error_response(f"Failed to download drive file: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "file_token": file_token,
                "download_url": _get_attr(data, "download_url", "url"),
                "expire_time": _get_attr(data, "expire_time", "expiration_time"),
                "file_name": _get_attr(data, "file_name", "name"),
                "raw": _to_jsonable(data),
            }
        )
    except Exception as e:
        logger.error("[feishu_drive_file_download] error: %s", e)
        return _error_response(f"Failed to download drive file: {str(e)}")


@tool("feishu_drive_create_folder", parse_docstring=True)
def feishu_drive_create_folder(folder_token: str, name: str) -> str:
    """Create a folder in Feishu drive.

    Args:
        folder_token: Parent folder token (required).
        name: Folder name (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not folder_token.strip():
        return _error_response("folder_token is required")
    if not name.strip():
        return _error_response("name is required")

    try:
        CreateFolderFileRequest = _load_drive_model("create_folder_file_request", "CreateFolderFileRequest")
        CreateFolderFileRequestBody = _load_drive_model("create_folder_file_request_body", "CreateFolderFileRequestBody")

        body = CreateFolderFileRequestBody.builder().folder_token(folder_token).name(name).build()
        request = CreateFolderFileRequest.builder().request_body(body).build()
        response = client.drive.v1.file.create_folder(request)
        if not response.success():
            return _error_response(f"Failed to create folder: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "token": _get_attr(data, "token", "file_token"),
                "name": _get_attr(data, "name"),
                "parent_token": folder_token,
            }
        )
    except Exception as e:
        logger.error("[feishu_drive_create_folder] error: %s", e)
        return _error_response(f"Failed to create folder: {str(e)}")


@tool("feishu_drive_file_upload", parse_docstring=True)
def feishu_drive_file_upload(folder_token: str, file_name: str, content_base64: str) -> str:
    """Upload a file to Feishu drive.

    Args:
        folder_token: Parent folder token (required).
        file_name: Name for the uploaded file (required).
        content_base64: File content as base64 encoded string (required).
    """
    import base64
    import io

    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not folder_token.strip():
        return _error_response("folder_token is required")
    if not file_name.strip():
        return _error_response("file_name is required")
    if not content_base64.strip():
        return _error_response("content_base64 is required")

    try:
        file_content = base64.b64decode(content_base64)
        file_size = len(file_content)
        file_io = io.BytesIO(file_content)

        UploadAllFileRequest = _load_drive_model("upload_all_file_request", "UploadAllFileRequest")
        UploadAllFileRequestBody = _load_drive_model("upload_all_file_request_body", "UploadAllFileRequestBody")

        body = (
            UploadAllFileRequestBody.builder()
            .file_name(file_name)
            .parent_type("file")
            .parent_node(folder_token)
            .size(file_size)
            .file(file_io)
            .build()
        )
        request = UploadAllFileRequest.builder().request_body(body).build()
        response = client.drive.v1.file.upload_all(request)
        if not response.success():
            return _error_response(f"Failed to upload file: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        return _ok_response(
            {
                "file_token": _get_attr(data, "file_token", "token"),
                "file_name": file_name,
                "parent_token": folder_token,
            }
        )
    except Exception as e:
        logger.error("[feishu_drive_file_upload] error: %s", e)
        return _error_response(f"Failed to upload file: {str(e)}")


@tool("feishu_drive_file_delete", parse_docstring=True)
def feishu_drive_file_delete(file_token: str, file_type: str = "file") -> str:
    """Delete a file in Feishu drive.

    Args:
        file_token: The file token to delete (required).
        file_type: File type - "file", "docx", "bitable", "folder", "sheet" (default "file").
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not file_token.strip():
        return _error_response("file_token is required")

    valid_types = {"file", "docx", "bitable", "folder", "sheet", "doc"}
    if file_type not in valid_types:
        return _error_response(f"file_type must be one of: {', '.join(valid_types)}")

    try:
        DeleteFileRequest = _load_drive_model("delete_file_request", "DeleteFileRequest")
        request = DeleteFileRequest.builder().file_token(file_token).type(file_type).build()
        response = client.drive.v1.file.delete(request)
        if not response.success():
            return _error_response(f"Failed to delete file: code={response.code}, msg={response.msg}")

        return _ok_response({"file_token": file_token, "file_type": file_type, "deleted": True})
    except Exception as e:
        logger.error("[feishu_drive_file_delete] error: %s", e)
        return _error_response(f"Failed to delete file: {str(e)}")


@tool("feishu_drive_file_move", parse_docstring=True)
def feishu_drive_file_move(file_token: str, folder_token: str, file_type: str = "file") -> str:
    """Move a file to a different folder in Feishu drive.

    Args:
        file_token: The file token to move (required).
        folder_token: Target folder token (required).
        file_type: File type - "file", "docx", "bitable", "folder", "sheet" (default "file").
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not file_token.strip():
        return _error_response("file_token is required")
    if not folder_token.strip():
        return _error_response("folder_token is required")

    valid_types = {"file", "docx", "bitable", "folder", "sheet", "doc"}
    if file_type not in valid_types:
        return _error_response(f"file_type must be one of: {', '.join(valid_types)}")

    try:
        MoveFileRequest = _load_drive_model("move_file_request", "MoveFileRequest")
        MoveFileRequestBody = _load_drive_model("move_file_request_body", "MoveFileRequestBody")
        body = MoveFileRequestBody.builder().folder_token(folder_token).type(file_type).build()
        request = MoveFileRequest.builder().file_token(file_token).request_body(body).build()
        response = client.drive.v1.file.move(request)
        if not response.success():
            return _error_response(f"Failed to move file: code={response.code}, msg={response.msg}")

        return _ok_response({"file_token": file_token, "folder_token": folder_token, "file_type": file_type, "moved": True})
    except Exception as e:
        logger.error("[feishu_drive_file_move] error: %s", e)
        return _error_response(f"Failed to move file: {str(e)}")


@tool("feishu_drive_file_copy", parse_docstring=True)
def feishu_drive_file_copy(file_token: str, folder_token: str, name: str | None = None, file_type: str = "file") -> str:
    """Copy a file to a different folder in Feishu drive.

    Args:
        file_token: The file token to copy (required).
        folder_token: Target folder token (required).
        name: New file name (optional, keeps original name if not provided).
        file_type: File type - "file", "docx", "bitable", "folder", "sheet" (default "file").
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not file_token.strip():
        return _error_response("file_token is required")
    if not folder_token.strip():
        return _error_response("folder_token is required")

    valid_types = {"file", "docx", "bitable", "folder", "sheet", "doc"}
    if file_type not in valid_types:
        return _error_response(f"file_type must be one of: {', '.join(valid_types)}")

    try:
        CopyFileRequest = _load_drive_model("copy_file_request", "CopyFileRequest")
        CopyFileRequestBody = _load_drive_model("copy_file_request_body", "CopyFileRequestBody")
        builder = CopyFileRequestBody.builder().folder_token(folder_token).type(file_type)
        if name:
            builder = builder.name(name)
        body = builder.build()
        request = CopyFileRequest.builder().file_token(file_token).request_body(body).build()
        response = client.drive.v1.file.copy(request)
        if not response.success():
            return _error_response(f"Failed to copy file: code={response.code}, msg={response.msg}")

        data = getattr(response, "data", None)
        new_file = _get_attr(data, "file") or data
        return _ok_response({
            "file_token": file_token,
            "folder_token": folder_token,
            "file_type": file_type,
            "copied": True,
            "new_file": _to_jsonable(new_file) if new_file else None,
        })
    except Exception as e:
        logger.error("[feishu_drive_file_copy] error: %s", e)
        return _error_response(f"Failed to copy file: {str(e)}")
