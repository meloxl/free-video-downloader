from __future__ import annotations

import json
from typing import Any

import requests

from . import settings as settings_mod


def _extract_json_object(s: str) -> dict[str, Any]:
    s = s.strip()
    if s.startswith("```"):
        parts = s.split("```")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                return json.loads(part)
    if s.startswith("{") and s.endswith("}"):
        return json.loads(s)
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        return json.loads(s[start : end + 1])
    raise ValueError("模型返回中未找到 JSON 对象")


def summarize_with_deepseek(
    *,
    transcript_text: str,
    video_title: str | None,
    video_url: str,
    summary_template: str = "learning",
) -> dict[str, Any]:
    if settings_mod.settings.demo_mode:
        return {
            "outline": ["演示章节 1", "演示章节 2"],
            "key_points": ["这是演示环境下的关键要点。"],
            "action_items": ["确认环境变量后执行真实总结。"],
            "terms": ["演示模式", "转写", "总结"],
            "model": settings_mod.settings.deepseek_model,
            "template": summary_template,
        }

    if not settings_mod.settings.deepseek_api_key.strip():
        raise RuntimeError("未配置 DeepSeek API Key（FVD_DEEPSEEK_API_KEY）")

    template_prompt = {
        "learning": "输出适合学习复盘的结构，强调知识脉络、关键概念和实践建议。",
        "course": "输出适合课程精读的结构，强调课程章节、重点知识、课后行动计划。",
    }.get(summary_template, "输出适合学习复盘的结构，强调知识脉络、关键概念和实践建议。")

    prompt = (
        "你是视频学习助手。请基于转写内容输出 JSON，且必须是合法 JSON。\n"
        f"模板要求：{template_prompt}\n"
        "字段要求：\n"
        "- outline: string[]，视频结构化大纲（3-8条）\n"
        "- key_points: string[]，核心知识点（5-12条）\n"
        "- action_items: string[]，可执行建议（3-8条）\n"
        "- terms: string[]，关键词术语（5-15条）\n"
        "不要输出任何 JSON 之外的内容。"
    )
    user_text = (
        f"视频标题: {video_title or '未知'}\n"
        f"视频链接: {video_url}\n\n"
        f"转写内容:\n{transcript_text[:30000]}"
    )
    endpoint = settings_mod.settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings_mod.settings.deepseek_model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings_mod.settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek 请求失败: {resp.status_code} {resp.text[:400]}")
    data = resp.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    result = _extract_json_object(content)
    result["model"] = settings_mod.settings.deepseek_model
    result["template"] = summary_template
    usage = data.get("usage")
    if usage:
        result["usage"] = usage
    return result
