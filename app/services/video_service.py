import threading
from datetime import datetime, timezone

from app.services.scene_builder import build_scene
from app.services.image_search import find_matching_image


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
        # --------------------------------
        # STEP 1: Analyze quote
        # --------------------------------
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

        # --------------------------------
        # STEP 2: Find matching visual
        # --------------------------------
        update_job(
            job_id,
            status="finding_visual",
            progress=35,
        )

        image = find_matching_image(
            scene["scene_description"]
        )

        scene["image"] = image

        # --------------------------------
        # STEP 3: Scene ready
        # --------------------------------
        update_job(
            job_id,
            status="scene_ready",
            progress=50,
            scene=scene,
            image=image,
        )

        # --------------------------------
        # STEP 4: Ready for video renderer
        # --------------------------------
        update_job(
            job_id,
            status="ready_for_render",
            progress=55,
        )

        # --------------------------------
        # VIDEO RENDERER WILL BE ADDED NEXT
        # --------------------------------
        #
        # render_video(...)
        #
        # Once the renderer is connected,
        # this section will create the MP4.
        #

    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            error=str(exc),
            progress=0,
        )


def update_job(job_id: str, **changes):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(changes)


def get_video_job(job_id: str):
    with _lock:
        return _jobs.get(job_id)
