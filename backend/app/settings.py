from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FVD_", case_sensitive=False)

    enable_cookies: bool = Field(default=False)
    admin_token: str = Field(default="")
    demo_mode: bool = Field(default=False)

    ttl_seconds: int = Field(default=3600, ge=60)
    max_urls_per_request: int = Field(default=20, ge=1, le=200)
    max_active_jobs_per_ip: int = Field(default=3, ge=1, le=50)

    download_root: str = Field(default="/tmp/fvd")
    cleanup_interval_seconds: int = Field(default=300, ge=30)

    enable_ai_summary: bool = Field(default=True)
    summary_only_bilibili: bool = Field(default=True)

    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_model: str = Field(default="deepseek-chat")

    max_summary_workers: int = Field(default=2, ge=1, le=16)

    # Stripe billing (Pro subscription)
    public_base_url: str = Field(default="http://localhost:8000")
    billing_db_path: str = Field(default="/tmp/fvd/billing.db")
    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    stripe_price_monthly: str = Field(default="")
    stripe_price_yearly: str = Field(default="")
    stripe_demo_mode: bool = Field(default=False)
    pro_max_active_jobs_per_ip: int = Field(default=10, ge=1, le=100)


settings = Settings()
