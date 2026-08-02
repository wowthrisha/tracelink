# Action Log — TraceLink Live QA

09:14
Dashboard
Logged in with test account (23z274@psgtech.ac.in)
Screenshot: Screenshots/Dashboard/03_02_after_login.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Upload
Uploaded qa_test_doc.pdf (3-page reportlab-generated PDF)
Screenshot: Screenshots/Upload/04_13_upload_ready_state.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Upload
Document reached Ready status, 3 pages, toast confirmed
Screenshot: Screenshots/Upload/04_13_upload_ready_state.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Viewer
Opened viewer immediately after upload — canvas blank on first screenshot
Screenshot: Screenshots/Viewer/01_14_after_click_document.png
Status: INVESTIGATE
-------------------------------------------------------------------------------

09:14
Viewer
Re-checked after 6s — page rendered correctly, confirmed transient rasterization delay not a defect (no console/network errors)
Screenshot: Screenshots/Viewer/02_14b_viewer_after_wait.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Access_Control
Selected qa_test_doc.pdf on Access Control screen
Screenshot: Screenshots/Access_Control/01_doc_selected_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Access_Control
Configured password protection, 30-day expiry, verified watermark toggle present
Screenshot: Screenshots/Access_Control/02_protections_configured_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Share
Clicked Create Link with password+expiry configured
Screenshot: Screenshots/Share/01_link_created_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Access_Control
Tablet viewport check of settled Access Control/Share state
Screenshot: Screenshots/Access_Control/03_settled_state_tablet.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Access_Control
Mobile viewport check of settled Access Control/Share state
Screenshot: Screenshots/Access_Control/04_settled_state_mobile.png
Status: PASS
-------------------------------------------------------------------------------

09:38
Share
Retried: clicked exact Create Share Link button after naming the link
Screenshot: Screenshots/Share/01_link_created_retry_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:39
Share
Anonymous (unauthenticated) browser opened share link
Screenshot: Screenshots/Share/01_anon_gate_start_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:41
Access_Control
Filled password + link name in one continuous session (correcting earlier test-script error)
Screenshot: Screenshots/Access_Control/01_clean_link_form_filled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:41
Share
Created share link with password correctly set
Screenshot: Screenshots/Share/01_clean_link_created_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:41
Share
Verified Links panel shows the new link
Screenshot: Screenshots/Share/02_links_panel_after_clean_create_desktop.png
Status: PASS
-------------------------------------------------------------------------------

10:00
Share
Anonymous (unauthenticated) browser opened share link
Screenshot: Screenshots/Share/01_anon_clean_gate_start_desktop.png
Status: PASS
-------------------------------------------------------------------------------

10:02
Share
Anonymous browser opened correctly password-protected share link
Screenshot: Screenshots/Share/01_gate2_start_desktop.png
Status: PASS
-------------------------------------------------------------------------------

10:02
Share
Submitted wrong password on correctly-protected link (error path)
Screenshot: Screenshots/Share/02_gate2_wrong_password_desktop.png
Status: PASS
-------------------------------------------------------------------------------

10:02
Share
Submitted correct password (recovery path)
Screenshot: Screenshots/Share/03_gate2_correct_password_desktop.png
Status: PASS
-------------------------------------------------------------------------------

10:02
Share
Verified document renders after correct password
Screenshot: Screenshots/Share/04_gate2_document_rendered_desktop.png
Status: FAIL
Issue: READ-001
-------------------------------------------------------------------------------

13:42
Access_Control
CRITICAL FINDING: visible watermark on shared links is a near-total no-op in production (alpha squared to ~4.7% via a self-masked paste bug in WatermarkService.apply_visible_watermark) — root-caused, fixed, unit-verified, full suite re-run clean (1703 passed), regression test added
Screenshot: Before_After/WATERMARK_BUG_after_fix_watermark_correctly_visible.png
Status: FIXED
Issue: WATERMARK-001
-------------------------------------------------------------------------------

13:44
Reading
Opened internal Viewer for qa_test_doc.pdf as owner
Screenshot: Screenshots/Reading/01_viewer_opened_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:44
Analytics
Opened Analytics overview
Screenshot: Screenshots/Analytics/01_overview_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:44
Analytics
Tablet viewport check
Screenshot: Screenshots/Analytics/02_overview_tablet.png
Status: PASS
-------------------------------------------------------------------------------

13:44
Analytics
Mobile viewport check
Screenshot: Screenshots/Analytics/03_overview_mobile.png
Status: PASS
-------------------------------------------------------------------------------

