from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.video_service import (
    create_video_job,
    get_video_job,
)


router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
)


GENERATED_DIR = Path("generated")


class VideoRequest(BaseModel):
    quote: str = Field(
        ...,
        min_length=3,
        max_length=500,
    )

    style: str = Field(
        default="cinematic",
    )


@router.post("")
def generate_video(request: VideoRequest):
    job_id = __import__("uuid").uuid4().__str__()

    job = create_video_job(
        job_id=job_id,
        quote=request.quote,
        style=request.style,
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": job["status"],
        "message": "Video generation started.",
    }


@router.get("/{job_id}")
def video_status(job_id: str):
    job = get_video_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Video job not found.",
        )

    return job


@router.get("/{job_id}/file")
def download_video(job_id: str):
    job = get_video_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Video job not found.",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="Video is not ready yet.",
        )

    video_path = GENERATED_DIR / f"{job_id}.mp4"

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Generated video file was not found.",
        )

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"j-tec-{job_id}.mp4",
    )
