from __future__ import annotations

import uuid
from typing import Any, Literal

import stripe
from stripe import SignatureVerificationError, Webhook

from ..settings import settings
from .db import BillingStore

PlanId = Literal["monthly", "yearly"]

_ACTIVE_STATUSES = frozenset({"active", "trialing"})


def _as_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return dict(obj)


class BillingService:
    def __init__(self, store: BillingStore | None = None) -> None:
        self.store = store or BillingStore()
        if settings.stripe_secret_key and not settings.stripe_demo_mode:
            stripe.api_key = settings.stripe_secret_key

    def init(self) -> None:
        self.store.init()

    def ensure_device(self, device_id: str) -> None:
        self.store.ensure_device(device_id)

    def is_pro(self, device_id: str) -> bool:
        if settings.stripe_demo_mode:
            return self.store.is_pro(device_id)
        return self.store.is_pro(device_id)

    def get_entitlements(self, device_id: str) -> dict[str, Any]:
        pro = self.is_pro(device_id)
        max_active = settings.pro_max_active_jobs_per_ip if pro else settings.max_active_jobs_per_ip
        summary_all_platforms = pro or (not settings.summary_only_bilibili)
        return {
            "is_pro": pro,
            "max_active_jobs_per_ip": max_active,
            "summary_all_platforms": summary_all_platforms,
        }

    def get_billing_status(self, device_id: str) -> dict[str, Any]:
        self.ensure_device(device_id)
        sub = self.store.get_active_subscription(device_id)
        ent = self.get_entitlements(device_id)
        return {
            "device_id": device_id,
            "is_pro": ent["is_pro"],
            "entitlements": ent,
            "subscription": _subscription_payload(sub) if sub else None,
        }

    def _price_id_for_plan(self, plan: PlanId) -> str:
        if plan == "monthly":
            price_id = settings.stripe_price_monthly
        else:
            price_id = settings.stripe_price_yearly
        if not price_id:
            raise ValueError(f"Stripe price not configured for plan: {plan}")
        return price_id

    def create_checkout_session(
        self,
        *,
        device_id: str,
        plan: PlanId,
        idempotency_key: str | None = None,
    ) -> dict[str, str]:
        self.ensure_device(device_id)
        base = settings.public_base_url.rstrip("/")

        if settings.stripe_demo_mode:
            return {
                "url": f"{base}/billing/demo-checkout?plan={plan}",
                "session_id": f"demo_{uuid.uuid4().hex}",
            }

        price_id = self._price_id_for_plan(plan)

        if not settings.stripe_secret_key:
            raise RuntimeError("FVD_STRIPE_SECRET_KEY is required for checkout")

        device = self.store.get_device(device_id) or {}
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base}/billing/cancel",
            "client_reference_id": device_id,
            "metadata": {"device_id": device_id, "plan": plan},
            "subscription_data": {"metadata": {"device_id": device_id}},
        }
        if device.get("stripe_customer_id"):
            params["customer"] = device["stripe_customer_id"]

        kwargs: dict[str, Any] = {}
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key

        session = stripe.checkout.Session.create(**params, **kwargs)
        if not session.url:
            raise RuntimeError("Stripe Checkout Session has no url")
        return {"url": session.url, "session_id": session.id}

    def activate_demo_subscription(self, device_id: str, *, plan: PlanId = "monthly") -> None:
        """Test/demo only: grant Pro without Stripe."""
        self.ensure_device(device_id)
        try:
            price_id = self._price_id_for_plan(plan)
        except ValueError:
            price_id = f"demo_{plan}"
        sub_id = f"demo_sub_{device_id}"
        self.store.upsert_subscription(
            device_id=device_id,
            stripe_subscription_id=sub_id,
            stripe_customer_id=f"demo_cus_{device_id}",
            status="active",
            price_id=price_id,
            current_period_end=None,
        )

    def handle_webhook(self, payload: bytes, sig_header: str | None) -> None:
        if settings.stripe_demo_mode and not settings.stripe_webhook_secret:
            return

        if not settings.stripe_webhook_secret:
            raise RuntimeError("FVD_STRIPE_WEBHOOK_SECRET is required for webhooks")

        try:
            event = Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
        except ValueError as e:
            raise ValueError(f"Invalid payload: {e}") from e
        except SignatureVerificationError as e:
            raise ValueError(f"Invalid signature: {e}") from e

        if not self.store.mark_event_processed(event["id"], event["type"]):
            return

        etype = event["type"]
        data = event["data"]["object"]

        if etype == "checkout.session.completed":
            self._on_checkout_completed(data)
        elif etype == "customer.subscription.updated":
            self._on_subscription_updated(data)
        elif etype == "customer.subscription.deleted":
            self._on_subscription_deleted(data)

    def _on_checkout_completed(self, session: Any) -> None:
        session = _as_dict(session)
        device_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("device_id")
        if not device_id:
            return
        self.ensure_device(device_id)

        customer_id = session.get("customer")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id")
        if customer_id:
            email = None
            details = session.get("customer_details") or {}
            if isinstance(details, dict):
                email = details.get("email")
            self.store.update_device_customer(device_id, stripe_customer_id=str(customer_id), email=email)

        sub_id = session.get("subscription")
        if not sub_id:
            return
        if isinstance(sub_id, dict):
            sub_id = sub_id.get("id")
        if not sub_id:
            return

        if settings.stripe_secret_key:
            sub = stripe.Subscription.retrieve(sub_id)
            self._upsert_from_stripe_subscription(device_id, sub)
        else:
            self.store.upsert_subscription(
                device_id=device_id,
                stripe_subscription_id=str(sub_id),
                stripe_customer_id=str(customer_id) if customer_id else None,
                status="active",
                price_id=None,
                current_period_end=None,
            )

    def _on_subscription_updated(self, sub: Any) -> None:
        sub = _as_dict(sub)
        device_id = (sub.get("metadata") or {}).get("device_id")
        if not device_id:
            existing = self.store.get_subscription_by_stripe_id(sub.get("id", ""))
            if existing:
                device_id = existing["device_id"]
        if not device_id:
            return
        self._upsert_from_stripe_subscription(device_id, sub)

    def _on_subscription_deleted(self, sub: Any) -> None:
        sub = _as_dict(sub)
        sub_id = sub.get("id")
        if sub_id:
            self.store.set_subscription_status(str(sub_id), "canceled")

    def _upsert_from_stripe_subscription(self, device_id: str, sub: Any) -> None:
        sub = _as_dict(sub)

        status = sub.get("status", "unknown")
        sub_id = sub.get("id")
        customer_id = sub.get("customer")
        period_end = sub.get("current_period_end")
        price_id = None
        items = (sub.get("items") or {}).get("data") or []
        if items:
            price = items[0].get("price") or {}
            price_id = price.get("id")

        if not sub_id:
            return

        self.store.upsert_subscription(
            device_id=device_id,
            stripe_subscription_id=str(sub_id),
            stripe_customer_id=str(customer_id) if customer_id else None,
            status=str(status),
            price_id=price_id,
            current_period_end=float(period_end) if period_end else None,
        )

    def verify_checkout_session(self, session_id: str, device_id: str) -> dict[str, Any]:
        """Success page: confirm session belongs to device and subscription is active."""
        if settings.stripe_demo_mode and session_id.startswith("demo_"):
            sub = self.store.get_active_subscription(device_id)
            return {"ok": bool(sub), "session_id": session_id}

        if not settings.stripe_secret_key:
            raise RuntimeError("FVD_STRIPE_SECRET_KEY is required")

        session = _as_dict(stripe.checkout.Session.retrieve(session_id, expand=["subscription"]))
        ref = session.get("client_reference_id") or (session.get("metadata") or {}).get("device_id")
        if ref and ref != device_id:
            return {"ok": False, "session_id": session_id, "error": "session_mismatch"}

        sub = session.get("subscription")
        if sub and hasattr(sub, "to_dict"):
            sub = sub.to_dict()
        if isinstance(sub, dict) and sub.get("status") in _ACTIVE_STATUSES:
            if ref:
                self._upsert_from_stripe_subscription(ref, sub)
            return {"ok": True, "session_id": session_id}

        return {"ok": self.is_pro(device_id), "session_id": session_id}


def _subscription_payload(sub: dict[str, Any] | None) -> dict[str, Any] | None:
    if not sub:
        return None
    return {
        "status": sub.get("status"),
        "price_id": sub.get("price_id"),
        "current_period_end": sub.get("current_period_end"),
        "stripe_subscription_id": sub.get("stripe_subscription_id"),
    }
