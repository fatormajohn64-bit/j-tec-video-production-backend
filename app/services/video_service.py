import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services.scene_builder import build_scene
from app.services.image_search import find_matching_images
from app.services.video_encoder import render_video


_jobs = {}
_lock = threading.Lock()

GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_FPS = [10, 20, 30, 50, 60]
ALLOWED_DURATIONS = [4, 5, 6, 7, 8, 9, 10, 15, 20]

# Idea: a 10s/60fps single-image video already crashed the free-tier
# Render instance (0.15 CPU / 512MB) around the 3-minute mark. Frame
# count (fps x duration) drives Playwright/FFmpeg load — not image
# count — so this cap protects against combos like 60fps x 20s that
# would reliably crash on this tier. This number is a conservative
# starting guess, not a measured limit. Tune it once you've tested
# how far this Render plan can actually go, or drop it once you
# upgrade off the free tier.
MAX_SAFE_FRAMES = 240


def resolve_render_settings(requested_fps, requested_duration):
    fps = requested_fps if requested_fps in ALLOWED_FPS else 30
    duration = requested_duration if requested_duration in ALLOWED_DURATIONS else 10

    notes = []
    total_frames = fps * duration

    if total_frames > MAX_SAFE_FRAMES:
        fps_options = sorted(
            [f for f in ALLOWED_FPS if f * duration <= MAX_SAFE_FRAMES],
            reverse=True,
        )

        if fps_options:
            new_fps = fps_options[0]
            if new_fps != fps:
                notes.append(f"Reduced fps from {fps} to {new_fps} to fit server limits.")
            fps = new_fps
        else:
            fps = min(ALLOWED_FPS)
            duration_options = sorted(
                [d for d in ALLOWED_DURATIONS if fps * d <= MAX_SAFE_FRAMES],
                reverse=True,
            )
            new_duration = duration_options[0] if duration_options else min(ALLOWED_DURATIONS)
            if new_duration != duration:
                notes.append(f"Reduced duration from {duration}s to {new_duration}s to fit server limits.")
            duration = new_duration

    return fps, duration, notes


def create_video_job(
    job_id: str,
    quote: str,
    style: str,
    fps: int = 30,
    duration_seconds: int = 10,
    num_images: int = 1,
):
    fps = fps if fps in ALLOWED_FPS else 30
    duration_seconds = duration_seconds if duration_seconds in ALLOWED_DURATIONS else 10
    num_images = max(1, min(10, num_images))

    resolved_fps, resolved_duration, notes = resolve_render_settings(fps, duration_seconds)

    job = {
        "job_id": job_id,
        "quote": quote,
        "style": style,
        "requested_fps": fps,
        "requested_duration_seconds": duration_seconds,
        "fps": resolved_fps,
        "duration_seconds": resolved_duration,
        "num_images": num_images,
        "adjustments": notes,
        "status": "queued",
        "progress": 0,
        "scene": None,
        "images": None,
        "video_url": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _jobs[job_id] = job

    thread = threading.Thread(target=process_video_job, args=(job_id,), daemon=True)
    thread.start()

    return job


def process_video_job(job_id: str):
    try:
        update_job(job_id, status="analyzing", progress=10)

        job = get_video_job(job_id)
        if not job:
            raise RuntimeError("Video job was not found.")

        scene = build_scene(
            quote=job["quote"],
            style=job["style"],
            num_images=job["num_images"],
            fps=job["fps"],
            duration_seconds=job["duration_seconds"],
        )

        update_job(job_id, status="finding_visual", progress=25)

        images = find_matching_images(scene["scene_descriptions"])
        scene["images"] = images

        update_job(job_id, status="scene_ready", progress=40, scene=scene, images=images)

        update_job(job_id, status="rendering", progress=45)

        output_path = GENERATED_DIR / f"{job_id}.mp4"

        render_video(
            quote=job["quote"],
            image_paths=[image["local_path"] for image in images],
            style=job["style"],
            output_path=str(output_path),
            fps=job["fps"],
            duration_seconds=job["duration_seconds"],
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            video_url=f"/api/v1/videos/{job_id}/file",
        )

    except Exception as exc:
        update_job(job_id, status="failed", progress=0, error=str(exc))


def update_job(job_id: str, **changes):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(changes)


def get_video_job(job_id: str):
    with _lock:
        return _jobs.get(job_id)
