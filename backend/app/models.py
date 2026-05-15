from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    queued = "queued"
    downloading = "downloading"
    finished = "finished"
    failed = "failed"
    expired = "expired"


class SummaryStatus(str, Enum):
    not_requested = "not_requested"
    queued = "queued"
    transcribing = "transcribing"
    summarizing = "summarizing"
    done = "done"
    failed = "failed"
    skipped = "skipped"


@dataclass
class JobProgress:
    status: JobStatus = JobStatus.queued
    percent: float | None = None
    speed: str | None = None
    eta: str | None = None
    filename: str | None = None
    message: str | None = None


@dataclass
class Job:
    id: str
    url: str
    created_at: float
    updated_at: float
    expires_at: float
    ip: str

    status: JobStatus = JobStatus.queued
    progress: JobProgress = field(default_factory=JobProgress)

    output_path: str | None = None
    display_name: str | None = None
    error: str | None = None
    summary_status: SummaryStatus = SummaryStatus.not_requested
    summary_error: str | None = None
    transcript_error: str | None = None
    summary_result: dict[str, Any] | None = None

    meta: dict[str, Any] = field(default_factory=dict)