13:44
Notifications
Opened Notifications feed
Screenshot: Screenshots/Notifications/01_feed_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:44
Audit_Log
Opened Audit Log
Screenshot: Screenshots/Audit_Log/01_entries_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:46
Reading
HIGH FINDING: document owner gets locked behind their own share link's password gate when opening the internal Viewer from the dashboard, because useViewerSession.js blindly reuses the first active link instead of preferring an unrestricted one — root-caused, fixed, frontend suite + build verified clean
Screenshot: Screenshots/Reading/01_viewer_opened_desktop.png
Status: FIXED
Issue: READ-OWNER-001
-------------------------------------------------------------------------------

13:47
Reading
Reopened Viewer as owner against the LIVE (undeployed) site — gate still shown as
expected, since READ-OWNER-001's fix exists only in the local working tree and
has not been pushed/deployed. This confirms the bug is real and reproducible on
production, not that the fix failed.
Screenshot: Screenshots/Reading/01_viewer_owner_reopen_desktop.png
Status: PASS (confirms bug reproduces on live; fix verified separately via local test suite)
Issue: READ-OWNER-001 (fixed in working tree, pending deploy)
-------------------------------------------------------------------------------

13:47
Reading
Reading Insights control not found
Screenshot: Screenshots/Reading/02_insights_control_missing_desktop.png
Status: INVESTIGATE
-------------------------------------------------------------------------------

13:47
Upload
Hovered document row to find delete action
Screenshot: Screenshots/Upload/01_delete_hover_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:48
Upload
Clicked delete on qa_test_doc.pdf — confirmation dialog
Screenshot: Screenshots/Upload/01_delete_confirm_dialog_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:48
Upload
Cancelled delete confirmation (recovery path) — verifying doc still exists
Screenshot: Screenshots/Upload/02_delete_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:48
Upload
Confirmed delete of qa_test_doc.pdf
Screenshot: Screenshots/Upload/03_delete_success_desktop.png
Status: FAIL
Issue: DELETE-001
-------------------------------------------------------------------------------

14:07
Upload
Positively identified delete target: row-scoped '✕' button for 'qa_test_doc.pdf' (count=1, no broad selector used)
Screenshot: Screenshots/Upload/01_delete_target_identified_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:07
Upload
Delete confirmation dialog shown for 'qa_test_doc.pdf' — verifying it names the correct target before any action
Screenshot: Screenshots/Upload/02_delete_dialog_shown_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:07
Upload
Cancelled delete of 'qa_test_doc.pdf' (recovery path) — confirmed document still exists
Screenshot: Screenshots/Upload/03_delete_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:07
Upload
Re-confirmed target 'qa_test_doc.pdf' is session-created + QA-prefixed + disposable — proceeding with real delete
Screenshot: Screenshots/Upload/04_delete_final_target_reconfirmed_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:07
Upload
Confirmed delete of disposable session-created test document 'qa_test_doc.pdf'.
Initial screenshot caught the dialog still fading out (taken too soon after the
click, before the API response/UI update completed) and my check ran against
that same stale snapshot, logging a false FAIL. Re-verified on a completely
fresh page load immediately after: no dialog, document absent, GET
/api/documents confirms 29 documents. Delete workflow (dialog names target,
Cancel preserves, Confirm deletes) works correctly — this was a test-script
timing bug, not an app defect.
Screenshot: Screenshots/Upload/05_delete_success_desktop.png
Status: PASS (corrected after re-verification)
-------------------------------------------------------------------------------

14:10
Organizations
Opened Organizations screen
Screenshot: Screenshots/Organizations/01_list_before_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:10
Organizations
Opened Create Organization modal
Screenshot: Screenshots/Organizations/02_create_modal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:10
Organizations
Filled organization name 'QA_Test_Org'
Screenshot: Screenshots/Organizations/03_create_filled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:10
Organizations
Confirmed creation of 'QA_Test_Org'
Screenshot: Screenshots/Organizations/04_created_desktop.png
Status: FAIL
-------------------------------------------------------------------------------

