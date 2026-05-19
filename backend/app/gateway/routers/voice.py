from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.gateway.auth import require_user
from app.gateway.data.voice_config import get_voice_config, upsert_voice_config

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceSTTResponse(BaseModel):
    text: str = Field(..., description="Transcribed text")
    language: str = Field(default="zh", description="Detected language")
    duration: float = Field(..., description="Audio duration in seconds")


class VoiceConfigResponse(BaseModel):
    stt_enabled: bool
    tts_enabled: bool
    stt_language: str
    stt_model_size: str = Field(default="small")
    tts_voice: str
    tts_speed: float


class VoiceConfigUpdate(BaseModel):
    stt_enabled: bool | None = None
    tts_enabled: bool | None = None
    stt_language: str | None = None
    stt_model_size: str | None = None
    tts_voice: str | None = None
    tts_speed: float | None = None


class VoiceTTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize", min_length=1, max_length=500)


_stt_model_cache: dict[str, object] = {}


def _get_stt_model(model_size: str):
    cache_key = f"stt_model_{model_size}"
    if cache_key in _stt_model_cache:
        return _stt_model_cache[cache_key]

    try:
        from faster_whisper import WhisperModel

        compute_type = "int8" if model_size in ("tiny", "small") else "float16"
        model = WhisperModel(
            model_size_or_path=model_size,
            device="cpu",
            compute_type=compute_type,
        )
        _stt_model_cache[cache_key] = model
        return model
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="faster-whisper not installed. Please run: uv add faster-whisper",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load STT model: {e}")


@router.post("/stt", response_model=VoiceSTTResponse)
async def speech_to_text(
    file: Annotated[UploadFile, File(description="Audio file in webm format")],
    request: Request,
):
    user = require_user(request)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content_type = file.content_type or ""
    if "webm" not in content_type.lower() and "audio" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {content_type}. Expected audio/webm",
        )

    config = get_voice_config(user.id)
    if not config.get("stt_enabled", True):
        raise HTTPException(status_code=403, detail="STT is disabled for this user")

    audio_data = await file.read()

    if len(audio_data) < 1000:
        raise HTTPException(status_code=400, detail="Audio file too short or empty")

    MAX_SIZE = 10 * 1024 * 1024
    if len(audio_data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        model_size = config.get("stt_model_size", "small")
        model = _get_stt_model(model_size)

        language = config.get("stt_language", "zh")
        language_param = None if language == "auto" else language

        segments, info = model.transcribe(
            tmp_path,
            language=language_param,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        text_parts = []
        total_duration = 0.0
        for segment in segments:
            text_parts.append(segment.text)
            total_duration = segment.end

        full_text = "".join(text_parts).strip()

        if not full_text:
            raise HTTPException(status_code=400, detail="No speech content detected")

        return VoiceSTTResponse(
            text=full_text,
            language=info.language or "zh",
            duration=total_duration,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/config", response_model=VoiceConfigResponse)
async def get_voice_config_endpoint(request: Request):
    user = require_user(request)
    config = get_voice_config(user.id)
    return VoiceConfigResponse(**config)


@router.put("/config", response_model=VoiceConfigResponse)
async def update_voice_config_endpoint(
    request: Request,
    update: VoiceConfigUpdate,
):
    user = require_user(request)

    update_data = update.model_dump(exclude_unset=True)

    if update_data.get("stt_model_size") and update_data["stt_model_size"] not in (
        "tiny",
        "small",
        "medium",
    ):
        raise HTTPException(
            status_code=400,
            detail="stt_model_size must be one of: tiny, small, medium",
        )

    updated = upsert_voice_config(user.id, update_data)
    return VoiceConfigResponse(**updated)


@router.post("/tts")
async def text_to_speech(
    request_body: VoiceTTSRequest,
    request: Request,
):
    user = require_user(request)

    config = get_voice_config(user.id)
    if not config.get("tts_enabled", True):
        raise HTTPException(status_code=403, detail="TTS is disabled for this user")

    text = request_body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        from edge_tts import Communicate

        voice = config.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        speed = config.get("tts_speed", 1.0)
        rate_percent = int((speed - 1) * 100)
        rate = f"+{rate_percent}%"
        communicate = Communicate(text=text, voice=voice, rate=rate)

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        if not audio_data:
            raise HTTPException(status_code=500, detail="TTS synthesis produced no audio")

        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "X-TTS-Voice": voice,
                "X-TTS-Speed": str(config.get("tts_speed", 1.0)),
            },
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="edge-tts not installed. Please run: uv add edge-tts",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")