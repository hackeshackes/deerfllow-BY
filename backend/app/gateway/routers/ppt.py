import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.ppt_master_service import get_ppt_master_service
from app.services.ppt_service import get_ppt_service

router = APIRouter(prefix="/api/ppt", tags=["PPT Generation"])


class PPTGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="PPT 主题")
    num_slides: int = Field(default=8, ge=3, le=20, description="幻灯片数量 (3-20)")
    style: str = Field(default="gradient-modern", description="设计风格")
    aspect_ratio: str = Field(default="16:9", description="幻灯片比例")


class PPTAIGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="PPT 主题")
    content: str | None = Field(default=None, description="可选：直接提供内容")
    source_file: str | None = Field(default=None, description="可选：源文件路径")
    num_slides: int = Field(default=8, ge=3, le=20, description="幻灯片数量 (3-20)")
    style: str = Field(default="free", description="设计风格: free, consulting, academic, etc.")
    template: str | None = Field(default=None, description="可选：模板名称")
    format: str = Field(default="ppt169", description="格式: ppt169, ppt43, xhs, story")
    aspect_ratio: str = Field(default="16:9", description="幻灯片比例")


class PPTMasterTemplatesResponse(BaseModel):
    success: bool
    templates: list[dict] = []


class PPTMasterInfoResponse(BaseModel):
    success: bool
    installed: bool
    task_id: str | None = None
    file_path: str | None = None
    status: str
    message: str
    error: str | None = None
    is_fallback: bool = False
    warning: str | None = None


class PPTGenerateResponse(BaseModel):
    success: bool
    task_id: str | None = None
    status: str
    message: str
    error: str | None = None
    is_fallback: bool = False
    warning: str | None = None


class PPTTaskStatusResponse(BaseModel):
    task_id: str
    phase: str
    progress: float
    attempts: int
    error: str | None = None
    is_fallback: bool = False
    started_at: float
    updated_at: float
    output_path: str | None = None


class PPTTaskCancelResponse(BaseModel):
    success: bool
    message: str


@router.post("/generate", response_model=PPTGenerateResponse)
async def generate_ppt(request: PPTGenerateRequest) -> PPTGenerateResponse:
    service = get_ppt_master_service()

    result = service.generate(
        topic=request.topic,
        num_slides=request.num_slides,
        style=request.style,
        aspect_ratio=request.aspect_ratio,
    )

    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    return PPTGenerateResponse(
        success=result.get("success", False),
        task_id=result.get("task_id"),
        status=result.get("status", "completed"),
        message=result.get("message", "PPT generated successfully"),
        error=result.get("error"),
        is_fallback=result.get("is_fallback", False),
        warning=result.get("warning"),
    )


@router.get("/download/{task_id}")
async def download_ppt(task_id: str) -> FileResponse:
    service = get_ppt_service()
    filepath = service.get_output_path(task_id)

    if not filepath or not os.path.exists(filepath):
        ppt_master = get_ppt_master_service()
        filepath = ppt_master.get_output_path(task_id)

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PPT file not found or expired")

    filename = os.path.basename(filepath)
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.post("/generate-ai", response_model=PPTMasterInfoResponse)
async def generate_ppt_ai(request: PPTAIGenerateRequest) -> PPTMasterInfoResponse:
    service = get_ppt_master_service()

    result = service.generate(
        topic=request.topic,
        content=request.content,
        source_file=request.source_file,
        num_slides=request.num_slides,
        style=request.style,
        template=request.template,
        format=request.format,
        aspect_ratio=request.aspect_ratio,
    )

    return PPTMasterInfoResponse(
        success=result.get("success", False),
        installed=service._ensure_skill_dir(),
        task_id=result.get("task_id"),
        file_path=result.get("file_path"),
        status=result.get("status", "failed"),
        message=result.get("message", ""),
        error=result.get("error"),
        is_fallback=result.get("is_fallback", False),
        warning=result.get("warning"),
    )


@router.get("/task/{task_id}/status", response_model=PPTTaskStatusResponse)
async def get_ppt_task_status(task_id: str) -> PPTTaskStatusResponse:
    service = get_ppt_master_service()
    state = service.get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="PPT task not found or expired")
    return PPTTaskStatusResponse(**state)


@router.post("/task/{task_id}/cancel", response_model=PPTTaskCancelResponse)
async def cancel_ppt_task(task_id: str) -> PPTTaskCancelResponse:
    service = get_ppt_master_service()
    if not service.cancel_task(task_id):
        raise HTTPException(status_code=404, detail="PPT task not found or expired")
    return PPTTaskCancelResponse(success=True, message="Task cancelled")


@router.get("/templates", response_model=PPTMasterTemplatesResponse)
async def list_ppt_templates() -> PPTMasterTemplatesResponse:
    service = get_ppt_master_service()
    templates = service.list_templates()
    return PPTMasterTemplatesResponse(success=True, templates=templates)


@router.get("/templates/{template_name}")
async def get_template_info(template_name: str) -> dict:
    service = get_ppt_master_service()
    info = service.get_template_info(template_name)
    if info is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True, **info}


@router.get("/status")
async def ppt_master_status() -> dict:
    service = get_ppt_master_service()
    installed = service._ensure_skill_dir()
    return {
        "installed": installed,
        "skill_dir": str(service.SKILL_DIR),
        "available": installed,
        "message": "PPT Master ready" if installed else "PPT Master not fully installed",
    }
