import threading
from datetime import datetime, timezone

from app.services.scene_builder import build_scene


_jobs = {}
_lock = threading.Lock()


def create_video_job(job_id: str, quote: str, style: str):
    job = {
        "job_id": job_id,
        "quote": quote,
        "style": style,
        "status": "queued",
        "progress": 0,
        "scene": None,
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
        update_job(job_id, status="analyzing", progress=10)

        job = get_video_job(job_id)

        scene = build_scene(
            quote=job["quote"],
            style=job["style"],
        )

        update_job(
            job_id,
            status="scene_ready",
            progress=25,
            scene=scene,
        )

        # Video renderer will be connected here next.
        update_job(
            job_id,
            status="ready_for_render",
            progress=30,
        )

    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            error=str(exc),
        )


def update_job(job_id: str, **changes):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(changes)


def get_video_job(job_id: str):
    with _lock:
        return _jobs.get(job_id)
