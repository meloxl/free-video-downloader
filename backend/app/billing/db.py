from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from ..settings import settings

_ACTIVE_STATUSES = frozenset({"active", "trialing"})


def _now() -> float:
    return time.time()


class BillingStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.billing_db_path

    def init(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    stripe_customer_id TEXT,
                    email TEXT
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    stripe_subscription_id TEXT UNIQUE,
                    stripe_customer_id TEXT,
                    status TEXT NOT NULL,
                    price_id TEXT,
                    current_period_end REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES devices(id)
                );

                CREATE INDEX IF NOT EXISTS idx_subscriptions_device
                    ON subscriptions(device_id);

                CREATE TABLE IF NOT EXISTS stripe_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    processed_at REAL NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_device(self, device_id: str) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
            if row:
                return
            conn.execute(
                "INSERT INTO devices (id, created_at) VALUES (?, ?)",
                (device_id, _now()),
            )
            conn.commit()

    def update_device_customer(self, device_id: str, *, stripe_customer_id: str, email: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE devices
                SET stripe_customer_id = COALESCE(?, stripe_customer_id),
                    email = COALESCE(?, email)
                WHERE id = ?
                """,
                (stripe_customer_id, email, device_id),
            )
            conn.commit()

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
            return dict(row) if row else None

    def upsert_subscription(
        self,
        *,
        device_id: str,
        stripe_subscription_id: str,
        stripe_customer_id: str | None,
        status: str,
        price_id: str | None,
        current_period_end: float | None,
    ) -> None:
        t = _now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM subscriptions WHERE stripe_subscription_id = ?",
                (stripe_subscription_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE subscriptions
                    SET device_id = ?, stripe_customer_id = ?, status = ?,
                        price_id = ?, current_period_end = ?, updated_at = ?
                    WHERE stripe_subscription_id = ?
                    """,
                    (
                        device_id,
                        stripe_customer_id,
                        status,
                        price_id,
                        current_period_end,
                        t,
                        stripe_subscription_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO subscriptions (
                        device_id, stripe_subscription_id, stripe_customer_id,
                        status, price_id, current_period_end, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        device_id,
                        stripe_subscription_id,
                        stripe_customer_id,
                        status,
                        price_id,
                        current_period_end,
                        t,
                        t,
                    ),
                )
            conn.commit()

    def get_active_subscription(self, device_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM subscriptions
                WHERE device_id = ? AND status IN ('active', 'trialing')
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()
            return dict(row) if row else None

    def is_pro(self, device_id: str) -> bool:
        sub = self.get_active_subscription(device_id)
        return sub is not None and sub.get("status") in _ACTIVE_STATUSES

    def mark_event_processed(self, event_id: str, event_type: str) -> bool:
        """Return True if this event was newly recorded; False if duplicate."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT event_id FROM stripe_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO stripe_events (event_id, event_type, processed_at) VALUES (?, ?, ?)",
                (event_id, event_type, _now()),
            )
            conn.commit()
            return True

    def set_subscription_status(self, stripe_subscription_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE subscriptions SET status = ?, updated_at = ? WHERE stripe_subscription_id = ?",
                (status, _now(), stripe_subscription_id),
            )
            conn.commit()

    def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE stripe_subscription_id = ?",
                (stripe_subscription_id,),
            ).fetchone()
            return dict(row) if row else None
