# Risk Register
Sprint 4.5A — Production Blocker Elimination
Date: 2026-06-22

Status values: RESOLVED | OPEN | DEFERRED | ACCEPTED

---

## Resolved This Sprint

| ID | Severity | Title | Resolution | Commit |
|---|---|---|---|---|
| B-01 | HIGH | New Link button stub | Wired to createLink API | f0000fb |
| B-03 | HIGH | javascript: href XSS in LinksPanel | Protocol guard added | 3f31dff |
| B-04 | HIGH | Export CSV button stub | Client-side CSV generation | 79203c2 |
| B-02 | MEDIUM | Supabase anon key in git history | Reclassified — public key, live code clean | N/A |

---

## Open Risks (Deferred — Not Sprint 4.5A Scope)

| ID | Severity | Title | Source | Deferral Reason |
|---|---|---|---|---|
| R-01 | MEDIUM | Analytics range selector not forwarded to API | UI-004 from certification | Requires verifying backend accepts range param before wiring. No backend endpoint confirmed. Not a correctness defect — data is accurate, just unfiltered. |
| R-02 | MEDIUM | BillingScreen uses direct fetch() instead of SecureDocAPI | UI-006 from certification | Functional — billing works. Architectural debt only. |
| R-03 | MEDIUM | SSE auth incompatible with EventSource (header-only) | API-003 from certification | Requires design decision. SSE not yet wired in frontend — this is pre-implementation. |
| R-04 | MEDIUM | In-process rate limiting ineffective under horizontal scaling | SEC-004 from certification | Infrastructure concern. No current horizontal deployment confirmed. |
| R-05 | LOW | Git history purge for ffac077 (anon key) | SEC-001 reclassified | Hygiene only. Key is public. No emergency. Schedule during maintenance window. |
| R-06 | LOW | Upload button label says "PDF" (accepts 6 formats) | UI-001 from certification | Label cosmetic issue. No functional impact. |
| R-07 | HIGH | link.viewed event never dispatched from viewer.py | SEC-006/API-001 from certification | Backend change. Not a current UI defect. High business value but no UI depends on it today. Defer to Sprint 4.6 (SSE/Webhooks sprint). |
| R-08 | HIGH | 5 backend-only features invisible to users | F-46–F-50 from certification | Planned for Sprint 4.6 (feature exposure sprint). |

---

## Accepted Risks

| ID | Severity | Title | Acceptance Rationale |
|---|---|---|---|
| R-09 | MEDIUM | JWT in localStorage (SEC-003) | Acceptable given SEC-002 (XSS) is now fixed. Primary attack vector removed. httpOnly cookie migration requires backend changes outside current scope. |
| R-10 | LOW | Feedback viewer submission path unverified | Source reading limitation — the ViewerScreen is 872 lines and feedback submit was not confirmed. Existing feedback items in production confirm the write path functions. |

---

## Risks Introduced This Sprint

None. All three code changes are additive (no existing behavior removed) or defensive (URL guard makes existing behavior safer). The CSV export is read-only from existing state. The New Link fix calls an existing, tested endpoint.
