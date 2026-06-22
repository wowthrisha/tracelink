import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel


class LinkCreateRequest(BaseModel):
    document_id: uuid.UUID
    label: Optional[str] = None
    password: Optional[str] = None
    allowed_emails: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    ip_allowlist: Optional[List[str]] = None
    max_views: Optional[int] = None
    max_concurrent_sessions: Optional[int] = None
    expires_at: Optional[datetime] = None
    permissions: Optional[Dict[str, bool]] = None


class LinkUpdateRequest(BaseModel):
    label: Optional[str] = None
    expires_at: Optional[datetime] = None
    max_views: Optional[int] = None
    max_concurrent_sessions: Optional[int] = None
    allowed_emails: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    ip_allowlist: Optional[List[str]] = None
    permissions: Optional[Dict[str, bool]] = None
    password: Optional[str] = None


class LinkResponse(BaseModel):
    id: uuid.UUID
    token: str
    share_url: str
    label: Optional[str]
    expires_at: Optional[datetime]
    max_views: Optional[int]
    view_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LinkSummary(BaseModel):
    id: uuid.UUID
    token: str
    share_url: str
    label: Optional[str]
    expires_at: Optional[datetime]
    max_views: Optional[int]
    view_count: int
    revoked_at: Optional[datetime]
    created_at: datetime
    is_active: bool
    has_password: bool
    permissions: Optional[Dict[str, bool]] = None
    allowed_emails: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    ip_allowlist: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class RevokeResponse(BaseModel):
    id: uuid.UUID
    revoked_at: Optional[datetime]
    message: str
