from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.video_service import create_video_job, get_video_job


router = APIRouter(prefix="/videos", tags=["Videos"])


class VideoRequest(BaseModel):
    quote: str = Field(..., min_length=3, max_length=500)
    style: str = Field(default="cinematic")


@router.post("")
def generate_video(request: VideoRequest):
    job_id = str(uuid4())

    job = create_video_job(
        job_id=job_id,
        quote=request.quote,
        style=request.style,
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": job["status"],
        "message": "Video generation job created."
    }


@router.get("/{job_id}")
def video_status(job_id: str):
    job = get_video_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Video job not found."
        )

    return job
