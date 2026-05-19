import hashlib
import hmac
import importlib
import json
import time

from fastapi.testclient import TestClient

import backend.app.billing.db as billing_db_mod
import backend.app.billing.service as billing_service_mod
import backend.app.main as main_mod
import backend.app.settings as settings_mod
import backend.app.ydl as ydl_mod


def _stripe_test_signature(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    signed = f"{ts}.{payload.decode('utf-8')}"
    digest = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _reload_app(monkeypatch, tmp_path, **env):
    env = {"FVD_DEMO_MODE": "true", **env}
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    monkeypatch.setenv("FVD_BILLING_DB_PATH", str(tmp_path / "billing.db"))
    importlib.reload(settings_mod)
    importlib.reload(billing_db_mod)
    importlib.reload(billing_service_mod)
    importlib.reload(ydl_mod)
    importlib.reload(main_mod)
    return TestClient(main_mod.app)


def test_billing_me_and_demo_checkout(monkeypatch, tmp_path):
    with _reload_app(monkeypatch, tmp_path, FVD_STRIPE_DEMO_MODE="true", FVD_DEMO_MODE="true") as client:
        me = client.get("/api/billing/me")
        assert me.status_code == 200
        assert me.json()["is_pro"] is False

        r = client.get("/billing/demo-checkout?plan=monthly", follow_redirects=False)
        assert r.status_code == 303

        me2 = client.get("/api/billing/me")
        assert me2.json()["is_pro"] is True
        assert me2.json()["entitlements"]["max_active_jobs_per_ip"] >= 10


def test_pro_higher_concurrency_entitlement(monkeypatch, tmp_path):
    with _reload_app(
        monkeypatch,
        tmp_path,
        FVD_STRIPE_DEMO_MODE="true",
        FVD_MAX_ACTIVE_JOBS_PER_IP="1",
        FVD_PRO_MAX_ACTIVE_JOBS_PER_IP="3",
    ) as client:
        free = client.get("/api/billing/me").json()
        free_limit = free["entitlements"]["max_active_jobs_per_ip"]

        client.get("/billing/demo-checkout?plan=monthly")
        pro = client.get("/api/billing/me").json()
        assert pro["is_pro"] is True
        assert pro["entitlements"]["max_active_jobs_per_ip"] > free_limit


def test_pro_enables_summary_for_non_bilibili(monkeypatch, tmp_path):
    with _reload_app(
        monkeypatch,
        tmp_path,
        FVD_STRIPE_DEMO_MODE="true",
        FVD_DEMO_MODE="true",
        FVD_SUMMARY_ONLY_BILIBILI="true",
        FVD_ENABLE_AI_SUMMARY="true",
    ) as client:
        free = client.post("/api/jobs", data={"urls": "https://example.com/video-free"})
        assert free.status_code == 200
        assert free.json()["jobs"][0]["summary_status"] == "skipped"

        client.get("/billing/demo-checkout?plan=yearly")
        pro = client.post("/api/jobs", data={"urls": "https://example.com/video-pro"})
        assert pro.status_code == 200
        assert pro.json()["jobs"][0]["summary_status"] == "queued"


def test_checkout_session_demo_mode(monkeypatch, tmp_path):
    with _reload_app(monkeypatch, tmp_path, FVD_STRIPE_DEMO_MODE="true") as client:
        assert settings_mod.settings.stripe_demo_mode is True
        r = client.post("/api/billing/checkout-session", json={"plan": "monthly"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data
        assert "demo-checkout" in data["url"]


def test_billing_success_page(monkeypatch, tmp_path):
    with _reload_app(monkeypatch, tmp_path, FVD_STRIPE_DEMO_MODE="true") as client:
        client.get("/billing/demo-checkout?plan=monthly")
        page = client.get("/billing/success?session_id=demo_ok")
        assert page.status_code == 200
        assert "Pro" in page.text


def test_webhook_idempotency(monkeypatch, tmp_path):
    monkeypatch.setenv("FVD_DEMO_MODE", "true")
    monkeypatch.setenv("FVD_STRIPE_DEMO_MODE", "false")
    monkeypatch.setenv("FVD_STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    monkeypatch.setenv("FVD_BILLING_DB_PATH", str(tmp_path / "billing.db"))
    importlib.reload(settings_mod)
    importlib.reload(billing_db_mod)
    importlib.reload(billing_service_mod)
    importlib.reload(main_mod)

    store = main_mod.billing_service.store
    store.init()
    device_id = "dev_webhook_test"
    store.ensure_device(device_id)

    event = {
        "id": "evt_test_idempotent_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "object": "checkout.session",
                "mode": "subscription",
                "client_reference_id": device_id,
                "customer": "cus_test_1",
                "subscription": "sub_test_1",
                "metadata": {"device_id": device_id},
            }
        },
    }
    payload = json.dumps(event).encode("utf-8")
    sig = _stripe_test_signature(payload, "whsec_test_secret")

    with TestClient(main_mod.app) as client:
        r1 = client.post("/api/stripe/webhook", content=payload, headers={"Stripe-Signature": sig})
        assert r1.status_code == 200
        assert store.is_pro(device_id)

        r2 = client.post("/api/stripe/webhook", content=payload, headers={"Stripe-Signature": sig})
        assert r2.status_code == 200

        rows = store._connect().execute("SELECT COUNT(*) FROM stripe_events WHERE event_id = ?", (event["id"],)).fetchone()
        assert rows[0] == 1
