import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services.scene_builder import build_scene
from app.services.image_search import find_matching_images
from app.services.video_encoder import render_video


GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = GENERATED_DIR / "jobs.db"
_db_lock = threading.Lock()

ALLOWED_FPS = [10, 20, 30, 50, 60]
ALLOWED_DURATIONS = [4, 5, 6, 7, 8, 9, 10, 15, 20]

# Idea (kept from before): a 10s/60fps single-image video already
# crashed the free-tier Render instance. This caps total frames as a
# safety net. NOTE: if restarts are happening even at 10fps/4s (40
# frames), frame count likely isn't the real cause — see the note in
# process_video_job below.
MAX_SAFE_FRAMES = 240


def _get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _db_lock:
        conn = _get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    quote TEXT,
                    style TEXT,
                    requested_fps INTEGER,
                    requested_duration_seconds INTEGER,
                    fps INTEGER,
                    duration_seconds INTEGER,
                    num_images INTEGER,
                    adjustments TEXT,
                    status TEXT,
                    progress INTEGER,
                    scene TEXT,
                    images TEXT,
                    video_url TEXT,
                    error TEXT,
                    created_at TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


_init_db()


def _row_to_job(row):
    if row is None:
        return None
    job = dict(row)
    job["adjustments"] = json.loads(job["adjustments"]) if job["adjustments"] else []
    job["scene"] = json.loads(job["scene"]) if job["scene"] else None
    job["images"] = json.loads(job["images"]) if job["images"] else None
    return job


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

    with _db_lock:
        conn = _get_connection()
        try:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, quote, style, requested_fps, requested_duration_seconds,
                    fps, duration_seconds, num_images, adjustments, status, progress,
                    scene, images, video_url, error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"], job["quote"], job["style"],
                    job["requested_fps"], job["requested_duration_seconds"],
                    job["fps"], job["duration_seconds"], job["num_images"],
                    json.dumps(job["adjustments"]), job["status"], job["progress"],
                    None, None, job["video_url"], job["error"], job["created_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

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
    if "adjustments" in changes:
        changes["adjustments"] = json.dumps(changes["adjustments"])
    if "scene" in changes:
        changes["scene"] = json.dumps(changes["scene"]) if changes["scene"] is not None else None
    if "images" in changes:
        changes["images"] = json.dumps(changes["images"]) if changes["images"] is not None else None

    if not changes:
        return

    columns = ", ".join(f"{key} = ?" for key in changes.keys())
    values = list(changes.values()) + [job_id]

    with _db_lock:
        conn = _get_connection()
        try:
            conn.execute(f"UPDATE jobs SET {columns} WHERE job_id = ?", values)
            conn.commit()
        finally:
            conn.close()


def get_video_job(job_id: str):
    with _db_lock:
        conn = _get_connection()
        try:
            cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return _row_to_job(row)
        finally:
            conn.close()
