import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    message: str


class DocumentPageMeta(BaseModel):
    page_number: int
    width_px: int
    height_px: int


class DocumentSummary(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    page_count: Optional[int]
    file_size_bytes: int
    created_at: datetime
    share_link_count: int
    total_views: int
    group_id: Optional[uuid.UUID] = None
    group_name: Optional[str] = None
    group_color: Optional[str] = None
    file_type: str = "pdf"

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentSummary):
    pages: List[DocumentPageMeta] = []


class DocumentStatusResponse(BaseModel):
    status: str
    page_count: Optional[int]
    error_message: Optional[str]
