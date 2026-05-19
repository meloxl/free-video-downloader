import time
import importlib

from fastapi.testclient import TestClient

import backend.app.billing.db as billing_db_mod
import backend.app.billing.service as billing_service_mod
import backend.app.main as main_mod
import backend.app.settings as settings_mod
import backend.app.ydl as ydl_mod


def test_create_jobs_and_finish_in_demo_mode(monkeypatch):
    # Ensure demo mode enabled for tests
    monkeypatch.setenv("FVD_DEMO_MODE", "true")
    importlib.reload(settings_mod)
    importlib.reload(ydl_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as client:
        resp = client.post("/api/jobs", data={"urls": "https://example.com/a\nhttps://example.com/b"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 2

        job_id = data["jobs"][0]["id"]
        # Wait up to ~4s for demo completion
        for _ in range(14):
            r = client.get(f"/api/jobs/{job_id}")
            assert r.status_code == 200
            j = r.json()
            if j["status"] == "finished" and j.get("summary_status") in {"done", "skipped"}:
                break
            time.sleep(0.3)
        assert j["status"] == "finished"
        assert j.get("summary_status") in {"done", "skipped"}


def test_active_limit(monkeypatch):
    monkeypatch.setenv("FVD_DEMO_MODE", "true")
    monkeypatch.setenv("FVD_MAX_ACTIVE_JOBS_PER_IP", "1")
    importlib.reload(settings_mod)
    importlib.reload(billing_db_mod)
    importlib.reload(billing_service_mod)
    importlib.reload(ydl_mod)
    importlib.reload(main_mod)
    with TestClient(main_mod.app) as client:
        # Same request creates two jobs while the first is still active.
        r = client.post("/api/jobs", data={"urls": "https://example.com/1\nhttps://example.com/2"})
        assert r.status_code == 429


def test_summary_endpoint_in_demo_mode(monkeypatch):
    monkeypatch.setenv("FVD_DEMO_MODE", "true")
    monkeypatch.setenv("FVD_SUMMARY_ONLY_BILIBILI", "false")
    importlib.reload(settings_mod)
    importlib.reload(ydl_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as client:
        resp = client.post(
            "/api/jobs",
            data={
                "urls": "https://www.bilibili.com/video/BV1xx411c7mD",
                "summary_template": "course",
            },
        )
        assert resp.status_code == 200
        first_job = resp.json()["jobs"][0]
        job_id = first_job["id"]
        assert first_job["meta"]["summary_template"] == "course"

        for _ in range(20):
            j = client.get(f"/api/jobs/{job_id}").json()
            if j["status"] == "finished" and j["summary_status"] == "done":
                break
            time.sleep(0.3)

        assert j["status"] == "finished"
        assert j["summary_status"] == "done"

        s = client.get(f"/api/jobs/{job_id}/summary")
        assert s.status_code == 200
        payload = s.json()
        assert "summary_result" in payload
        assert isinstance(payload["summary_result"].get("outline"), list)
        assert payload["summary_result"].get("template") == "course"
        assert j.get("transcript_error") in (None, "")
        assert j.get("summary_error") in (None, "")

        tr = client.get(f"/api/jobs/{job_id}/transcript")
        assert tr.status_code == 200
        tr_payload = tr.json()
        assert isinstance(tr_payload.get("transcript", {}).get("text"), str)

        md = client.get(f"/api/jobs/{job_id}/summary.md")
        assert md.status_code == 200
        assert "text/markdown" in md.headers.get("content-type", "")
        assert "视频大纲" in md.text

        txt = client.get(f"/api/jobs/{job_id}/transcript.txt")
        assert txt.status_code == 200
        assert "text/plain" in txt.headers.get("content-type", "")
        assert "字幕/转写文本" in txt.text


def test_summary_template_fallback(monkeypatch):
    monkeypatch.setenv("FVD_DEMO_MODE", "true")
    monkeypatch.setenv("FVD_SUMMARY_ONLY_BILIBILI", "false")
    importlib.reload(settings_mod)
    importlib.reload(ydl_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as client:
        resp = client.post(
            "/api/jobs",
            data={
                "urls": "https://example.com/video1",
                "summary_template": "unknown_template",
            },
        )
        assert resp.status_code == 200
        first_job = resp.json()["jobs"][0]
        assert first_job["meta"]["summary_template"] == "learning"
