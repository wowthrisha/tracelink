# UI Changelog — V10.0

User-facing text/behavior changes only (subset of `FIX_LOG.md`, filtered to what an end user would actually notice). Append-only.

(Populated as fixes land below.)

## 2026-07-23

- **Fixed**: wrong-password shake feedback on the public share-link gate now actually animates (was silently broken — the keyframe it referenced didn't exist).
- **Fixed**: 9 modals across API Keys, Webhooks, and Organizations screens (Create/Rename/Invite/Members/New Key/Secret Reveal/Delivery History) now open with a consistent fade-in animation, trap keyboard focus while open, and close on Escape or a backdrop click — previously these 9 were the only modals in the app that did none of the three.
- **Fixed**: the two document-permission toggle switches on the Access Control screen now announce what they control to screen readers (previously announced nothing).

## 2026-07-24

- **Fixed**: a third, previously-missed unlabeled permission toggle in the Access Control screen's "Edit Link" modal now announces what it controls (found while auditing the same screen for jargon — the earlier find-and-replace fix didn't match this call site's formatting).
- **Improved**: Access Control's permission toggles (Watermark, IP Allowlist, Info Panel, and others) now show a plain-language explanation on hover instead of just a technical label.
- **Improved**: the "Blocked Attempts" stat now explains what it counts on both the Upload and Analytics screens (previously only on Analytics, and its own explanation referred to "DRM events" without defining that term either).
- **Improved**: API Keys' "Scopes" section (create and edit) now leads with a one-line explanation of what choosing a scope does.
- **Improved**: Webhooks' info card now opens with a plain-language definition before the technical payload/signing details.
- **Improved**: Organizations screen now notes that organizations are optional for users working alone.
- **Improved**: Audit Log's subtitle now leads with why a user would use the page, before listing what it tracks.
- **Improved**: Billing's plan comparison now explains what "Watermarking" does on hover.

## 2026-07-26 (V12.0)

No user-visible frontend changes this sprint — the one bug found and fixed (`AUDIT-LINK-COMMIT-001`) is backend-only (an internal audit-trail persistence bug with no UI symptom; the UI already correctly showed the permission change taking effect, only the *record* of the change was missing). Recorded here for completeness rather than silently omitting a sprint from this log.
