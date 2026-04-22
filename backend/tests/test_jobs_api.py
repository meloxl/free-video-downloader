import time
import importlib

from fastapi.testclient import TestClient

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
            if j["status"] == "finished":
                break
            time.sleep(0.3)
        assert j["status"] == "finished"


def test_active_limit(monkeypatch):
    monkeypatch.setenv("FVD_DEMO_MODE", "true")
    monkeypatch.setenv("FVD_MAX_ACTIVE_JOBS_PER_IP", "1")
    importlib.reload(settings_mod)
    importlib.reload(ydl_mod)
    importlib.reload(main_mod)
    with TestClient(main_mod.app) as client:
        r1 = client.post("/api/jobs", data={"urls": "https://example.com/1"})
        assert r1.status_code == 200
        r2 = client.post("/api/jobs", data={"urls": "https://example.com/2"})
        assert r2.status_code == 429

