"""Upload router for handling file uploads."""

import logging
import os
import stat
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.gateway.auth import require_user
from app.gateway.deps import get_checkpointer, get_store
from app.gateway.ownership import (
    attach_owner_metadata,
    require_thread_manage_access,
    require_thread_read_access,
)
from deerflow.config.paths import get_paths
from deerflow.sandbox.sandbox_provider import get_sandbox_provider
from deerflow.uploads.manager import (
    DangerousFileTypeError,
    PathTraversalError,
    delete_file_safe,
    enrich_file_listing,
    ensure_uploads_dir,
    get_uploads_dir,
    list_files_in_dir,
    normalize_filename,
    upload_artifact_url,
    upload_virtual_path,
    validate_upload_extension,
)
from deerflow.utils.file_conversion import CONVERTIBLE_EXTENSIONS, convert_file_to_markdown

logger = logging.getLogger(__name__)


async def _auto_create_thread(request: Request, thread_id: str) -> None:
    """Create a thread in the Store if it doesn't exist.

    This is used by the upload endpoint to auto-create threads for new conversations.
    """
    try:
        from langgraph.checkpoint.base import empty_checkpoint

        store = get_store(request)
        checkpointer = get_checkpointer(request)
        user = require_user(request)

        if store is None:
            logger.warning("Store not available, cannot auto-create thread")
            return

        # Check if thread already exists
        existing = await store.aget(("threads",), thread_id)
        if existing is not None:
            return

        now = time.time()
        metadata = attach_owner_metadata({"visibility": "private"}, user)

        # Create thread record in Store
        thread_record = {
            "thread_id": thread_id,
            "status": "idle",
            "created_at": now,
            "updated_at": now,
            "metadata": metadata,
        }
        await store.aput(("threads",), thread_id, thread_record)

        # Create checkpoint
        if checkpointer is not None:
            config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
            ckpt_metadata = {
                "step": -1,
                "source": "input",
                "writes": None,
                "parents": {},
                **metadata,
                "created_at": now,
            }
            try:
                await checkpointer.aput(config, empty_checkpoint(), ckpt_metadata, {})
            except Exception:
                logger.debug("Failed to create checkpoint for auto-created thread %s", thread_id)

        logger.info("Auto-created thread %s for file upload", thread_id)
    except Exception:
        logger.exception("Failed to auto-create thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to create thread")


router = APIRouter(prefix="/api/threads/{thread_id}/uploads", tags=["uploads"])

