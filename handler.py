from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

import runpod

from config import settings
from engine import engine, validate_request
from storage import publish_artifacts

_MAX_BATCH_JOBS = 20


def _single(job_id: str, data: dict) -> dict:
    job_dir = Path(settings.output_dir) / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True, exist_ok=False)

    uploaded = False
    try:
        started = time.perf_counter()
        result = engine.generate(data, job_dir)
        artifacts = publish_artifacts(job_dir, job_id)
        uploaded = bool(settings.s3_bucket)
        return {
            "job_id": job_id,
            "status": result.get("status", "complete"),
            "truncated": result.get("truncated", {}),
            "sample_rate": result.get("sample_rate"),
            "audio_seconds": result.get("audio_seconds"),
            "execution_seconds": time.perf_counter() - started,
            "timing": result.get("timing", {}),
            "artifacts": artifacts,
        }
    finally:
        if uploaded and settings.cleanup_after_upload:
            shutil.rmtree(job_dir, ignore_errors=True)


def handler(job: dict) -> dict:
    parent_id = str(job.get("id") or uuid.uuid4())
    data = job.get("input")

    if isinstance(data, dict) and "jobs" in data:
        unknown = set(data) - {"jobs", "continue_on_error"}
        if unknown:
            raise ValueError(f"unsupported batch fields: {sorted(unknown)}")
        jobs = data.get("jobs")
        if not isinstance(jobs, list) or not jobs:
            raise ValueError("batch jobs must be a non-empty array")
        if len(jobs) > _MAX_BATCH_JOBS:
            raise ValueError(f"batch supports at most {_MAX_BATCH_JOBS} jobs per request")

        # Validate the complete batch before spending GPU time.
        clean_jobs = [validate_request(item) for item in jobs]
        continue_on_error = bool(data.get("continue_on_error", True))
        results = []
        started = time.perf_counter()

        for index, item in enumerate(clean_jobs, start=1):
            child_id = str(item.get("id") or f"song-{index:03d}")
            artifact_id = f"{parent_id}-{child_id}"
            try:
                result = _single(artifact_id, item)
                result["id"] = child_id
            except Exception as exc:
                result = {
                    "id": child_id,
                    "job_id": artifact_id,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
                results.append(result)
                if not continue_on_error:
                    break
                continue
            results.append(result)

        failed = sum(r.get("status") == "failed" for r in results)
        return {
            "batch_id": parent_id,
            "status": "complete" if failed == 0 else "partial_failure",
            "jobs_requested": len(clean_jobs),
            "jobs_finished": len(results),
            "jobs_failed": failed,
            "execution_seconds": time.perf_counter() - started,
            "results": results,
        }

    return _single(parent_id, data)


if __name__ == "__main__":
    if settings.preload:
        print("Preloading YuE2 model before accepting jobs...", flush=True)
        engine.warmup()
        print("YuE2 model preload complete.", flush=True)
    runpod.serverless.start({"handler": handler})