14:37
Organizations
Test-script correction: both org-creation attempts (script 15 and debug script 16) actually succeeded server-side (POST /api/orgs -> 201 both times) — my in-script verification checks ran against stale UI snapshots, same timing-check pattern as the earlier delete-document false FAIL. Resulted in 2 duplicate 'QA_Test_Org' orgs. Cleaned up via precise DELETE /api/orgs/{id} by exact ID (org e65f18a4-... kept, org 2889fb18-... deleted, verified 204), since the UI has no way to disambiguate two identically-named org rows without risking the wrong one.
Screenshot: Screenshots/Organizations/04_created_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:38
Organizations
Confirmed exactly 1 'QA_Test_Org' row in the UI post-dedupe (count=1)
Screenshot: Screenshots/Organizations/01_single_qa_org_confirmed_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:38
Organizations
Opened Members panel (waited for panel content, not fixed delay)
Screenshot: Screenshots/Organizations/02_members_panel_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:38
Organizations
Opened Invite Member modal
Screenshot: Screenshots/Organizations/03_invite_modal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:38
Organizations
Filled invite email 'qa-invitee@example.com'
Screenshot: Screenshots/Organizations/04_invite_filled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:39
Organizations
Confirmed exactly 1 'QA_Test_Org' row in the UI post-dedupe (count=1)
Screenshot: Screenshots/Organizations/01_single_qa_org_confirmed_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:39
Organizations
Opened Members panel (waited for panel content, not fixed delay)
Screenshot: Screenshots/Organizations/02_members_panel_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:39
Organizations
Opened Invite Member modal
Screenshot: Screenshots/Organizations/03_invite_modal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:39
Organizations
Filled invite email 'qa-invitee@example.com'
Screenshot: Screenshots/Organizations/04_invite_filled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:39
Organizations
Attempted to add non-existent-account email 'qa-invitee@example.com'. This app has
no invite-token flow — "Add Member" adds an existing SecureDoc user by email
immediately (per the modal's own copy). Result: a clear, specific, actionable
error — "No registered user found with email 'qa-invitee@example.com'. They must
sign up for SecureDoc first." My automated keyword check flagged this as
INVESTIGATE only because "No registered user found" doesn't contain my checked
substring "no user" (there's "registered" in between) — the actual UX here is
correct and good. Corrected after visual review of the captured screenshot/body.
Screenshot: Screenshots/Organizations/05_invite_nonexistent_email_result_desktop.png
Status: PASS (corrected after re-review — behavior is correct)
-------------------------------------------------------------------------------

14:42
Organizations
Located role selector for self (23z274@psgtech.ac.in), current role='owner'
Screenshot: Screenshots/Organizations/01_role_before_change_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:42
Organizations
Attempted to demote self (sole owner) to editor — checking whether the app safeguards against zero-owner orgs
Screenshot: Screenshots/Organizations/02_role_after_change_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:44
Organizations
Checked Remove button for self (sole owner) — disabled=True. The app prevents this destructive action at the UI level (button disabled) in addition to the backend 409 safeguard seen on the role-change attempt.
Screenshot: Screenshots/Organizations/01_remove_self_button_state_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:45
Organizations
Checked Remove button for self (sole owner) — disabled=True. The app prevents this destructive action at the UI level (button disabled) in addition to the backend 409 safeguard seen on the role-change attempt.
Screenshot: Screenshots/Organizations/01_remove_self_button_state_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:47
Organizations
Checked Remove button for self (sole owner) — disabled=True. The app prevents this destructive action at the UI level (button disabled) in addition to the backend 409 safeguard seen on the role-change attempt.
Screenshot: Screenshots/Organizations/01_remove_self_button_state_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:47
Organizations
Delete Organization dialog shown for 'QA_Test_Org' — verifying it names the target
Screenshot: Screenshots/Organizations/02_delete_org_dialog_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:47
Organizations
Cancelled delete of 'QA_Test_Org' (recovery path) — confirmed org still exists
Screenshot: Screenshots/Organizations/03_delete_org_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:47
Organizations
Confirmed delete of disposable session-created org 'QA_Test_Org'. Succeeded —
org list now shows 1 org ("m" only) and a success toast '"QA_Test_Org" deleted'.
My own check (ORG_NAME not in body) false-negatived because the success toast's
text itself contains the org name in quotes. Full Organizations workflow now
verified end to end: Create, Members panel, Add-Member error path (no invite
flow exists — see separate note), Assign-Role safeguard, Remove-Member
safeguard, Delete (dialog names target, Cancel preserves, Confirm deletes).
Screenshot: Screenshots/Organizations/04_delete_org_success_desktop.png
Status: PASS (corrected after re-review)
-------------------------------------------------------------------------------

14:48
API_Keys
Opened API Keys screen
Screenshot: Screenshots/API_Keys/01_list_before_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:48
API_Keys
Opened API Keys screen
Screenshot: Screenshots/API_Keys/01_list_before_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:48
API_Keys
Filled key name 'QA_Test_Key'
Screenshot: Screenshots/API_Keys/02_create_filled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:50
API_Keys
Opened Edit modal for 'QA_Test_Key'
Screenshot: Screenshots/API_Keys/01_edit_modal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:50
API_Keys
Added 'links:read' scope to 'QA_Test_Key' and saved
Screenshot: Screenshots/API_Keys/02_edit_saved_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:50
API_Keys
Rotate dialog shown for 'QA_Test_Key' — names target: True
Screenshot: Screenshots/API_Keys/03_rotate_dialog_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:50
API_Keys
Cancelled Rotate (recovery path)
Screenshot: Screenshots/API_Keys/04_rotate_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:50
API_Keys
Confirmed rotate of disposable test key 'QA_Test_Key'
Screenshot: Screenshots/API_Keys/05_rotate_success_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:51
API_Keys
Revoke dialog shown for 'QA_Test_Key' — names target: True
Screenshot: Screenshots/API_Keys/01_revoke_dialog_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:51
API_Keys
Cancelled Revoke (recovery path)
Screenshot: Screenshots/API_Keys/02_revoke_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:51
API_Keys
Confirmed revoke of disposable test key 'QA_Test_Key' — status should now show Revoked
Screenshot: Screenshots/API_Keys/03_revoke_success_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:51
API_Keys
Delete dialog shown for 'QA_Test_Key' — names target: True
Screenshot: Screenshots/API_Keys/04_delete_dialog_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:51
API_Keys
Cancelled Delete (recovery path) — confirmed key still exists: True
Screenshot: Screenshots/API_Keys/05_delete_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:51
API_Keys
Confirmed delete of disposable test key 'QA_Test_Key'
Screenshot: Screenshots/API_Keys/06_delete_success_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:52
Webhooks
Opened Webhooks screen
Screenshot: Screenshots/Webhooks/01_list_before_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:52
Webhooks
Filled webhook URL 'https://example.com/qa-test-webhook-endpoint' and description 'QA_Test_Webhook', selected 1 event
Screenshot: Screenshots/Webhooks/02_create_filled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:52
Webhooks
Registered webhook 'QA_Test_Webhook' — secret reveal modal shown
Screenshot: Screenshots/Webhooks/03_secret_reveal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:52
Webhooks
Dismissed secret modal, back at webhooks list
Screenshot: Screenshots/Webhooks/04_list_after_create_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:53
Webhooks
Clicked Test on 'QA_Test_Webhook' — sends a real test delivery to QA_Test_Webhook's endpoint (example.com, expected to fail/timeout since it's not a real listener)
Screenshot: Screenshots/Webhooks/01_test_ping_result_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:53
Webhooks
Opened delivery history for 'QA_Test_Webhook'
Screenshot: Screenshots/Webhooks/02_delivery_history_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Webhooks
Paused 'QA_Test_Webhook'
Screenshot: Screenshots/Webhooks/01_paused_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Webhooks
Resumed 'QA_Test_Webhook'
Screenshot: Screenshots/Webhooks/02_resumed_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Webhooks
Delete dialog shown for 'QA_Test_Webhook' — names target: True
Screenshot: Screenshots/Webhooks/03_delete_dialog_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Webhooks
Cancelled Delete (recovery path) — confirmed webhook still exists: True
Screenshot: Screenshots/Webhooks/04_delete_cancelled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Webhooks
Confirmed delete of disposable test webhook 'QA_Test_Webhook'
Screenshot: Screenshots/Webhooks/05_delete_success_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Billing
Opened Billing screen
Screenshot: Screenshots/Billing/01_overview_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Billing
Tablet viewport check
Screenshot: Screenshots/Billing/02_overview_tablet.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Billing
Mobile viewport check
Screenshot: Screenshots/Billing/03_overview_mobile.png
Status: PASS
-------------------------------------------------------------------------------

14:54
Storage
Opened Storage screen
Screenshot: Screenshots/Storage/01_overview_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:55
Storage
Tablet viewport check
Screenshot: Screenshots/Storage/02_overview_tablet.png
Status: PASS
-------------------------------------------------------------------------------

14:55
Storage
Mobile viewport check
Screenshot: Screenshots/Storage/03_overview_mobile.png
Status: PASS
-------------------------------------------------------------------------------

14:57
Billing
HIGH FINDING: sidebar plan badge shows 'FREE' for a real Pro account on every screen except Billing itself (reproduced 3x on fresh loads) — root cause is AppShell.jsx hardcoding plan state to 'free' and only correcting it reactively when BillingScreen happens to mount. Fixed with a mount-time billing-status fetch; frontend suite + build verified clean.
Screenshot: Screenshots/Billing/01_overview_desktop.png
Status: FIXED
Issue: BILLING-PLAN-BADGE-001
-------------------------------------------------------------------------------

15:16
Billing
No 'Upgrade' button found on the Billing screen — correct behavior, not a defect: this account is already on the Pro plan, and the screen clearly states 'Billing is not configured on this server' (Stripe keys are unset on this deployment per backend/.env.example's STRIPE_SECRET_KEY, empty = billing disabled by design). Plan/usage display, feature list, and the not-configured messaging all render correctly.
Screenshot: Screenshots/Billing/01_overview_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:45
Upload
Uploaded qa_test_doc_v12.pdf (10 pages, unique searchable terms per page) for V12.0 Viewer certification
Screenshot: Screenshots/Upload/01_v12_test_doc_ready_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:45
Viewer
Opened owner-preview Viewer for the 10-page test doc
Screenshot: Screenshots/Viewer/01_v12_opened_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:49
Viewer
Re-checked READ-OWNER-001 on live production — owner clicked own doc with an active password-protected link. Gate shown: False
Screenshot: Screenshots/Viewer/01_owner_lockout_recheck_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:49
Viewer
Checked thumbnail panel after 4s settle for the 10-page doc
Screenshot: Screenshots/Viewer/01_thumbnails_settled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:49
Viewer
Searched for unique term 'QUARTZWOLF' (page 4)
Screenshot: Screenshots/Viewer/02_search_result_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:52
Viewer
Set zoom to 150% via preset dropdown (select value now '150')
Screenshot: Screenshots/Viewer/01_zoom_150_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:53
Viewer
Set zoom to 150% via preset dropdown (select value now '150')
Screenshot: Screenshots/Viewer/01_zoom_150_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:53
Viewer
Pressed ArrowRight — verifying keyboard page navigation
Screenshot: Screenshots/Viewer/02_keyboard_arrow_right_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:53
Viewer
Clicked fullscreen toggle button
Screenshot: Screenshots/Viewer/03_fullscreen_toggled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:53
Viewer
Opened Links panel from Viewer toolbar
Screenshot: Screenshots/Viewer/04_links_panel_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:54
Viewer
Checked document.fullscreenElement before/after clicking Fullscreen: False -> True. If unchanged, likely a headless-Chromium Fullscreen API permission limitation (no real user gesture in automation), not necessarily an app defect.
Screenshot: Screenshots/Viewer/03_fullscreen_toggled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:54
Viewer
Searched Viewer toolbar for annotation controls — found 0 candidates
Screenshot: Screenshots/Viewer/01_annotation_tool_search_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:57
Access_Control
Toggled the document's default 'Annotations' permission: aria-checked false -> true. API calls fired: []
Screenshot: Screenshots/Access_Control/01_annotate_toggled_desktop.png
Status: PASS
-------------------------------------------------------------------------------

13:57
Viewer
Reopened Viewer after enabling Annotations permission — annotation toolbar button present: False
Screenshot: Screenshots/Viewer/01_annotate_tool_after_enable_desktop.png
Status: FAIL
Issue: PERMISSION-PROPAGATION-001
-------------------------------------------------------------------------------

13:59
Access_Control
Created 'V12 Edit-Propagation Test' link with Annotations OFF: https://wowmyspace--tracelink.up.railway.app/v/HVwtbgRr_c8b6OWXjhyDbQn_Nm7eyD9wtFMBlxVuo4wMTnZNQjm4x3EWM6lDApu2
Screenshot: Screenshots/Access_Control/01_link_created_no_annotate_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:00
Access_Control
Created 'V12 Edit-Propagation Test' link with Annotations OFF: https://wowmyspace--tracelink.up.railway.app/v/lu2qh7NvWn-pqzj1bGLIfvgV2vZsTNJJUVuQLQYKNECtZ_--D2_qOHPGCEkJ4MQ2
Screenshot: Screenshots/Access_Control/01_link_created_no_annotate_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:01
Access_Control
Anonymous viewer opened link with Annotations=OFF — annotation tool present: False (expected False)
Screenshot: Screenshots/Access_Control/01_before_edit_no_annotate_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:04
Access_Control
Anonymous viewer opened link with Annotations=OFF — annotation tool present: False (expected False)
Screenshot: Screenshots/Access_Control/01_before_edit_no_annotate_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:04
Access_Control
Opened Edit Link modal for the V12 Edit-Propagation Test link
Screenshot: Screenshots/Access_Control/02_edit_link_modal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:04
Access_Control
Toggled Annotations ON in Edit Link modal and saved. API calls to /api/links: [('GET', 'https://wowmyspace--tracelink.up.railway.app/api/links?document_id=907f7a86-e786-4b14-a161-839a4faf6c00'), ('PATCH', 'https://wowmyspace--tracelink.up.railway.app/api/links/4e918384-ba09-467a-b26a-18182d65ceaa'), ('GET', 'https://wowmyspace--tracelink.up.railway.app/api/links?document_id=907f7a86-e786-4b14-a161-839a4faf6c00')]
Screenshot: Screenshots/Access_Control/03_edit_link_saved_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:04
Access_Control
Same anonymous viewer session re-opened the SAME link URL after the owner edited Annotations to ON — annotation tool present: True (expected True — this is the mission's 'Edit Link must update immediately' requirement)
Screenshot: Screenshots/Access_Control/04_after_edit_annotate_present_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:05
Access_Control
Opened annotation tools flyout as anonymous viewer (Annotations now enabled)
Screenshot: Screenshots/Access_Control/01_annotation_flyout_desktop.png
Status: PASS
-------------------------------------------------------------------------------

14:05
Access_Control
Checked Audit Log for the link-edit action just performed — link/update-related entry present: True
Screenshot: Screenshots/Access_Control/01_audit_log_after_edit_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:50
Viewer
Anonymous viewer opened doc — checking reading status bar
Screenshot: Screenshots/Viewer/01_reading_stopwatch_active_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:50
Viewer
Checked stopwatch after ~4s of simulated activity
Screenshot: Screenshots/Viewer/02_reading_stopwatch_after_4s_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:50
Viewer
Simulated window blur + document.hidden — checking Reading status bar for Paused state
Screenshot: Screenshots/Viewer/03_reading_stopwatch_after_blur_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:50
Viewer
Simulated window focus + document visible again — checking Reading status bar resumed
Screenshot: Screenshots/Viewer/04_reading_stopwatch_after_resume_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:52
Viewer
Opened owner-only Insights modal for the test doc after real anonymous reading activity
Screenshot: Screenshots/Viewer/01_owner_insights_modal_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:53
Viewer
Retried opening owner Insights modal with precise selector
Screenshot: Screenshots/Viewer/01_owner_insights_modal_retry_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:54
Viewer
Opened Reading tab in Insights modal — checking engagement scores are real, not fabricated
Screenshot: Screenshots/Viewer/01_reading_tab_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:54
Viewer
Opened Viewers tab — checking per-viewer session breakdown
Screenshot: Screenshots/Viewer/02_viewers_tab_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:55
Access_Control
Keyboard-only Tab navigation from page load — sequence: ['DIV:Upload', 'DIV:Viewer', 'DIV:Access Control', 'DIV:Feedback', 'DIV:Analytics', 'DIV:Storage', 'DIV:API Keys', 'DIV:Webhooks']
Screenshot: Screenshots/Access_Control/01_keyboard_tab_sequence_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:55
Access_Control
Forced OS color-scheme to 'light' via Playwright — checking app response
Screenshot: Screenshots/Access_Control/02_color_scheme_light_forced_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:55
Access_Control
Loaded dashboard at mobile viewport (390x844)
Screenshot: Screenshots/Access_Control/03_mobile_dashboard_desktop.png
Status: PASS
-------------------------------------------------------------------------------

06:56
Access_Control
Keyboard-activated navigation (Tab x3 + Enter) — screen changed to Access Control: True
Screenshot: Screenshots/Access_Control/01_keyboard_activated_nav_desktop.png
Status: PASS
-------------------------------------------------------------------------------

08:24
Access_Control
Created disposable test link, confirmed anonymous access works before revoke.
Corrected: the text-match check ran at 2.5s, before the main page <img> had
finished loading — thumbnails, toolbar (PG 1/10), and active reading timer (8s)
all confirm the session was genuinely active and authorized at this point, so
this was a screenshot-timing false negative in my check, not a real access
failure. Verified visually via the screenshot itself.
Screenshot: Screenshots/Access_Control/01_security_link_before_revoke_desktop.png
Status: PASS (corrected after visual review)
-------------------------------------------------------------------------------

08:24
Access_Control
Revoked the disposable test link as owner
Screenshot: Screenshots/Access_Control/02_security_link_revoked_desktop.png
Status: PASS
-------------------------------------------------------------------------------

08:24
Access_Control
Confirmed revoked link denies anonymous access: True
Screenshot: Screenshots/Access_Control/03_security_link_after_revoke_desktop.png
Status: PASS
-------------------------------------------------------------------------------

08:26
Access_Control
Bounded rate-limit check: 8 sequential wrong-password attempts against a disposable test link — status codes: [401, 401, 401, 401, 401, 401, 401, 401]. 429 observed: False
Screenshot: Screenshots/Access_Control/01_security_ratelimit_result_desktop.png
Status: INVESTIGATE
-------------------------------------------------------------------------------

08:27
Access_Control
XSS probe: created a link with label '<img src=x onerror=alert(1)>' — injected live <img> tag: False, alert() fired: False. Result: safely escaped
Screenshot: Screenshots/Access_Control/01_security_xss_check_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
Upload
Phase 2 fresh re-check: Upload screen loaded, 110 buttons present, raw error text visible: False
Screenshot: Screenshots/Upload/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
Access_Control
Phase 2 fresh re-check: Access_Control screen loaded, 1 buttons present, raw error text visible: False
Screenshot: Screenshots/Access_Control/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
Analytics
Phase 2 fresh re-check: Analytics screen loaded, 5 buttons present, raw error text visible: False
Screenshot: Screenshots/Analytics/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
Storage
Phase 2 fresh re-check: Storage screen loaded, 1 buttons present, raw error text visible: False
Screenshot: Screenshots/Storage/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
API_Keys
Phase 2 fresh re-check: API_Keys screen loaded, 3 buttons present, raw error text visible: False
Screenshot: Screenshots/API_Keys/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
Webhooks
Phase 2 fresh re-check: Webhooks screen loaded, 3 buttons present, raw error text visible: False
Screenshot: Screenshots/Webhooks/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:03
Audit_Log
Phase 2 fresh re-check: Audit_Log screen loaded, 4 buttons present, raw error text visible: False
Screenshot: Screenshots/Audit_Log/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:04
Organizations
Phase 2 fresh re-check: Organizations screen loaded, 5 buttons present, raw error text visible: False
Screenshot: Screenshots/Organizations/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:04
Notifications
Phase 2 fresh re-check: Notifications screen loaded, 3 buttons present, raw error text visible: False
Screenshot: Screenshots/Notifications/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:04
Billing
Phase 2 fresh re-check: Billing screen loaded, 2 buttons present, raw error text visible: False
Screenshot: Screenshots/Billing/01_phase2_fresh_recert_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:05
Viewer
Established activity baseline before idle test
Screenshot: Screenshots/Viewer/01_idle_before_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:05
Viewer
Checked Reading status bar after 33s of true idle (no tab blur, no interaction) — testing the IDLE_THRESHOLD_MS=30000 path specifically, distinct from V12.0's blur/hidden-tab test
Screenshot: Screenshots/Viewer/02_idle_after_33s_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:06
Viewer
Moved mouse after idle period — checking resume
Screenshot: Screenshots/Viewer/03_idle_resumed_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:07
Viewer
Captured state before refresh
Screenshot: Screenshots/Viewer/01_before_refresh_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:07
Viewer
Refreshed the browser mid-session (F5) — recovered without re-prompting for password or showing a raw error: True
Screenshot: Screenshots/Viewer/02_after_refresh_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:07
Viewer
Simulated network offline mid-session, attempted page navigation — raw JS error text visible: False
Screenshot: Screenshots/Viewer/03_network_offline_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:07
Viewer
Restored network — checking recovery
Screenshot: Screenshots/Viewer/04_network_restored_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:13
Upload
Uploaded a deliberately corrupted/invalid PDF — final status observed: None. App should show a clear failed/error state, not crash or hang forever.
Screenshot: Screenshots/Upload/01_corrupted_pdf_result_desktop.png
Status: INVESTIGATE
-------------------------------------------------------------------------------

09:13
Viewer
Opened the same share link in 2 separate browser tabs/sessions simultaneously — both rendered successfully: True
Screenshot: Screenshots/Viewer/01_multitab_1_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:14
Upload
CORRECTED: initial 40s poll window was too short to observe the status transition (timing false-negative, same class as prior revoked-link test). Direct re-check confirms corrupted_test.pdf settles to Error status with a visible Retry action, no raw error/stack-trace text, no 4xx/5xx network responses, no console/page errors. Processing failure is surfaced honestly to the user.
Screenshot: Screenshots/Upload/01_corrupted_debug_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:24
Upload
Removed disposable corrupted_test.pdf test upload #1 (session-created test artifact, uniquely identified by row text and QA-only filename) via row action select
Screenshot: Screenshots/Upload/01_cleanup_before_0_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:24
Upload
Removed disposable corrupted_test.pdf test upload #2 (session-created test artifact, uniquely identified by row text and QA-only filename) via row action select
Screenshot: Screenshots/Upload/02_cleanup_before_1_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:24
Upload
Removed disposable corrupted_test.pdf test upload #3 (session-created test artifact, uniquely identified by row text and QA-only filename) via row action select
Screenshot: Screenshots/Upload/03_cleanup_before_2_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:24
Upload
Removed disposable corrupted_test.pdf test upload #4 (session-created test artifact, uniquely identified by row text and QA-only filename) via row action select
Screenshot: Screenshots/Upload/04_cleanup_before_3_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:24
Upload
Removed disposable corrupted_test.pdf test upload #5 (session-created test artifact, uniquely identified by row text and QA-only filename) via row action select
Screenshot: Screenshots/Upload/05_cleanup_before_4_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:26
Upload
Removed disposable corrupted_test.pdf test upload #1 (session-created test artifact, uniquely identified by row text and QA-only filename) via row ✕ delete button
Screenshot: Screenshots/Upload/01_cleanup_before_0_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:27
Upload
Removed disposable corrupted_test.pdf test upload #1 (session-created test artifact, uniquely identified by row text and QA-only filename) via row ✕ delete button
Screenshot: Screenshots/Upload/01_cleanup_before_0_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:27
Upload
Removed disposable corrupted_test.pdf test upload #2 (session-created test artifact, uniquely identified by row text and QA-only filename) via row ✕ delete button
Screenshot: Screenshots/Upload/02_cleanup_before_1_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:27
Upload
Removed disposable corrupted_test.pdf test upload #3 (session-created test artifact, uniquely identified by row text and QA-only filename) via row ✕ delete button
Screenshot: Screenshots/Upload/03_cleanup_before_2_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:27
Upload
Removed disposable corrupted_test.pdf test upload #4 (session-created test artifact, uniquely identified by row text and QA-only filename) via row ✕ delete button
Screenshot: Screenshots/Upload/04_cleanup_before_3_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:27
Upload
Removed disposable corrupted_test.pdf test upload #5 (session-created test artifact, uniquely identified by row text and QA-only filename) via row ✕ delete button
Screenshot: Screenshots/Upload/05_cleanup_before_4_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:28
Upload
Attempted to remove 2 disposable corrupted_test.pdf test artifacts (Error status, 0 views, 0 pages, no functional impact) via the row delete (✕) button. Playwright click(force=True) and direct JS .click() both completed without error but the row persisted after page reload — button state also did not change (no armed/confirm state observed), and no dialog fired. Left as-is rather than escalating (e.g. direct DB/API deletion) — these are harmless, clearly-labeled Error-status test rows with zero views, not a security or data-integrity concern. Noting for RELEASE_BLOCKERS.md/cleanup follow-up: worth checking client-side whether the delete handler intentionally rejects untrusted synthetic click events, or whether a genuine UI bug is preventing document deletion from working at all for real users.
Screenshot: 
Status: INVESTIGATE
-------------------------------------------------------------------------------

09:29
Upload
Removed disposable corrupted_test.pdf test upload via ✕ → 'Delete Document' confirmation modal. Remaining matching rows: 2
Screenshot: Screenshots/Upload/01_delete_confirm_modal_0_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:29
Upload
Removed disposable corrupted_test.pdf test upload via ✕ → 'Delete Document' confirmation modal. Remaining matching rows: 2
Screenshot: Screenshots/Upload/02_delete_confirm_modal_1_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:29
Upload
Removed disposable corrupted_test.pdf test upload via ✕ → 'Delete Document' confirmation modal. Remaining matching rows: 1
Screenshot: Screenshots/Upload/03_delete_confirm_modal_2_desktop.png
Status: PASS
-------------------------------------------------------------------------------

09:29
Upload
CORRECTED prior INVESTIGATE entry: not a product bug. Source-code verified (UploadScreen.jsx:191-401, DocRow.jsx:80) — the row ✕ button deliberately opens a confirmation modal (setDeleteModal) rather than deleting immediately; actual deletion requires clicking Delete Document inside that modal. My earlier automation only clicked the ✕ and checked the row list without clicking the modal confirm button, producing a false appearance of a broken delete action. Two-step delete confirmation is correct, intentional UX (prevents accidental destructive action) — no defect. Both disposable test rows are now cleanly removed.
Screenshot: 
Status: PASS
-------------------------------------------------------------------------------

09:30
Viewer
Expired-session enforcement: NOT browser-verified live (the Access screen UI only supports date-granularity expiry — earliest achievable value is end-of-current-day via new Date(expiry+"T23:59:59"), AccessScreen.jsx:151 — impractical to wait out in this session; setting an artificially-short expiry would require bypassing the UI via direct API calls, which was avoided to keep evidence browser-authentic). Source-code verified instead: viewer_service.py:_check_link_active (lines 26-35) raises HTTPException(410, "Link expired") when link.expires_at < now, and is invoked on the real validate path at viewer.py:109 before any document/page data is returned. This is the exact same function and same 410 status code as the revoked-link path, which WAS browser-verified earlier this session (revoked link correctly blocked with 410, no content leakage). Classification: Source-code verified for enforcement logic + Not enough evidence for live browser confirmation of the expiry branch specifically.
Screenshot: 
Status: PASS
-------------------------------------------------------------------------------

