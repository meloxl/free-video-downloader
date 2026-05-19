from __future__ import annotations

import asyncio
import os
import shutil
import time
import uuid
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import AsyncIterator

from fastapi import HTTPException

from .models import Job, JobProgress, JobStatus, SummaryStatus
from .settings import settings


def _now() -> float:
    return time.time()


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._events: dict[str, asyncio.Queue[dict]] = {}
        self._lock = asyncio.Lock()
        self._active_by_ip: dict[str, set[str]] = defaultdict(set)

    async def create_job(
        self,
        *,
        url: str,
        ip: str,
        meta: dict | None = None,
        max_active_jobs_per_ip: int | None = None,
    ) -> Job:
        limit = max_active_jobs_per_ip if max_active_jobs_per_ip is not None else settings.max_active_jobs_per_ip
        async with self._lock:
            active = {jid for jid in self._active_by_ip[ip] if self._jobs.get(jid, None) and self._jobs[jid].status in {JobStatus.queued, JobStatus.downloading}}
            self._active_by_ip[ip] = active
            if len(active) >= limit:
                raise HTTPException(status_code=429, detail="Too many active downloads for this IP")

            job_id = uuid.uuid4().hex
            t = _now()
            job = Job(
                id=job_id,
                url=url,
                ip=ip,
                created_at=t,
                updated_at=t,
                expires_at=t + settings.ttl_seconds,
                meta=meta or {},
            )
            self._jobs[job_id] = job
            self._events[job_id] = asyncio.Queue(maxsize=500)
            self._active_by_ip[ip].add(job_id)

        await self.emit(job_id, {"type": "status", "status": job.status.value})
        return job

    async def get_job(self, job_id: str) -> Job:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            return job

    async def list_jobs(self) -> list[Job]:
        async with self._lock:
            return list(self._jobs.values())

    async def update_job(self, job_id: str, **kwargs) -> Job:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.updated_at = _now()
            return job

    async def set_progress(self, job_id: str, progress: JobProgress) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.progress = progress
            job.status = progress.status
            job.updated_at = _now()

        payload = asdict(progress)
        payload["status"] = progress.status.value
        await self.emit(job_id, {"type": "progress", "progress": payload})

    async def mark_finished(self, job_id: str, *, output_path: str, display_name: str | None) -> None:
        await self.update_job(job_id, status=JobStatus.finished, output_path=output_path, display_name=display_name)
        await self.emit(job_id, {"type": "status", "status": JobStatus.finished.value, "output_path": output_path, "display_name": display_name})

    async def mark_failed(self, job_id: str, *, error: str) -> None:
        await self.update_job(job_id, status=JobStatus.failed, error=error)
        await self.emit(job_id, {"type": "status", "status": JobStatus.failed.value, "error": error})

    async def set_summary_status(
        self,
        job_id: str,
        summary_status: SummaryStatus,
        *,
        summary_error: str | None = None,
        transcript_error: str | None = None,
        summary_result: dict | None = None,
    ) -> None:
        await self.update_job(
            job_id,
            summary_status=summary_status,
            summary_error=summary_error,
            transcript_error=transcript_error,
            summary_result=summary_result,
        )
        await self.emit(
            job_id,
            {
                "type": "summary",
                "summary_status": summary_status.value,
                "summary_error": summary_error,
                "transcript_error": transcript_error,
                "summary_result": summary_result,
            },
        )

    async def emit(self, job_id: str, event: dict) -> None:
        q = self._events.get(job_id)
        if not q:
            return
        try:
            q.put_nowait({"ts": _now(), **event})
        except asyncio.QueueFull:
            # Drop if overwhelmed; UI will resync via status endpoint.
            pass

    async def subscribe(self, job_id: str) -> AsyncIterator[dict]:
        q = self._events.get(job_id)
        if not q:
            raise HTTPException(status_code=404, detail="Job not found")
        while True:
            event = await q.get()
            yield event

    async def cleanup_expired(self) -> int:
        t = _now()
        expired: list[str] = []
        async with self._lock:
            for job_id, job in list(self._jobs.items()):
                if job.status in {JobStatus.finished, JobStatus.failed, JobStatus.expired} and job.expires_at <= t:
                    expired.append(job_id)
                elif job.status in {JobStatus.queued, JobStatus.downloading} and job.expires_at <= t:
                    # Expire even if still running; worker should handle stop best-effort.
                    expired.append(job_id)

            for job_id in expired:
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.expired
                self._events.pop(job_id, None)
                self._jobs.pop(job_id, None)
                self._active_by_ip[job.ip].discard(job_id) if job else None

        for job_id in expired:
            job_dir = Path(settings.download_root) / job_id
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)

        return len(expired)

    async def count_active_for_ip(self, ip: str) -> int:
        async with self._lock:
            active = 0
            for jid in self._active_by_ip.get(ip, set()):
                j = self._jobs.get(jid)
                if j and j.status in {JobStatus.queued, JobStatus.downloading}:
                    active += 1
            return active


def ensure_job_dir(job_id: str) -> str:
    root = Path(settings.download_root)
    root.mkdir(parents=True, exist_ok=True)
    job_dir = root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return str(job_dir)


def safe_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in (" ", "-", "_", ".", "(", ")") else "_" for ch in name)
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned[:180] or "video"
