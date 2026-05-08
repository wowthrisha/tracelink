import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.group import DocumentGroup
from app.models.document import Document
from app.schemas.group import GroupCreateRequest, GroupUpdateRequest, GroupResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _group_to_response(group: DocumentGroup, doc_count: int) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        name=group.name,
        color=group.color,
        description=group.description,
        document_count=doc_count,
        created_at=group.created_at,
    )


@router.get("", response_model=dict)
async def list_groups(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(DocumentGroup).order_by(DocumentGroup.name))
    groups = result.scalars().all()

    out = []
    for g in groups:
        count_result = await db.execute(
            select(func.count()).select_from(Document).where(Document.group_id == g.id)
        )
        doc_count = count_result.scalar() or 0
        out.append(_group_to_response(g, doc_count))

    return {"groups": out}


@router.post("", status_code=201, response_model=GroupResponse)
async def create_group(
    payload: GroupCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Check unique name
    existing = await db.execute(
        select(DocumentGroup).where(DocumentGroup.name == payload.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Group name already exists")

    group = DocumentGroup(
        name=payload.name,
        color=payload.color or "#6366f1",
        description=payload.description,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return _group_to_response(group, 0)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.group_id == group_id)
    )
    doc_count = count_result.scalar() or 0
    return _group_to_response(group, doc_count)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if payload.name is not None:
        # Check unique name
        existing = await db.execute(
            select(DocumentGroup).where(
                DocumentGroup.name == payload.name,
                DocumentGroup.id != group_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Group name already exists")
        group.name = payload.name

    if payload.color is not None:
        group.color = payload.color
    if "description" in payload.model_fields_set:
        group.description = payload.description

    await db.commit()
    await db.refresh(group)

    count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.group_id == group_id)
    )
    doc_count = count_result.scalar() or 0
    return _group_to_response(group, doc_count)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Unassign all documents in this group
    docs_result = await db.execute(
        select(Document).where(Document.group_id == group_id)
    )
    for doc in docs_result.scalars().all():
        doc.group_id = None

    await db.delete(group)
    await db.commit()


@router.put("/{group_id}/documents", response_model=dict)
async def assign_documents_to_group(
    group_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Assign a list of document IDs to a group. Pass document_ids: [uuid, ...]."""
    result = await db.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    user_uuid = uuid.UUID(user["user_id"])
    doc_ids = body.get("document_ids", [])
    assigned = 0
    for doc_id in doc_ids:
        try:
            doc_uuid = uuid.UUID(str(doc_id))
        except ValueError:
            continue
        doc_result = await db.execute(
            select(Document).where(Document.id == doc_uuid, Document.user_id == user_uuid)
        )
        doc = doc_result.scalar_one_or_none()
        if doc:
            doc.group_id = group_id
            assigned += 1

    await db.commit()
    return {"assigned": assigned, "group_id": str(group_id)}


@router.delete("/{group_id}/documents/{document_id}", status_code=204)
async def remove_document_from_group(
    group_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Remove a single document from its group."""
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != uuid.UUID(user["user_id"]):
        raise HTTPException(status_code=403, detail="Not authorized to modify this document")
    if doc.group_id != group_id:
        raise HTTPException(status_code=400, detail="Document is not in this group")
    doc.group_id = None
    await db.commit()
