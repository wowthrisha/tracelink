# Documentation Maturity — Sprint V7.0 (Phase 7)

Builds on `ENGINEERING_GOVERNANCE.md`'s (V6.0) documentation-duplication catalogue rather than re-deriving it. This document adds two things V6.0 didn't cover: a diagram inventory/staleness check, and a concrete, ready-to-execute merge plan for the one consolidation that's furthest along.

## Diagram inventory

No image-based diagrams exist anywhere in the repo (confirmed by search) — every diagram is ASCII art in Markdown fences. No Mermaid/PlantUML either.

| Diagram | Location | Status |
|---|---|---|
| System Components, Viewer DRM Session Lifecycle | `docs/architecture/ARCHITECTURE.md` | **Stale** — says "25 Alembic migr." (actual: 27), omits the Reading Intelligence Engine and 6 real tables entirely, and has two outright wrong table names (`org_members`→should be `org_memberships`; `webhook_configs`→should be `webhook_endpoints`) plus one nonexistent table (`annotation_threads`). |
| System Architecture, Frontend Component Graph, Data Flow (Upload/View) | `docs/architecture/OVERVIEW.md` | **Mixed** — says "26 Alembic migrations" (also stale, and disagrees with ARCHITECTURE.md's "25"). The Frontend Component Graph is largely current (correctly includes Organizations-era screens). Reading Intelligence Engine is under-represented — mentioned only as a vague "AI-ready insights surface," with no `ReadingStatusBar`, `useReadingAnalytics`, or the `/api/reading/*` router anywhere in the diagrams. |
| System Components, Data Flow | `docs/reading_analytics/READING_ANALYTICS_ARCHITECTURE.md` | **Current and accurate** — verified against code: correctly lists all 6 actual endpoints, all 3 actual models, and migration 026. This is the one diagram in the entire repo confirmed fully up to date, and not coincidentally it's exactly the subsystem missing from the two root diagrams above. |
| Directory-tree diagrams | `docs/development/DEVELOPER_GUIDE.md`, `docs/governance/FINAL_REPOSITORY_STRUCTURE.md` | File-layout diagrams, not architecture/data-flow — out of scope for the staleness check above. |
| 3 historical diagrams | `archive/legacy-traceview/`, `archive/sprint5-6/frontend-docs/` | Appropriately archived, correctly not presented as current — no action needed. |

## The real problem is worse than staleness: two docs actively contradict each other

`ARCHITECTURE.md` and `OVERVIEW.md` don't just cover different ground — they give **conflicting factual accounts** of the same mechanisms, which a reader has no way to know without checking the source:

1. **Migration count**: 25 vs. 26 (both wrong; actual is 27).
2. **Watermark model**: ARCHITECTURE.md describes one forensic watermark applied at serve time. OVERVIEW.md describes two distinct stamps — a visible viewer watermark at serve time *and* a separate forensic stamp burned in at processing time. These are structurally different claims about how/when watermarking happens, not a detail-level difference.
3. **Cache TTL / revocation timing**: ARCHITECTURE.md states 30s for both session-validation and link-snapshot caches. OVERVIEW.md states 5s (session, citing ADR-004) and 10s (link). Direct numeric conflict on the same mechanism, with real operational consequences (an incident responder trusting the wrong number would misjudge how fast a revoked link actually stops being viewable).

**These must be resolved against actual source code before any merge** — not decided by picking whichever file "sounds more current." Not done this sprint (requires reading the watermarking/caching implementation and updating both the doc and this finding with the verified answer) — flagged as the top-priority documentation task, not attempted here to avoid guessing at a security-relevant number.

## Merge plan (ready to execute once the contradictions above are resolved)

Proposed canonical `docs/architecture/ARCHITECTURE.md` (retire `OVERVIEW.md` as a separate file), section by section:

1. **Overview** — ARCHITECTURE.md's tech-stack summary + OVERVIEW.md's date/version-stamp convention (adopt going forward; ARCHITECTURE.md currently has none).
2. **System Architecture Diagram** — merge the two box diagrams; keep ARCHITECTURE.md's middleware-stack detail, add OVERVIEW.md's Layer Summary table. Fix the migration count to 27 in the merged version.
3. **Frontend Component Graph** — from OVERVIEW.md verbatim, refreshed to name the Reading Intelligence Engine's actual components instead of the vague current placeholder text.
4. **Key Design Decisions (ADR index)** — from OVERVIEW.md verbatim (ARCHITECTURE.md has none).
5. **Authentication** — ARCHITECTURE.md's section + OVERVIEW.md's SAML/SSO mention (ADR-010), which ARCHITECTURE.md omits.
6. **Document Processing Pipeline / Upload Data Flow** — union: ARCHITECTURE.md's adapter-level detail + OVERVIEW.md's sidecar-extraction and status-transition detail, neither of which the other file has.
7. **Viewer Session Lifecycle / View Data Flow** — union: ARCHITECTURE.md's link-validation chain + OVERVIEW.md's cache-tier flow and event logging.
8. **Security Model** — merge only after resolving contradiction #2 above against actual watermarking code.
9. **Caching Strategy** — from ARCHITECTURE.md, with the TTL numbers corrected per contradiction #3's resolution.
10. **Database Schema** — from ARCHITECTURE.md, corrected: fix the two wrong table names, drop the nonexistent one, add the 6 missing tables (`reading_sessions`, `page_reading_events`, `document_complexity`, `document_groups`, `admin_audit_log`, `storage_snapshots`, `organizations`, `user_billing`, `viewer_profiles`). Ideally superseded once the still-missing canonical `docs/architecture/DATABASE.md` is written (per V6.0's `ENGINEERING_GOVERNANCE.md`).
11. **Observability** — from ARCHITECTURE.md verbatim (OVERVIEW.md has no equivalent).

## Broken references — reconfirmed, nothing new found

The one previously-known broken/archive-pointing reference (root `CHANGELOG.md`, now grown to line 140, still pointing into `archive/sprint5-6/frontend-docs/certification/`) is the only one that exists — a fresh full-repo check this sprint (README, CONTRIBUTING, DEVELOPER_GUIDE, and every other non-archived `.md` file) found every other link resolves correctly. `archive/README.md`'s 6 dead pointers (documented in V6.0) remain unfixed — still stale, not touched this sprint since it's a judgment call about whether the archive needs a live index at all vs. simply being deleted.

## Documentation maturity verdict

The doc *set* is comprehensive — there is a document for nearly every topic a mature engineering org would expect (runbook, incident response, backup/restore, deployment, ADRs, developer guide). The maturity gap is entirely about **canonicalization**, not coverage: too many point-in-time sprint/release reports were never retired once superseded, two of the most-read documents (the architecture docs) actively disagree with each other on facts an engineer would reasonably trust, and the one subsystem added most recently (Reading Intelligence Engine) is the one most poorly represented in the docs a new engineer is pointed to first.
