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
from app.utils.crypto import hash_value, mask_email

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
        time_spent_ms: Optional[int] = None,
        commit: bool = True,
    ) -> AccessEvent:
        """Add an access event.

        Pass commit=False when the caller will issue its own db.commit() — this
        lets callers batch the analytics write with other pending DB changes into
        a single round-trip instead of an extra commit per event.

        time_spent_ms: milliseconds the viewer spent on the page before this
        event was fired. Used for time-on-page analytics (Action 12).
        """
        event = AccessEvent(
            link_id=link_id,
            event_type=event_type,
            page_number=page_number,
            time_spent_ms=time_spent_ms,
            viewer_email=mask_email(viewer_email) if viewer_email else None,
            ip_hash=hash_value(ip) if ip else None,
            user_agent_hash=hash_value(user_agent) if user_agent else None,
            session_id=session_id[:8] if session_id else None,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.add(event)
        if commit:
            await db.commit()
            # db.refresh(event) is intentionally omitted: no caller uses server-
            # generated fields from the returned event (id is client-side UUID4;
            # return value is ignored at every call site).  Removing this SELECT
            # eliminates one extra DB round-trip per page request under load.
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

        # total_groups — scoped to this user
        total_groups_q = select(func.count()).select_from(DocumentGroup)
        if user_id is not None:
            total_groups_q = total_groups_q.where(DocumentGroup.user_id == user_id)
        total_groups = (await db.execute(total_groups_q)).scalar() or 0

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

        # views_last_7_days — SQL GROUP BY DATE avoids fetching all raw timestamps
        week_start = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if scoped_link_ids is not None and not scoped_link_ids:
            date_counts: dict = {}
        else:
            week_q = (
                select(
                    func.date(AccessEvent.created_at).label("day"),
                    func.count().label("cnt"),
                )
                .where(
                    AccessEvent.event_type == "opened",
                    AccessEvent.created_at >= week_start,
                )
                .group_by(func.date(AccessEvent.created_at))
            )
            if scoped_link_ids:
                week_q = week_q.where(AccessEvent.link_id.in_(scoped_link_ids))
            # func.date() returns a str in SQLite and a date object in PostgreSQL;
            # str() normalises both to "YYYY-MM-DD" for the dict key.
            date_counts = {str(row.day): row.cnt for row in (await db.execute(week_q)).all()}

        views_7_days = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_str = day_start.strftime("%Y-%m-%d")
            views_7_days.append({"date": date_str, "count": date_counts.get(date_str, 0)})

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
        limit: int = 100,
        offset: int = 0,
    ) -> tuple:
        """Returns (documents: list, total: int)."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)

        base_filter = []
        if group_id:
            base_filter.append(Document.group_id == group_id)
        if user_id is not None:
            base_filter.append(Document.user_id == user_id)

        count_q = select(func.count()).select_from(Document)
        if base_filter:
            count_q = count_q.where(*base_filter)
        total = (await db.execute(count_q)).scalar() or 0

        query = select(Document)
        if base_filter:
            query = query.where(*base_filter)
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        documents = result.scalars().all()

        if not documents:
            return [], total

        doc_ids = [d.id for d in documents]

        # Batch: group info for all referenced groups (1 query)
        group_ids = {d.group_id for d in documents if d.group_id}
        groups: dict = {}
        if group_ids:
            grp_result = await db.execute(
                select(DocumentGroup).where(DocumentGroup.id.in_(group_ids))
            )
            groups = {g.id: g for g in grp_result.scalars().all()}

        # Batch: all link IDs per document (1 query)
        links_result = await db.execute(
            select(ShareLink.id, ShareLink.document_id)
            .where(ShareLink.document_id.in_(doc_ids))
        )
        doc_link_ids: dict = {d.id: [] for d in documents}
        all_link_ids: list = []
        for row in links_result.all():
            doc_link_ids[row.document_id].append(row.id)
            all_link_ids.append(row.id)

        # Batch event aggregates — one GROUP BY query per metric (6 queries total)
        def _by_link(rows) -> dict:
            return {row[0]: row[1] for row in rows}

        if all_link_ids:
            views_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.event_type == "opened")
                .group_by(AccessEvent.link_id)
            )).all())

            sessions_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count(AccessEvent.session_id.distinct()).label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.session_id.isnot(None))
                .group_by(AccessEvent.link_id)
            )).all())

            blocked_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)))
                .group_by(AccessEvent.link_id)
            )).all())

            blocked24h_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(
                    AccessEvent.link_id.in_(all_link_ids),
                    AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
                    AccessEvent.created_at >= last_24h,
                )
                .group_by(AccessEvent.link_id)
            )).all())

            completions_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.event_type == "completed")
                .group_by(AccessEvent.link_id)
            )).all())

            pageviews_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.event_type == "page_viewed")
                .group_by(AccessEvent.link_id)
            )).all())
        else:
            views_by_link = sessions_by_link = blocked_by_link = {}
            blocked24h_by_link = completions_by_link = pageviews_by_link = {}

        # Aggregate per document in Python
        analytics = []
        for doc in documents:
            link_ids = doc_link_ids[doc.id]
            grp = groups.get(doc.group_id) if doc.group_id else None

            total_views = sum(views_by_link.get(lid, 0) for lid in link_ids)
            unique_sessions = sum(sessions_by_link.get(lid, 0) for lid in link_ids)
            blocked_attempts = sum(blocked_by_link.get(lid, 0) for lid in link_ids)
            blocked_24h = sum(blocked24h_by_link.get(lid, 0) for lid in link_ids)
            completions = sum(completions_by_link.get(lid, 0) for lid in link_ids)
            page_views = sum(pageviews_by_link.get(lid, 0) for lid in link_ids)

            completion_rate = (completions / total_views * 100) if total_views > 0 else 0.0

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
                "group_name": grp.name if grp else None,
                "group_color": grp.color if grp else None,
                "total_views": total_views,
                "unique_sessions": unique_sessions,
                "completion_rate_pct": round(completion_rate, 1),
                "blocked_attempts": blocked_attempts,
                "risk_score": risk_score,
            })

        return analytics, total

    async def get_page_heatmap(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[dict]:
        """
        Aggregate page_viewed events by page number for a specific document.

        Returns None if the document doesn't exist or belongs to another user.
        Result: {document_id, page_count, total_views, pages: [{page, views, pct, avg_time_sec}]}
        Uses existing analytics data only — no new tracking events or DB tables.
        """
        # Security: verify document ownership
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return None

        # Get all link IDs for this document
        links_result = await db.execute(
            select(ShareLink.id).where(ShareLink.document_id == document_id)
        )
        link_ids = [r[0] for r in links_result.all()]
        if not link_ids:
            return {
                "document_id": str(document_id),
                "filename": doc.filename,
                "page_count": doc.page_count or 0,
                "total_views": 0,
                "pages": [],
            }

        # Aggregate page_viewed events: COUNT per page + AVG time_spent_ms
        heatmap_q = (
            select(
                AccessEvent.page_number,
                func.count().label("views"),
                func.avg(AccessEvent.time_spent_ms).label("avg_ms"),
            )
            .where(
                AccessEvent.link_id.in_(link_ids),
                AccessEvent.event_type == "page_viewed",
                AccessEvent.page_number.isnot(None),
            )
            .group_by(AccessEvent.page_number)
            .order_by(AccessEvent.page_number)
        )
        rows = (await db.execute(heatmap_q)).all()
        total_views = sum(r.views for r in rows)
        pages = [
            {
                "page": r.page_number,
                "views": r.views,
                "pct": round(r.views / total_views * 100, 1) if total_views > 0 else 0.0,
                "avg_time_sec": round((r.avg_ms or 0.0) / 1000.0, 1),
            }
            for r in rows
        ]
        return {
            "document_id": str(document_id),
            "filename": doc.filename,
            "page_count": doc.page_count or 0,
            "total_views": total_views,
            "pages": pages,
        }

    async def get_group_analytics(
        self, db: AsyncSession, user_id: Optional[uuid.UUID] = None,
        limit: int = 100, offset: int = 0,
    ) -> tuple:
        """Aggregate analytics at the group level. Returns (groups: list, total: int)."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)

        # Security: only return this user's groups
        count_q = select(func.count()).select_from(DocumentGroup)
        if user_id is not None:
            count_q = count_q.where(DocumentGroup.user_id == user_id)
        total = (await db.execute(count_q)).scalar() or 0

        groups_q = select(DocumentGroup).order_by(DocumentGroup.name)
        if user_id is not None:
            groups_q = groups_q.where(DocumentGroup.user_id == user_id)
        groups_q = groups_q.offset(offset).limit(limit)
        groups_result = await db.execute(groups_q)
        groups = groups_result.scalars().all()

        if not groups:
            return [], total

        group_ids = [g.id for g in groups]

        # Batch: doc counts and IDs per group (1 query)
        docs_q = select(Document.id, Document.group_id).where(Document.group_id.in_(group_ids))
        if user_id is not None:
            docs_q = docs_q.where(Document.user_id == user_id)
        docs_result = await db.execute(docs_q)
        group_doc_ids: dict = {gid: [] for gid in group_ids}
        all_doc_ids: list = []
        for row in docs_result.all():
            group_doc_ids[row.group_id].append(row.id)
            all_doc_ids.append(row.id)

        if not all_doc_ids:
            return [
                {
                    "group_id": g.id, "group_name": g.name, "group_color": g.color,
                    "document_count": 0, "total_views": 0, "unique_sessions": 0,
                    "blocked_attempts": 0, "risk_score": "LOW", "active_links": 0,
                }
                for g in groups
            ], total

        # Batch: link IDs per document (1 query)
        links_result = await db.execute(
            select(ShareLink.id, ShareLink.document_id, ShareLink.revoked_at, ShareLink.expires_at)
            .where(ShareLink.document_id.in_(all_doc_ids))
        )
        doc_link_rows = links_result.all()
        doc_link_ids: dict = {d: [] for d in all_doc_ids}
        all_link_ids: list = []
        active_link_ids: set = set()
        for row in doc_link_rows:
            doc_link_ids[row.document_id].append(row.id)
            all_link_ids.append(row.id)
            # Determine active at query time
            if row.revoked_at is None:
                exp = row.expires_at
                if exp is None or (exp.replace(tzinfo=timezone.utc) if exp.tzinfo is None else exp) > now:
                    active_link_ids.add(row.id)

        # Batch event aggregates — one GROUP BY query per metric (4 queries)
        def _by_link(rows) -> dict:
            return {row[0]: row[1] for row in rows}

        if all_link_ids:
            views_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.event_type == "opened")
                .group_by(AccessEvent.link_id)
            )).all())

            sessions_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count(AccessEvent.session_id.distinct()).label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.session_id.isnot(None))
                .group_by(AccessEvent.link_id)
            )).all())

            blocked_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(AccessEvent.link_id.in_(all_link_ids), AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)))
                .group_by(AccessEvent.link_id)
            )).all())

            blocked24h_by_link = _by_link((await db.execute(
                select(AccessEvent.link_id, func.count().label("c"))
                .where(
                    AccessEvent.link_id.in_(all_link_ids),
                    AccessEvent.event_type.in_(list(BLOCKED_EVENT_TYPES)),
                    AccessEvent.created_at >= last_24h,
                )
                .group_by(AccessEvent.link_id)
            )).all())
        else:
            views_by_link = sessions_by_link = blocked_by_link = blocked24h_by_link = {}

        # Aggregate per group in Python
        analytics = []
        for group in groups:
            doc_ids = group_doc_ids[group.id]
            link_ids = [lid for did in doc_ids for lid in doc_link_ids.get(did, [])]

            total_views = sum(views_by_link.get(lid, 0) for lid in link_ids)
            unique_sessions = sum(sessions_by_link.get(lid, 0) for lid in link_ids)
            blocked_attempts = sum(blocked_by_link.get(lid, 0) for lid in link_ids)
            blocked_24h = sum(blocked24h_by_link.get(lid, 0) for lid in link_ids)
            active_links = sum(1 for lid in link_ids if lid in active_link_ids)

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

        return analytics, total
