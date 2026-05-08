import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class GroupCreateRequest(BaseModel):
    name: str
    color: Optional[str] = "#6366f1"
    description: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if v and (len(v) != 7 or not v.startswith("#")):
            raise ValueError("color must be a 7-character hex string like #6366f1")
        return v


class GroupUpdateRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v and (len(v) != 7 or not v.startswith("#")):
            raise ValueError("color must be a 7-character hex string like #6366f1")
        return v


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    description: Optional[str]
    document_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
