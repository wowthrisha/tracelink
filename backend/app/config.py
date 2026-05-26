from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://securedoc:password@localhost:5432/securedoc"
    test_database_url: str = "sqlite+aiosqlite:///./test_securedoc.db"
    # Migration URL overrides (see alembic/env.py for precedence logic)
    database_public_url: Optional[str] = None   # Railway public proxy URL for local migrations
    migration_database_url: Optional[str] = None  # Explicit override — beats everything

    # Storage
    storage_endpoint_url: Optional[str] = None
    storage_access_key_id: str = "test_key"
    storage_secret_access_key: str = "test_secret"
    storage_bucket_name: str = "securedoc-docs"
    storage_region: str = "us-east-1"
    storage_public_base_url: Optional[str] = None

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    # TTL for the Phase 4 Redis-backed page/thumbnail byte cache (seconds).
    # 3600 s = 1 hour; keeps hot pages in Redis well beyond typical session length.
    redis_page_cache_ttl_sec: int = 3600

    # JWT (internal share-link tokens)
    jwt_secret: str = "change_me_to_a_long_random_string_in_production"
    jwt_algorithm: str = "HS256"
    jwt_link_expire_hours: int = 24

    # Supabase (user authentication)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # App
    app_env: str = "development"
    allowed_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    max_upload_mb: int = 100
    max_pages_per_doc: int = 500
    watermark_opacity: float = 0.22
    page_tile_dpi: int = 150
    page_format: str = "WEBP"
    page_tile_quality: int = 85

    # Frontend share URL base
    app_public_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5501"

    # Stripe billing (all optional — billing disabled when key is empty)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro: str = ""  # Stripe Price ID for Pro plan

    # Plan limits
    free_plan_doc_limit: int = 10  # documents allowed on free plan (0 = unlimited)

    # Security
    # Salt for IP address hashing.  MUST be set to a secret random value in
    # production — the default is a placeholder that makes hashes reversible.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    ip_hash_salt: str = "securedoc_ip_salt_change_in_production"

    # Rasterizer timeout in seconds per document.  PDFs that take longer than
    # this are rejected with a deterministic error (prevents PDF-bomb DoS).
    rasterizer_timeout_sec: int = 300

    # Trusted proxy / Cloudflare settings
    # Set real_ip_header = "CF-Connecting-IP" when all traffic comes through Cloudflare.
    # Set trusted_proxy_depth = 1 for generic reverse proxies using X-Forwarded-For.
    # Leave both at defaults when running without a proxy.
    real_ip_header: str = ""
    trusted_proxy_depth: int = 0

    # Text document settings (Phase 5)
    # Lines served per chunk in the text viewer. 100 lines ≈ ~8 KB per request.
    text_lines_per_chunk: int = 100
    # Maximum size allowed for text file uploads (separate from max_upload_mb).
    max_text_size_mb: int = 10

    # Phase 7 — enterprise / performance / observability
    # Log a warning when a single share link has more than this many concurrent sessions.
    # This is detection-only — it never blocks access.
    max_concurrent_sessions_per_link: int = 50
    # Set True in production to emit JSON log lines for Grafana Loki / Datadog / CloudWatch.
    enable_json_logging: bool = False
    # Watermark angle variation per session: ±this many degrees from the base -32°.
    # Randomises placement slightly per session to deter composite-removal attacks.
    watermark_angle_jitter_deg: float = 5.0

    @property
    def max_text_size_bytes(self) -> int:
        return self.max_text_size_mb * 1024 * 1024

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
