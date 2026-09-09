import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services.scene_builder import build_scene
from app.services.image_search import find_matching_image
from app.services.video_encoder import render_video


_jobs = {}
_lock = threading.Lock()

GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def create_video_job(job_id: str, quote: str, style: str):
    job = {
        "job_id": job_id,
        "quote": quote,
        "style": style,
        "status": "queued",
        "progress": 0,
        "scene": None,
        "image": None,
        "video_url": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _jobs[job_id] = job

    thread = threading.Thread(
        target=process_video_job,
        args=(job_id,),
        daemon=True,
    )

    thread.start()

    return job


def process_video_job(job_id: str):
    try:
        # -----------------------------
        # STEP 1: Analyze quote
        # -----------------------------
        update_job(
            job_id,
            status="analyzing",
            progress=10,
        )

        job = get_video_job(job_id)

        if not job:
            raise RuntimeError("Video job was not found.")

        scene = build_scene(
            quote=job["quote"],
            style=job["style"],
        )

        # -----------------------------
        # STEP 2: Find visual
        # -----------------------------
        update_job(
            job_id,
            status="finding_visual",
            progress=25,
        )

        image = find_matching_image(
            scene["scene_description"]
        )

        scene["image"] = image

        update_job(
            job_id,
            status="scene_ready",
            progress=40,
            scene=scene,
            image=image,
        )

        # -----------------------------
        # STEP 3: Render video
        # -----------------------------
        update_job(
            job_id,
            status="rendering",
            progress=45,
        )

        output_path = GENERATED_DIR / f"{job_id}.mp4"

        render_video(
            quote=job["quote"],
            image_path=image["local_path"],
            style=job["style"],
            output_path=str(output_path),
        )

        # -----------------------------
        # STEP 4: Completed
        # -----------------------------
        update_job(
            job_id,
            status="completed",
            progress=100,
            video_url=f"/api/v1/videos/{job_id}/file",
        )

    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            progress=0,
            error=str(exc),
        )


def update_job(job_id: str, **changes):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(changes)


def get_video_job(job_id: str):
    with _lock:
        return _jobs.get(job_id)
