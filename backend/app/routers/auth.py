"""
Auth registration endpoint — bypasses Supabase email confirmation.

Uses the Supabase Admin API (service role key) to create email-confirmed
users directly, then signs them in and returns an access token.

Requires SUPABASE_SERVICE_ROLE_KEY in environment.
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    email: str
    password: str


async def _confirm_existing_user(
    client: httpx.AsyncClient, base: str, admin_headers: dict, email: str
) -> bool:
    """
    Find an existing unconfirmed Supabase user by email and mark them confirmed.
    Returns True if the user was found and patched, False otherwise.
    """
    list_resp = await client.get(
        f"{base}/auth/v1/admin/users",
        headers=admin_headers,
        params={"per_page": 1000},
    )
    if not list_resp.is_success:
        return False
    users = list_resp.json().get("users", [])
    uid = next(
        (u["id"] for u in users if u.get("email", "").lower() == email.lower()),
        None,
    )
    if not uid:
        return False
    patch_resp = await client.put(
        f"{base}/auth/v1/admin/users/{uid}",
        headers=admin_headers,
        json={"email_confirm": True},
    )
    return patch_resp.is_success


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """
    Create a Supabase user with email pre-confirmed (no confirmation email sent).

    Returns an access_token the frontend can use immediately.
    Requires SUPABASE_SERVICE_ROLE_KEY to be set.
    """
    if not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=503,
            detail="Email-free registration is not configured. Ask the admin to set SUPABASE_SERVICE_ROLE_KEY.",
        )
    if not settings.supabase_url:
        raise HTTPException(status_code=503, detail="Supabase not configured.")

    svc_key = settings.supabase_service_role_key
    base = settings.supabase_url.rstrip("/")
    admin_headers = {
        "Content-Type": "application/json",
        "apikey": svc_key,
        "Authorization": f"Bearer {svc_key}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: create user via Admin API with email pre-confirmed
        create_resp = await client.post(
            f"{base}/auth/v1/admin/users",
            headers=admin_headers,
            json={
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
            },
        )
        create_data = create_resp.json()

        if not create_resp.is_success:
            msg = create_data.get("msg") or create_data.get("message") or ""
            already_exists = (
                "already registered" in msg.lower()
                or "already been registered" in msg.lower()
                or create_resp.status_code == 422
            )
            if already_exists:
                # User exists but may be unconfirmed — find and confirm them
                confirmed = await _confirm_existing_user(client, base, admin_headers, body.email)
                if not confirmed:
                    raise HTTPException(
                        status_code=409,
                        detail="An account with this email already exists. Please sign in.",
                    )
                logger.info("auth.register: confirmed existing unconfirmed user %s", body.email)
            else:
                raise HTTPException(status_code=400, detail=msg or "Registration failed")
        else:
            logger.info("auth.register: created user %s", body.email)

        # Step 2: sign in immediately to get access token
        token_resp = await client.post(
            f"{base}/auth/v1/token?grant_type=password",
            headers={
                "Content-Type": "application/json",
                "apikey": settings.supabase_anon_key,
            },
            json={"email": body.email, "password": body.password},
        )
        token_data = token_resp.json()

        if not token_resp.is_success or not token_data.get("access_token"):
            raise HTTPException(
                status_code=500,
                detail="Account created but sign-in failed. Please sign in manually.",
            )

        return JSONResponse({"access_token": token_data["access_token"]})