# Max upload size in bytes (default 10MB)
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("DEER_FLOW_MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024


def _validate_file_size(content: bytes, filename: str) -> None:
    """Validate file size is within limits.

    Raises:
        HTTPException: 413 if file is too large
    """
    size = len(content)
    if size > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File '{filename}' is too large. Maximum size: {max_mb}MB (got {size // (1024 * 1024)}MB)",
        )


class UploadResponse(BaseModel):
    """Response model for file upload."""

    success: bool
    files: list[dict[str, str]]
    message: str


def _make_file_sandbox_writable(file_path: os.PathLike[str] | str) -> None:
    """Ensure uploaded files remain writable when mounted into non-local sandboxes.

    In AIO sandbox mode, the gateway writes the authoritative host-side file
    first, then the sandbox runtime may rewrite the same mounted path. Granting
    world-writable access here prevents permission mismatches between the
    gateway user and the sandbox runtime user.
    """
    file_stat = os.lstat(file_path)
    if stat.S_ISLNK(file_stat.st_mode):
        logger.warning("Skipping sandbox chmod for symlinked upload path: %s", file_path)
        return

    writable_mode = stat.S_IMODE(file_stat.st_mode) | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    chmod_kwargs = {"follow_symlinks": False} if os.chmod in os.supports_follow_symlinks else {}
    os.chmod(file_path, writable_mode, **chmod_kwargs)


@router.post("", response_model=UploadResponse)
async def upload_files(
    thread_id: str,
    request: Request = None,
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    """Upload multiple files to a thread's uploads directory."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Auto-create thread if it doesn't exist (for new conversation uploads)
    try:
        await require_thread_manage_access(request, thread_id)
    except HTTPException as e:
        if e.status_code == 404:
            # Thread doesn't exist - create it automatically
            await _auto_create_thread(request, thread_id)
        else:
            raise

    try:
        uploads_dir = ensure_uploads_dir(thread_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    sandbox_uploads = get_paths().sandbox_uploads_dir(thread_id)
    uploaded_files = []

    sandbox_provider = get_sandbox_provider()
    sandbox_id = sandbox_provider.acquire(thread_id)
    sandbox = sandbox_provider.get(sandbox_id)

    for file in files:
        if not file.filename:
            continue

        try:
            safe_filename = normalize_filename(file.filename)
        except ValueError:
            logger.warning(f"Skipping file with unsafe filename: {file.filename!r}")
            continue

        try:
            validate_upload_extension(safe_filename)
        except DangerousFileTypeError as exc:
            logger.warning(f"Rejecting upload of dangerous file type: {safe_filename!r} ({exc})")
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed: {Path(safe_filename).suffix}",
            )

        try:
            content = await file.read()
            _validate_file_size(content, safe_filename)
            file_path = uploads_dir / safe_filename
            file_path.write_bytes(content)

            virtual_path = upload_virtual_path(safe_filename)

            if sandbox_id != "local":
                _make_file_sandbox_writable(file_path)
                sandbox.update_file(virtual_path, content)

            file_info = {
                "filename": safe_filename,
                "size": str(len(content)),
                "path": str(sandbox_uploads / safe_filename),
                "virtual_path": virtual_path,
                "artifact_url": upload_artifact_url(thread_id, safe_filename),
            }

            logger.info(f"Saved file: {safe_filename} ({len(content)} bytes) to {file_info['path']}")

            file_ext = file_path.suffix.lower()
            if file_ext in CONVERTIBLE_EXTENSIONS:
                md_path = await convert_file_to_markdown(file_path)
                if md_path:
                    md_virtual_path = upload_virtual_path(md_path.name)

                    if sandbox_id != "local":
                        _make_file_sandbox_writable(md_path)
                        sandbox.update_file(md_virtual_path, md_path.read_bytes())

                    file_info["markdown_file"] = md_path.name
                    file_info["markdown_path"] = str(sandbox_uploads / md_path.name)
                    file_info["markdown_virtual_path"] = md_virtual_path
                    file_info["markdown_artifact_url"] = upload_artifact_url(thread_id, md_path.name)

            uploaded_files.append(file_info)

        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")

    return UploadResponse(
        success=True,
        files=uploaded_files,
        message=f"Successfully uploaded {len(uploaded_files)} file(s)",
    )


@router.get("/list", response_model=dict)
async def list_uploaded_files(thread_id: str, request: Request = None) -> dict:
    """List all files in a thread's uploads directory."""
    await require_thread_read_access(request, thread_id)
    try:
        uploads_dir = get_uploads_dir(thread_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = list_files_in_dir(uploads_dir)
    enrich_file_listing(result, thread_id)

    # Gateway additionally includes the sandbox-relative path.
    sandbox_uploads = get_paths().sandbox_uploads_dir(thread_id)
    for f in result["files"]:
        f["path"] = str(sandbox_uploads / f["filename"])

    return result


@router.delete("/{filename}")
async def delete_uploaded_file(thread_id: str, filename: str, request: Request = None) -> dict:
    """Delete a file from a thread's uploads directory."""
    await require_thread_manage_access(request, thread_id)
    try:
        uploads_dir = get_uploads_dir(thread_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        return delete_file_safe(uploads_dir, filename, convertible_extensions=CONVERTIBLE_EXTENSIONS)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    except PathTraversalError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        logger.error(f"Failed to delete {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete {filename}: {str(e)}")
