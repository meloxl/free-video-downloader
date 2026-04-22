from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import orjson
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .douyin import is_douyin_url
from .jobs import JobStore, ensure_job_dir
from .models import JobProgress, JobStatus
from .settings import settings
from .ydl import download_url


app = FastAPI(title="Free Video Downloader", version="0.1.0")
BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

job_store = JobStore()
executor = ThreadPoolExecutor(max_workers=6)


def _client_ip(req: Request) -> str:
    # Minimal; behind proxy should be configured with trusted headers by deploy layer.
    return req.client.host if req.client else "unknown"


def _require_admin(x_admin_token: str | None) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.on_event("startup")
async def _startup() -> None:
    app.state.loop = asyncio.get_running_loop()

    async def cleaner() -> None:
        while True:
            try:
                await job_store.cleanup_expired()
            finally:
                await asyncio.sleep(settings.cleanup_interval_seconds)

    asyncio.create_task(cleaner())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    return templates.TemplateResponse("index.html", {"request": request, "title": "万能视频下载 · 一键保存"})


def _parse_urls(raw: str) -> list[str]:
    urls: list[str] = []
    for part in raw.replace("\r", "\n").split("\n"):
        s = part.strip()
        if not s:
            continue
        if len(s) > 2000:
            continue
        if s.startswith("http://") or s.startswith("https://"):
            # 抖音 URL 验证 - 只接受视频链接
            if is_douyin_url(s):
                # 抖音链接由 DouyinParser 处理（无需 Cookie）
                urls.append(s)
            elif "tiktok.com" in s:
                # TikTok 链接检查格式
                if "/video/" in s or "/v/" in s or "v.tiktok.com" in s:
                    urls.append(s)
            else:
                # 其他平台链接
                urls.append(s)
    return urls


def _human_error(e: Exception) -> str:
    s = str(e) or e.__class__.__name__
    
    # 针对抖音 URL 的特殊处理
    if "Unsupported URL" in s and "douyin.com" in s:
        return "不支持的抖音链接格式。请使用视频链接（如 https://v.douyin.com/... 或 https://www.douyin.com/video/...）"
    
    # Remove overly long noisy prefixes
    return s[:1200]


@app.post("/api/jobs")
async def create_jobs(
    request: Request,
    urls: str = Form(...),
    cookies: Optional[UploadFile] = File(default=None),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Any:
    ip = _client_ip(request)
    url_list = _parse_urls(urls)
    if not url_list:
        raise HTTPException(status_code=400, detail="No valid URLs provided")
    if len(url_list) > settings.max_urls_per_request:
        raise HTTPException(status_code=400, detail=f"Too many URLs (max {settings.max_urls_per_request})")

    # Best-effort extra guard (JobStore also enforces)
    active = await job_store.count_active_for_ip(ip)
    if active >= settings.max_active_jobs_per_ip:
        raise HTTPException(status_code=429, detail="Too many active downloads for this IP")

    cookies_path: Optional[str] = None
    if cookies is not None:
        if not settings.enable_cookies:
            raise HTTPException(status_code=403, detail="cookies is disabled by default")
        _require_admin(x_admin_token)

    jobs = []
    for u in url_list:
        job = await job_store.create_job(url=u, ip=ip)
        jobs.append(job)

    # If cookies uploaded, save once and reuse for this batch (same request).
    if cookies is not None:
        job_dir = ensure_job_dir(jobs[0].id)
        cookies_path = str(Path(job_dir) / "cookies.txt")
        content = await cookies.read()
        Path(cookies_path).write_bytes(content)

    loop = getattr(app.state, "loop", asyncio.get_running_loop())

    async def run_job(job_id: str, url: str, cookies_path_for_job: Optional[str]) -> None:
        job_dir = ensure_job_dir(job_id)
        if cookies_path_for_job and cookies_path_for_job != str(Path(job_dir) / "cookies.txt"):
            # copy cookies into this job dir if shared file
            try:
                Path(job_dir).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cookies_path_for_job, str(Path(job_dir) / "cookies.txt"))
            except Exception:
                pass
            cookies_path_for_job = str(Path(job_dir) / "cookies.txt")

        def on_progress(d: dict[str, Any]) -> None:
            status = d.get("status")
            if loop.is_closed():
                return
            if status == "downloading":
                percent_str = d.get("_percent_str") or ""
                try:
                    percent = float(percent_str.replace("%", "").strip())
                except Exception:
                    percent = None
                prog = JobProgress(
                    status=JobStatus.downloading,
                    percent=percent,
                    speed=d.get("_speed_str"),
                    eta=d.get("_eta_str"),
                    filename=os.path.basename(d.get("filename", "")) if d.get("filename") else None,
                    message=None,
                )
                asyncio.run_coroutine_threadsafe(job_store.set_progress(job_id, prog), loop)
            elif status == "finished":
                prog = JobProgress(status=JobStatus.downloading, percent=100.0, message="Processing...")
                asyncio.run_coroutine_threadsafe(job_store.set_progress(job_id, prog), loop)

        try:
            await job_store.set_progress(job_id, JobProgress(status=JobStatus.downloading, message="Starting..."))
            output_path, display_name = await loop.run_in_executor(
                executor,
                lambda: download_url(url=url, job_dir=job_dir, on_progress=on_progress, cookies_path=cookies_path_for_job),
            )
            await job_store.mark_finished(job_id, output_path=output_path, display_name=display_name)
        except Exception as e:
            await job_store.mark_failed(job_id, error=_human_error(e))

    # fire and forget each job
    for j in jobs:
        asyncio.create_task(run_job(j.id, j.url, cookies_path))

    def job_to_dict(j) -> dict[str, Any]:
        return {
            "id": j.id,
            "url": j.url,
            "status": j.status.value,
            "progress": {
                "status": j.progress.status.value,
                "percent": j.progress.percent,
                "speed": j.progress.speed,
                "eta": j.progress.eta,
                "filename": j.progress.filename,
                "message": j.progress.message,
            },
        }

    return Response(
        content=orjson.dumps({"jobs": [job_to_dict(j) for j in jobs]}),
        media_type="application/json",
    )


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> Any:
    j = await job_store.get_job(job_id)
    return {
        "id": j.id,
        "url": j.url,
        "status": j.status.value,
        "progress": {
            "status": j.progress.status.value,
            "percent": j.progress.percent,
            "speed": j.progress.speed,
            "eta": j.progress.eta,
            "filename": j.progress.filename,
            "message": j.progress.message,
        },
        "display_name": j.display_name,
        "error": j.error,
        "expires_at": j.expires_at,
    }


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    async def gen():
        # Initial ping to establish connection
        yield "event: ping\ndata: {}\n\n"
        async for evt in job_store.subscribe(job_id):
            data = orjson.dumps(evt).decode("utf-8")
            yield f"data: {data}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/file")
async def download_file(job_id: str) -> FileResponse:
    j = await job_store.get_job(job_id)
    if j.status != JobStatus.finished or not j.output_path:
        raise HTTPException(status_code=409, detail="Job not finished")
    p = Path(j.output_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    filename = j.display_name or p.name
    return FileResponse(path=str(p), filename=filename, media_type="application/octet-stream")

