from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import runpod

from config import settings
from engine import engine
from storage import publish_artifacts


def handler(job: dict) -> dict:
    job_id = str(job.get("id") or uuid.uuid4())
    job_dir = Path(settings.output_dir) / job_id

    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True, exist_ok=False)

    uploaded = False
    try:
        result = engine.generate(job.get("input"), job_dir)
        artifacts = publish_artifacts(job_dir, job_id)
        uploaded = bool(settings.s3_bucket)

        return {
            "job_id": job_id,
            "status": result.get("status", "complete"),
            "truncated": result.get("truncated", {}),
            "sample_rate": result.get("sample_rate"),
            "audio_seconds": result.get("audio_seconds"),
            "timing": result.get("timing", {}),
            "artifacts": artifacts,
        }
    finally:
        if uploaded and settings.cleanup_after_upload:
            shutil.rmtree(job_dir, ignore_errors=True)


if __name__ == "__main__":
    if settings.preload:
        print("Preloading YuE2 model before accepting jobs...", flush=True)
        engine.warmup()
        print("YuE2 model preload complete.", flush=True)
    runpod.serverless.start({"handler": handler})
