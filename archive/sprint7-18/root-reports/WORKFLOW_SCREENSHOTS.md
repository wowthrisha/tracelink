# Workflow Screenshots — Live QA Sprint

86 screenshots captured this sprint, filed under `docs/ui-audit/Screenshots/<Screen>/` (and mirrored to `~/Downloads/TraceLink_Product_Audit/Screenshots/`). Full machine-generated index with every filename, workflow tag, purpose, timestamp, and related issue: `docs/ui-audit/SCREENSHOT_INDEX.md`. This file is the curated, human-readable summary — one row per screen, pointing at the evidence that matters most.

| Screen | Count | Most important shots |
|---|---|---|
| Dashboard | 3 | `03_02_after_login.png` — authenticated session established, real document count visible |
| Upload | 13 | `04_13_upload_ready_state.png` — "Upload complete — 3 pages ready" toast + Processing complete banner; `05_delete_success_desktop.png` — delete workflow success |
| Viewer | 2 | `01_14_after_click_document.png` vs `02_14b_viewer_after_wait.png` — the transient-blank-canvas non-issue, before/after a longer wait |
| Access_Control | 5 | `02_protections_configured_desktop.png` — password + expiry + watermark toggle (confirmed ON) all set correctly |
| Share | 10 | `01_gate2_start_desktop.png` → `02_gate2_wrong_password_desktop.png` → `03_gate2_correct_password_desktop.png` → `04_gate2_document_rendered_desktop.png` — the full anonymous-viewer error/recovery/success sequence where WATERMARK-001 was found |
| Reading | 3 | `01_viewer_opened_desktop.png` — the "Password Required" gate blocking the owner, where READ-OWNER-001 was found |
| Analytics | 3 | `01_overview_desktop.png` + tablet/mobile variants |
| Notifications | 1 | `01_feed_desktop.png` |
| Audit_Log | 1 | `01_entries_desktop.png` |
| Organizations | 15 | `04_created_desktop.png` (duplicate-org discovery), Members panel role-select and disabled-Remove-button screenshots, `04_delete_org_success_desktop.png` |
| API_Keys | 13 | Full create → edit → rotate (dialog/cancel/confirm) → revoke (dialog/cancel/confirm) → delete (dialog/cancel/confirm) sequence |
| Webhooks | 11 | Register → secret reveal → test ping → delivery history (PENDING state) → pause/resume → delete sequence |
| Billing | 3 | `01_overview_desktop.png` — shows the sidebar/Billing-screen plan-badge discrepancy that became BILLING-PLAN-BADGE-001 |
| Storage | 3 | `01_overview_desktop.png` + tablet/mobile variants |

## Before/After evidence (bug fixes)

`docs/ui-audit/Before_After/` (also mirrored to Downloads), indexed in `docs/ui-audit/BEFORE_AFTER_INDEX.md`:

- **WATERMARK-001**: `WATERMARK_BUG_before_8x_contrast_no_watermark_visible.png` (live production page, 8x contrast-enhanced, zero watermark signal) vs. `WATERMARK_BUG_after_fix_watermark_correctly_visible.png` (same code path post-fix, correct diagonal tiled watermark at 22% opacity).
- **READ-OWNER-001**: documented via `Screenshots/Reading/01_viewer_opened_desktop.png` (the bug) — no separate after-shot since the fix isn't deployed to compare live; local frontend test suite is the verification.
- **BILLING-PLAN-BADGE-001**: documented via `Screenshots/Billing/01_overview_desktop.png` vs `Screenshots/Storage/01_overview_desktop.png` (same account, same moment, different sidebar badge) — no separate after-shot for the same deployment reason.

## Viewport coverage

Full desktop coverage across every screen touched. Tablet (820×1180) and mobile (390×844) coverage captured for the highest-traffic settled states (Access_Control/Share, Analytics, Billing, Storage) rather than every single intermediate step — see `WORKFLOW_PROGRESS.md` and the conversation record for the explicit scoping rationale. Note: `AppShell.jsx` has an intentional "desktop-only beta" gate below 768px width, so true mobile-responsive layout is out of scope by design, not a defect (`docs/engineering/ARCHITECTURE_DECISIONS.md`, AD-6).
