"""
Production-safe server runner.

Storage backend selection:
  - Default: real S3/Supabase storage (configured via STORAGE_* env vars)
  - Demo mode: set USE_DEMO_STORAGE=1 to use local disk at /tmp/securedoc_storage/
               (development only — requires APP_ENV=development)
"""
import os
import uvicorn

if os.getenv("USE_DEMO_STORAGE") == "1":
    import demo_storage_patch  # noqa: F401 — must be before app import

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
