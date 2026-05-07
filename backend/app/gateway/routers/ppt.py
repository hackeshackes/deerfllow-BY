import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.ppt_service import get_ppt_service

router = APIRouter(prefix="/api/ppt", tags=["PPT Generation"])


class PPTGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="PPT 主题")
    num_slides: int = Field(default=8, ge=3, le=20, description="幻灯片数量 (3-20)")
    style: str = Field(default="gradient-modern", description="设计风格")
    aspect_ratio: str = Field(default="16:9", description="幻灯片比例")


class PPTGenerateResponse(BaseModel):
    success: bool
    task_id: str | None = None
    status: str
    message: str
    error: str | None = None


@router.post("/generate", response_model=PPTGenerateResponse)
async def generate_ppt(request: PPTGenerateRequest) -> PPTGenerateResponse:
    service = get_ppt_service()

    result = service.generate(
        topic=request.topic,
        num_slides=request.num_slides,
        style=request.style,
        aspect_ratio=request.aspect_ratio,
    )

    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    return PPTGenerateResponse(
        success=True,
        task_id=result.get("task_id"),
        status="completed",
        message=result.get("message", "PPT generated successfully"),
    )


@router.get("/download/{task_id}")
async def download_ppt(task_id: str) -> FileResponse:
    service = get_ppt_service()
    filepath = service.get_output_path(task_id)

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PPT file not found or expired")

    return FileResponse(
        path=filepath,
        filename=f"presentation_{task_id}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
