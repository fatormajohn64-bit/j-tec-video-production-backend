from datetime import datetime, timezone


_jobs = {}


def create_video_job(job_id: str, quote: str, style: str):
    job = {
        "job_id": job_id,
        "quote": quote,
        "style": style,
        "status": "queued",
        "progress": 0,
        "video_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _jobs[job_id] = job

    return job


def get_video_job(job_id: str):
    return _jobs.get(job_id)
