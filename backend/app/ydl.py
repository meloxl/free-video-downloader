from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from yt_dlp import YoutubeDL

from .douyin import DouyinParser, is_douyin_url
from .jobs import safe_filename
from .settings import settings


_PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "ALL_PROXY",
    "no_proxy",
    "NO_PROXY",
)


def _disable_env_proxies() -> None:
    # Some environments inject proxies that break video hosts (Tunnel 403 etc).
    for k in _PROXY_ENV_KEYS:
        os.environ.pop(k, None)
    # Add Homebrew paths for ffmpeg
    brew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    current_path = os.environ.get("PATH", "").split(os.pathsep)
    for path in brew_paths:
        if path not in current_path:
            current_path.insert(0, path)
    os.environ["PATH"] = os.pathsep.join(current_path)


def extract_info(url: str) -> dict[str, Any]:
    _disable_env_proxies()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)


def _pick_final_file(job_dir: str) -> tuple[str | None, str | None]:
    # Prefer the largest file in job dir (video container after merge).
    p = Path(job_dir)
    files = [f for f in p.glob("*") if f.is_file()]
    if not files:
        return None, None
    files.sort(key=lambda f: f.stat().st_size, reverse=True)
    best = files[0]
    return str(best), best.name


def _download_douyin(
    *,
    url: str,
    job_dir: str,
    on_progress: Callable[[dict[str, Any]], None],
) -> tuple[str, str]:
    """
    Download Douyin video using public API (no cookies/auth required).
    """
    parser = DouyinParser(download_dir=job_dir)
    
    try:
        # Parse video info
        on_progress({
            "status": "downloading",
            "_percent_str": "5%",
            "_speed_str": "0B/s",
            "_eta_str": "calculating...",
            "filename": "Parsing video info...",
        })
        
        result = parser.download(url, mode="video")
        filepath = result["filepath"]
        filename = result["filename"]
        
        # Simulate progress for consistency
        on_progress({
            "status": "downloading",
            "_percent_str": "100%",
            "_speed_str": "0B/s",
            "_eta_str": "0s",
            "filename": filename,
        })
        
        return filepath, filename
    except Exception as e:
        raise RuntimeError(f"Douyin download failed: {e}")


def download_url(
    *,
    url: str,
    job_dir: str,
    on_progress: Callable[[dict[str, Any]], None],
    cookies_path: str | None = None,
) -> tuple[str, str]:
    """
    Blocking download. Intended to run in a worker thread.
    """
    _disable_env_proxies()
    
    # Use DouyinParser for Douyin URLs (no cookies needed)
    if is_douyin_url(url):
        return _download_douyin(url=url, job_dir=job_dir, on_progress=on_progress)
    
    outtmpl = str(Path(job_dir) / "%(title).180s-%(id)s.%(ext)s")

    if settings.demo_mode:
        # Deterministic, network-free path for local demos / CI.
        for pct in (3, 12, 27, 43, 61, 78, 92, 100):
            on_progress(
                {
                    "status": "downloading",
                    "_percent_str": f"{pct}%",
                    "_speed_str": "9.8MiB/s",
                    "_eta_str": f"{max(0, (100 - pct) // 10)}s",
                    "filename": str(Path(job_dir) / "demo.mp4"),
                }
            )
            time.sleep(0.25)
        # Write a small placeholder file (not a real video) so download endpoint works.
        demo_path = Path(job_dir) / "demo.txt"
        demo_path.write_text(
            "DEMO MODE\n\nThis is a placeholder download artifact.\n"
            "Set FVD_DEMO_MODE=false to use yt-dlp for real downloads.\n",
            encoding="utf-8",
        )
        return str(demo_path), demo_path.name

    # Determine appropriate headers based on URL source
    referer = "https://www.douyin.com"
    if "bilibili.com" in url:
        referer = "https://www.bilibili.com/"
    
    ydl_opts: dict[str, Any] = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": outtmpl,
        "progress_hooks": [on_progress],
        "noplaylist": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 8,
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": False,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referer,
            "Origin": referer.rstrip("/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    }
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    output_path, display_name = _pick_final_file(job_dir)
    if not output_path or not display_name:
        raise RuntimeError("Download finished but output file not found")

    display_name = safe_filename(display_name)
    final_path = str(Path(job_dir) / display_name)
    if final_path != output_path:
        try:
            Path(output_path).rename(final_path)
        except OSError:
            final_path = output_path
            display_name = Path(output_path).name

    return final_path, display_name

