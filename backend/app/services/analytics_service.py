import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from app.models.document import Document
from app.models.group import DocumentGroup
from app.models.link import ShareLink
from app.models.event import AccessEvent
from app.utils.crypto import hash_value

BLOCKED_EVENT_TYPES = {
    "print_attempt",
    "copy_attempt",
    "right_click_attempt",
    "download_attempt",
}


class AnalyticsService:
    async def log_event(
        self,
        db: AsyncSession,
        link_id: uuid.UUID,
        event_type: str,
        page_number: Optional[int] = None,
        viewer_email: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AccessEvent:
        event = AccessEvent(
            link_id=link_id,
            event_type=event_type,
            page_number=page_number,
            viewer_email=viewer_email,
            ip_hash=hash_value(ip) if ip else None,
            user_agent_hash=hash_value(user_agent) if user_agent else None,
            session_id=session_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def get_overview(
        self, db: AsyncSession, user_id: Optional[uuid.UUID] = None
    ) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Pre-compute user-scoped link IDs when filtering by user
        scoped_link_ids: Optional[list] = None
        if user_id is not None:
            doc_ids_r = await db.execute(
                select(Document.id).where(Document.user_id == user_id)
            )
            doc_ids = [r[0] for r in doc_ids_r.all()]
            if doc_ids:
                link_ids_r = await db.execute(
                    select(ShareLink.id).where(ShareLink.document_id.in_(doc_ids))
                )
                scoped_link_ids = [r[0] for r in link_ids_r.all()]
            else:
                scoped_link_ids = []

        # total_documents
        doc_q = select(func.count()).select_from(Document)
        if user_id is not None:
            doc_q = doc_q.where(Document.user_id == user_id)
        total_documents = (await db.execute(doc_q)).scalar() or 0

        # total_groups (organisational — not user-scoped)
        total_groups_result = await db.execute(select(func.count()).select_from(DocumentGroup))
        total_groups = total_groups_result.scalar() or 0

        # helper: execute a count query scoped to user's links (or all links)
        async def _count_events(*extra_filters):
            if scoped_link_ids is not None and not scoped_link_ids:
                return 0
            q = select(func.count()).select_from(AccessEvent).where(*extra_filters)
            if scoped_link_ids:
                q = q.where(AccessEvent.link_id.in_(scoped_link_ids))
            return (await db.execute(q)).scalar() or 0

        async def _count_links(*extra_filters):
            if scoped_link_ids is not None and not scoped_link_ids:
                return 0
            q = select(func.count()).select_from(ShareLink).where(*extra_filters)
            if scoped_link_ids:
                q = q.where(ShareLink.id.in_(scoped_link_ids))
            return (await db.execute(q)).scalar() or 0

        # total_views_today
        total_views_today = await _count_events(
            AccessEvent.event_type == "opened",
            AccessEvent.created_at >= today_start,
        )

        # active_links: not revoked, not expired
        active_links = await _count_links(
            ShareLink.revoked_at.is_(None),
            or_(ShareLink.expires_at.is_(None), ShareLink.expires_at > now),
        )

        # blocked_attempts_today
        blocked_attempts_today = await _count_events(
            AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
            AccessEvent.created_at >= today_start,
        )

        # expiring_soon_count
        fourteen_days_from_now = now + timedelta(days=14)
        expiring_soon_count = await _count_links(
            ShareLink.revoked_at.is_(None),
            ShareLink.expires_at.isnot(None),
            ShareLink.expires_at <= fourteen_days_from_now,
            ShareLink.expires_at > now,
        )

        # views_last_7_days
        views_7_days = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)
            count = await _count_events(
                AccessEvent.event_type == "opened",
                AccessEvent.created_at >= day_start,
                AccessEvent.created_at < day_end,
            )
            views_7_days.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "count": count,
            })

        return {
            "total_documents": total_documents,
            "total_groups": total_groups,
            "total_views_today": total_views_today,
            "active_links": active_links,
            "expiring_soon_count": expiring_soon_count,
            "blocked_attempts_today": blocked_attempts_today,
            "views_last_7_days": views_7_days,
        }

    async def get_document_analytics(
        self,
        db: AsyncSession,
        group_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> list:
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)

        query = select(Document)
        if group_id:
            query = query.where(Document.group_id == group_id)
        if user_id is not None:
            query = query.where(Document.user_id == user_id)

        result = await db.execute(query)
        documents = result.scalars().all()

        analytics = []
        for doc in documents:
            # Get all links for this document
            links_result = await db.execute(
                select(ShareLink).where(ShareLink.document_id == doc.id)
            )
            links = links_result.scalars().all()
            link_ids = [l.id for l in links]

            # Fetch group info
            group_name = None
            group_color = None
            if doc.group_id:
                grp_result = await db.execute(
                    select(DocumentGroup).where(DocumentGroup.id == doc.group_id)
                )
                grp = grp_result.scalar_one_or_none()
                if grp:
                    group_name = grp.name
                    group_color = grp.color

            if not link_ids:
                analytics.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "group_id": doc.group_id,
                    "group_name": group_name,
                    "group_color": group_color,
                    "total_views": 0,
                    "unique_sessions": 0,
                    "avg_time_on_page_sec": 0,
                    "completion_rate_pct": 0.0,
                    "blocked_attempts": 0,
                    "risk_score": "LOW",
                })
                continue

            # total_views
            tv_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type == "opened",
                    )
                )
            )
            total_views = tv_result.scalar() or 0

            # unique_sessions
            us_result = await db.execute(
                select(func.count(AccessEvent.session_id.distinct())).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.session_id.isnot(None),
                    )
                )
            )
            unique_sessions = us_result.scalar() or 0

            # blocked_attempts (all time)
            ba_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
                    )
                )
            )
            blocked_attempts = ba_result.scalar() or 0

            # blocked last 24h for risk scoring
            ba_24h_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
                        AccessEvent.created_at >= last_24h,
                    )
                )
            )
            blocked_24h = ba_24h_result.scalar() or 0

            # completion_rate: completed / opened
            comp_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type == "completed",
                    )
                )
            )
            completions = comp_result.scalar() or 0
            completion_rate = (completions / total_views * 100) if total_views > 0 else 0.0

            # avg_time_on_page_sec: 30s per page_viewed event / unique_sessions
            pv_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type == "page_viewed",
                    )
                )
            )
            page_views = pv_result.scalar() or 0
            avg_time_on_page_sec = (page_views * 30.0) / unique_sessions if unique_sessions > 0 else 0.0

            # risk_score
            if blocked_24h > 5:
                risk_score = "HIGH"
            elif blocked_24h > 2:
                risk_score = "MED"
            else:
                risk_score = "LOW"

            analytics.append({
                "id": doc.id,
                "filename": doc.filename,
                "group_id": doc.group_id,
                "group_name": group_name,
                "group_color": group_color,
                "total_views": total_views,
                "unique_sessions": unique_sessions,
                "avg_time_on_page_sec": round(avg_time_on_page_sec),
                "completion_rate_pct": round(completion_rate, 1),
                "blocked_attempts": blocked_attempts,
                "risk_score": risk_score,
            })

        return analytics

    async def get_group_analytics(
        self, db: AsyncSession, user_id: Optional[uuid.UUID] = None
    ) -> list:
        """Aggregate analytics at the group level."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)

        groups_result = await db.execute(select(DocumentGroup).order_by(DocumentGroup.name))
        groups = groups_result.scalars().all()

        analytics = []
        for group in groups:
            # Documents in this group (scoped to user if provided)
            docs_q = select(Document).where(Document.group_id == group.id)
            if user_id is not None:
                docs_q = docs_q.where(Document.user_id == user_id)
            docs_result = await db.execute(docs_q)
            docs = docs_result.scalars().all()
            doc_ids = [d.id for d in docs]

            if not doc_ids:
                analytics.append({
                    "group_id": group.id,
                    "group_name": group.name,
                    "group_color": group.color,
                    "document_count": 0,
                    "total_views": 0,
                    "unique_sessions": 0,
                    "blocked_attempts": 0,
                    "risk_score": "LOW",
                    "active_links": 0,
                })
                continue

            # All links for these documents
            links_result = await db.execute(
                select(ShareLink.id).where(ShareLink.document_id.in_(doc_ids))
            )
            link_ids = [row[0] for row in links_result.all()]

            if not link_ids:
                analytics.append({
                    "group_id": group.id,
                    "group_name": group.name,
                    "group_color": group.color,
                    "document_count": len(doc_ids),
                    "total_views": 0,
                    "unique_sessions": 0,
                    "blocked_attempts": 0,
                    "risk_score": "LOW",
                    "active_links": 0,
                })
                continue

            # total_views
            tv_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type == "opened",
                    )
                )
            )
            total_views = tv_result.scalar() or 0

            # unique_sessions
            us_result = await db.execute(
                select(func.count(AccessEvent.session_id.distinct())).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.session_id.isnot(None),
                    )
                )
            )
            unique_sessions = us_result.scalar() or 0

            # blocked_attempts (all time)
            ba_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
                    )
                )
            )
            blocked_attempts = ba_result.scalar() or 0

            # blocked last 24h for risk
            ba_24h_result = await db.execute(
                select(func.count()).select_from(AccessEvent).where(
                    and_(
                        AccessEvent.link_id.in_(link_ids),
                        AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
                        AccessEvent.created_at >= last_24h,
                    )
                )
            )
            blocked_24h = ba_24h_result.scalar() or 0

            # active links
            active_links_result = await db.execute(
                select(func.count()).select_from(ShareLink).where(
                    and_(
                        ShareLink.id.in_(link_ids),
                        ShareLink.revoked_at.is_(None),
                        or_(ShareLink.expires_at.is_(None), ShareLink.expires_at > now),
                    )
                )
            )
            active_links = active_links_result.scalar() or 0

            if blocked_24h > 5:
                risk_score = "HIGH"
            elif blocked_24h > 2:
                risk_score = "MED"
            else:
                risk_score = "LOW"

            analytics.append({
                "group_id": group.id,
                "group_name": group.name,
                "group_color": group.color,
                "document_count": len(doc_ids),
                "total_views": total_views,
                "unique_sessions": unique_sessions,
                "blocked_attempts": blocked_attempts,
                "risk_score": risk_score,
                "active_links": active_links,
            })

        return analytics
