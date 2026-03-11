"""
Minimal FastAPI stub: /health and /upscale placeholder for future API deployment.
CLI remains the main interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Optional: only import pipeline when upscale is actually called, to avoid loading heavy deps at startup
# from app.services.pipeline_service import run_pipeline

app = FastAPI(
    title="FlashVSR App API",
    description="Upscale video to 1080p using official FlashVSR (placeholder endpoints)",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "flashvsr_app"


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check for load balancers and readiness probes."""
    return HealthResponse()


class UpscaleRequest(BaseModel):
    input_path: str = Field(..., description="Path to input video file")
    output_dir: str = Field(..., description="Output directory for results")
    target_width: int = Field(1920, ge=1, le=4096)
    target_height: int = Field(1080, ge=1, le=2160)
    model_version: Literal["v1", "v1.1"] = "v1.1"
    mode: Literal["full", "tiny", "tiny_long_video"] = "tiny_long_video"
    fit_mode: Literal["pad", "crop", "stretch"] = "pad"
    keep_intermediate: bool = True


class UpscaleResponse(BaseModel):
    success: bool
    message: str
    final_output_path: Optional[str] = None
    error: Optional[str] = None


@app.post("/upscale", response_model=UpscaleResponse)
def upscale(request: UpscaleRequest) -> UpscaleResponse:
    """
    Placeholder for video upscale. In production, this would enqueue a job or run the pipeline.
    Currently returns a message indicating the endpoint is not yet implemented for async/safe use.
    """
    # Validate paths exist to avoid silent failures later
    input_path = Path(request.input_path)
    if not input_path.is_file():
        raise HTTPException(status_code=400, detail=f"Input file not found: {request.input_path}")
    output_dir = Path(request.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Optional: run pipeline synchronously (blocking). For production, use a task queue.
    # result = run_pipeline(
    #     input_video=input_path,
    #     output_dir=output_dir,
    #     target_width=request.target_width,
    #     target_height=request.target_height,
    #     model_version=request.model_version,
    #     mode=request.mode,
    #     fit_mode=request.fit_mode,
    #     keep_intermediate=request.keep_intermediate,
    # )
    # return UpscaleResponse(
    #     success=result.success,
    #     message="Pipeline completed",
    #     final_output_path=result.final_output_path,
    #     error=result.error,
    # )

    return UpscaleResponse(
        success=True,
        message="Upscale endpoint is a placeholder. Use CLI: python -m app.cli --input ... --output-dir ...",
        final_output_path=None,
    )
