from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import urlparse

from yt_dlp import YoutubeDL

from . import settings as settings_mod


def is_bilibili_url(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return False
    return "bilibili.com" in host or "b23.tv" in host


def _normalize_subtitle_lines(lines: list[str]) -> str:
    filtered: list[str] = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("WEBVTT") or s.startswith("NOTE"):
            continue
        if re.match(r"^\d+$", s):
            continue
        if "-->" in s:
            continue
        filtered.append(s)
    return "\n".join(filtered)


def _subtitle_text_from_blob(blob: str, ext: str) -> str:
    ext = (ext or "").lower()
    if ext in {"json", "json3"}:
        data = json.loads(blob)
        if isinstance(data, dict):
            # bilibili style
            body = data.get("body")
            if isinstance(body, list):
                lines = [str(item.get("content", "")).strip() for item in body if isinstance(item, dict)]
                return _normalize_subtitle_lines(lines)
            # youtube json3 style
            events = data.get("events")
            if isinstance(events, list):
                lines = []
                for evt in events:
                    segs = evt.get("segs") if isinstance(evt, dict) else None
                    if isinstance(segs, list):
                        text = "".join(str(seg.get("utf8", "")) for seg in segs if isinstance(seg, dict))
                        if text.strip():
                            lines.append(text.strip())
                return _normalize_subtitle_lines(lines)
    return _normalize_subtitle_lines(blob.splitlines())


def _pick_subtitle_track(info: dict[str, Any]) -> dict[str, str] | None:
    subtitles = info.get("subtitles") or {}
    auto_caps = info.get("automatic_captions") or {}
    lang_priority = [
        "zh-CN",
        "zh-Hans",
        "zh-Hant",
        "zh",
        "en",
    ]

    def pick(dct: dict[str, Any]) -> dict[str, str] | None:
        for lang in lang_priority:
            tracks = dct.get(lang) or []
            if tracks:
                best = tracks[0]
                if isinstance(best, dict) and best.get("url"):
                    return {
                        "url": str(best["url"]),
                        "ext": str(best.get("ext") or ""),
                        "lang": lang,
                    }
        for lang, tracks in dct.items():
            if tracks:
                best = tracks[0]
                if isinstance(best, dict) and best.get("url"):
                    return {
                        "url": str(best["url"]),
                        "ext": str(best.get("ext") or ""),
                        "lang": str(lang),
                    }
        return None

    return pick(subtitles) or pick(auto_caps)


def diagnose_subtitles(url: str) -> dict[str, Any]:
    """诊断函数，查看视频的完整字幕信息"""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 60,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        info = ydl.sanitize_info(info)
        
        return {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "subtitles": info.get("subtitles"),
            "automatic_captions": info.get("automatic_captions"),
            "has_subtitles": bool(info.get("subtitles")),
            "has_auto_caps": bool(info.get("automatic_captions")),
        }


def _fetch_subtitle_via_ytdlp(url: str) -> dict[str, Any]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 60,
        "retries": 10,
    }
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                info = ydl.sanitize_info(info)
                track = _pick_subtitle_track(info)
                if not track:
                    return {
                        "source": "none",
                        "lang": None,
                        "text": "",
                        "title": info.get("title"),
                        "duration": info.get("duration"),
                        "error": "该视频没有字幕",
                    }
                with ydl.urlopen(track["url"]) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                text = _subtitle_text_from_blob(raw, track["ext"])
                if not text.strip():
                    return {
                        "source": "none",
                        "lang": track.get("lang"),
                        "text": "",
                        "title": info.get("title"),
                        "duration": info.get("duration"),
                        "error": "字幕内容为空",
                    }
                return {
                    "source": "subtitle",
                    "lang": track["lang"],
                    "text": text,
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                }
        except Exception as e:
            if "Read timed out" in str(e) or "timeout" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            raise RuntimeError(f"字幕提取失败（已重试 {max_retries} 次）: {e}")


def extract_transcript(
    *,
    url: str,
    job_dir: str,
    output_path: str,
) -> dict[str, Any]:
    """
    直接提取B站等平台的默认字幕，不使用ASR兜底。
    """
    if settings_mod.settings.demo_mode:
        return {
            "source": "subtitle",
            "lang": "zh",
            "title": "DEMO 视频",
            "duration": 120,
            "text": "这是演示模式生成的转写文本。用于测试总结流程是否打通。",
        }

    return _fetch_subtitle_via_ytdlp(url)
