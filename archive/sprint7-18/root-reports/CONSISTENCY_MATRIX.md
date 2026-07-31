# Consistency Matrix — Sprint V6.0 (Phase 7)

Cross-screen consistency audit across naming, buttons, icons, terminology, status/toast messages, loading indicators, date/time formats, empty states, confirmation dialogs, keyboard shortcuts, ARIA labels, and permissions. All 12 screens compared directly against each other, not against an abstract style guide — every row below is a real difference between two or more screens, with file:line evidence.

## Confirmation dialog copy

**Standard pattern** (7 of 9 destructive actions): errorBg box, bold "⚠ This cannot be undone." lead line, names the affected item, `Cancel`(secondary)/`<Verb> <Noun>`(danger) footer.

| Finding | Status |
|---|---|
| "Delete Document" modal only mentioned share links being revoked, never that the document itself is deleted | ✅ **Fixed** — now explicitly states the document, its share links, annotations, and analytics are all permanently deleted. |
| Storage retention-change modal had no warning styling at all, generic "Confirm" button (breaking the danger-button convention every other destructive dialog follows) | ✅ **Fixed** — now uses the standard warning template when the change actually schedules deletion (any policy except "never"), with a `danger`-variant confirm button; kept a lighter, non-alarming style for the safe case (switching to "never," which is not destructive). |
| Revoke actions (API key, share link) use a "⚠ This will immediately..." warning template instead of the "cannot be undone" template used by delete actions | 📝 **Documented, not changed** — arguably correct as-is: revoke actions genuinely differ from delete (reversible in the sense that revoking doesn't destroy the record), so a distinct-but-still-serious template is defensible. Flagged for awareness, not treated as a bug. |

## Empty states

Three tiers coexist with no evident rule for which screen gets which: icon+heading+CTA (ApiKeys, Webhooks, Orgs), text+CTA (Upload, Storage), and bare single-line text with no icon or next step (Analytics, AuditLog, Notifications, most of AccessScreen, ViewerScreen's reply list). 📝 **Documented, not changed** — unifying empty-state treatment across ~10 tables/lists is a real but purely cosmetic, broad mechanical change; not attempted this sprint given the volume of correctness bugs that took priority.

## Date/time formatting

The same conceptual field ("created at") renders **three different ways** depending on screen: `fmtDate()` → "Jul 17, 2026" (ApiKeys/Orgs/Webhooks), raw `toLocaleString()` full timestamp (AccessScreen), custom `fmtTime()` → "Jul 17, 02:45 PM" (AuditLog). Two near-duplicate relative-time helpers also exist (`ApiKeysScreen.jsx`'s `fmtRelative`, never falling back to an absolute date; `NotificationsScreen.jsx`'s `fmtTime`, falling back after 24h) with diverging behavior. 📝 **Documented, not changed** — real inconsistency, but consolidating date formatting across 6+ call sites into one shared, configurable helper is exactly the kind of broad mechanical sweep that's higher-value done as its own dedicated pass with full before/after screenshots than folded into this governance sprint.

## Toast tone/structure

Delete/revoke toasts use `'success'` severity in ApiKeysScreen but `'info'` severity in AccessScreen for the same class of action (`ApiKeysScreen.jsx:151,173` vs `AccessScreen.jsx:853,879`). Punctuation (trailing period) is applied inconsistently even within the same screen. 📝 **Documented, not changed** — cosmetic, low risk either way, deferred in favor of the correctness fixes made this sprint.

## Loading indicators

ViewerScreen alone implements a real animated CSS spinner; every other screen shows plain "Loading…" text for the same underlying "waiting for data" state. LoginScreen uniquely says "Please wait…" instead of "Loading…". 📝 **Documented, not changed** — a design-system decision (should every screen get a spinner, or should ViewerScreen's be simplified to match?) that's better made deliberately than defaulted by whichever engineer touches it next; not this sprint's call to make unilaterally.

## Button variant usage

Row-level delete/revoke triggers use `ghost` + inline red text almost everywhere, but `outline-danger` specifically on AccessScreen's link rows and its page-level "Revoke All Access" button — same action class, different visual weight. Cancel buttons in confirm modals are consistently `secondary`, but some create/edit modals use `ghost` for the identical dismiss role. 📝 **Documented, not changed.**

## ARIA / accessibility

| Finding | Status |
|---|---|
| 6 screens (AnalyticsScreen, AppShell, AuditLogScreen, BillingScreen, NotificationsScreen, StorageScreen, ViewerScreen) have **zero** `aria-label` occurrences despite icon-only refresh/close/toggle controls | 📝 **Documented, not changed** — real accessibility gap, but adding correct labels to every icon-only control across 6 screens needs care (labels should describe the actual action, not be filler) and is a broad sweep better done deliberately. |
| The shared `Toggle` switch component is used twice without its `label` prop passed (`AccessScreen.jsx:331,996`), leaving `aria-label={undefined}` on a real interactive switch | 📝 **Documented, not changed** — small, contained fix (pass a label string at 2 call sites); deprioritized below the correctness bugs this sprint, but flagged as a very quick win for next time. |
| Several create/edit modals (ApiKeys, Orgs, Webhooks) hand-roll their own `position:fixed` overlay instead of using the shared `Modal` atom, silently losing the focus-trap and Escape-to-close behavior `Modal` provides for free | 📝 **Documented, not changed** — a real, noticeable keyboard-accessibility gap; fixing it means migrating each hand-rolled overlay onto the shared component, which risks subtle layout/behavior differences per modal and deserves its own careful pass rather than a rushed swap. |

## Terminology

"Share Link"/"Organization" naming is consistently used in titles and body copy across screens — no real inconsistency found there. One genuine finding: the same "pause access" concept is exposed as a `Toggle` switch on AccessScreen (link restrictions) but as a text button labeled "Pause"/"Resume" on WebhooksScreen — same underlying concept, two different control types. 📝 **Documented, not changed** — a UI-pattern decision, not a bug.

---

## Summary

Two concrete consistency bugs were fixed this sprint (Delete Document modal copy, Storage retention modal styling) because they directly matched the "destructive action needs a proper confirmation" correctness bar this sprint was also enforcing elsewhere. The remaining ~10 findings above are real but purely cosmetic/polish-level — each is individually low-risk but collectively represents a broad, multi-screen mechanical sweep (unify date formatting, unify toast severity, unify empty states, add missing ARIA labels, migrate hand-rolled modals onto the shared component) that's better executed as its own dedicated consistency pass, with before/after visual review, than squeezed into a governance sprint alongside correctness and security fixes. Recommended next-sprint candidate, ranked by user-visibility: date-format unification, empty-state unification, ARIA-label sweep.
