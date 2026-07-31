# Frontend Maturity — Sprint V7.0 (Phase 5)

Covers spacing, iconography, animation, keyboard behavior, and responsive behavior — the five dimensions not already covered by V6.0's `CONSISTENCY_MATRIX.md` (which covers confirmation-dialog copy, empty states, date/time formatting, toast tone, loading-indicator text, button-variant usage, ARIA labels, and terminology). Read both documents together for the full frontend-maturity picture.

## Spacing — no scale exists

`tokens.js` has a complete color-token system but **zero spacing constants**. Every `padding`/`gap`/`margin` value across all 12 screens is a raw hardcoded number. One pattern has converged organically (the info/warning banner card, consistently `padding: '12px 16px'` across 7+ instances), but elsewhere there's real, un-intentional-looking drift: visually-identical container types (modal-form cards, stat/metric cards, list-row cards) use `'22px 24px'` vs. `'14px 16px'` vs. `'14px 18px'` with no rule distinguishing them. Across all 12 screens: 44 distinct padding value-pairs and 13 distinct gap values, with the two most common gap values (`8` and `14`) both extremely common for what appear to be interchangeable flex-row contexts. Even the shared `Card` component's own default padding (`'16px 18px'`) is overridden by most call sites rather than relied on.

## Iconography — two systems, mostly-but-not-fully separated

Authenticated app chrome (sidebar, headers, tabs) consistently uses geometric Unicode glyphs (⊕ ◫ ◈ ✦ ▦ ◻ ⌗ ⇌ ≡ ◉ ◎ ◇) — internally consistent within that context. The public share-link gate (`AccessGate.jsx`) and several viewer components (`AnnotationLayer.jsx`'s bookmark/comment/sticky-note markers, `InsightsModal.jsx`'s 🔥 indicator) instead use real pictographic emoji. The two systems don't clash *within* their own contexts, but a viewer's actual session mixes both — the toolbar chrome (geometric), the annotation markers they place (emoji), and the insights panel (emoji) all differ within the same continuous screen. The same concept also gets different treatment in different places: "warning" is consistently the geometric ⚠ character everywhere it's used for confirmation dialogs, but "security/lock," a closely related concept, is a literal padlock emoji on the access gate while the sidebar's equivalent "Security"/"Access Control" nav items use the abstract ◈ diamond.

## Animation — centralized keyframes, inconsistent application, two broken instances

8 keyframes are centralized in one place (`SecureDoc.html`: `fadeUp`, `fadeIn`, `slideIn`, `pulse`, `toastIn`, `toastOut`, `progressAnim`, `spin`) with reusable utility classes — a genuinely good foundation. But durations drift for the same semantic "content appears" animation: the shared `Modal`'s overlay fades at `.15s` while its own dialog box fades at `.22s`, and `LoginScreen.jsx` uses a third value, `.25s`, with no rule for which gets which speed. Loading-spinner speed is consistent at `.65s` in most places but `QuickShareModal.jsx` uses `.7s`.

**Two confirmed broken defects** (documented here, not fixed, per this sprint's "no more bug fixes" scope):
- `AccessGate.jsx`'s wrong-password shake feedback references `animation: 'shake .4s'`, but `@keyframes shake` is never defined anywhere in the stylesheet — the shake silently does nothing. External viewers entering a wrong password get no visual feedback that anything happened beyond the inline error text.
- `ViewerScreen.jsx` injects its own one-off `@keyframes sdoc-shimmer` at runtime via direct DOM style manipulation, rather than adding it to the shared stylesheet alongside the other 8 — an inconsistent *implementation* pattern even though the shimmer effect itself is legitimate.

Separately, 7 hand-rolled modal overlays (`ApiKeysScreen.jsx`, `WebhooksScreen.jsx`, `OrgsScreen.jsx` — already flagged in V6.0's consistency matrix for lacking focus-trap/Escape-to-close) also have **zero entrance animation** at all — they snap into existence, unlike every modal built on the shared `Modal` component, which fades in automatically. This is the same underlying root cause (bypassing the shared component) manifesting as a second, distinct symptom.

## Keyboard behavior

`SearchPanel.jsx` (Enter/Shift+Enter/Escape) is the good reference pattern, and 11 other `onKeyDown` sites broadly follow reasonable conventions for their context. Two real gaps:
- **The Viewer's page-navigation arrow keys don't exist.** `ViewerToolbar.jsx` labels the prev/next buttons with tooltips reading "Previous (←)" / "Next (→)," but no keydown listener for `ArrowLeft`/`ArrowRight` exists anywhere in the viewer code — the advertised shortcut is fully non-functional. This is a documentation-vs-implementation mismatch inside the product UI itself, not just written docs.
- The 7 hand-rolled overlay modals (see Animation above) also lack Escape-to-close, unlike the shared `Modal`'s built-in handler — the same root cause, a third symptom.

## Responsive behavior — effectively desktop-only, with dead CSS

Exactly one CSS media query exists in the entire app (`max-width: 640px`, controlling toolbar-label hiding and minor padding). But `AppShell.jsx` independently gates the *entire application* at a harder 768px cutoff — anything under 768px viewport width is replaced with a "desktop only" message before the CSS's 640px rules could ever apply to anything. **The one responsive CSS block in the app is dead code**, made unreachable by a JS gate that's stricter than it. A third, unrelated one-off `640` check in `ViewerScreen.jsx` (setting initial sidebar visibility) is similarly moot and isn't kept in sync via a resize listener. No other screen, card, table, or fixed-width modal (many are hardcoded to specific pixel widths: 420/460/480/520/600) has any responsive handling — currently harmless only because the 768px gate blocks anything that would expose it.

---

## Top 6 most user-visible findings (ranked)

1. Viewer page-navigation arrow keys are advertised (tooltip text) but don't work at all.
2. `AccessGate`'s wrong-password shake animation references a keyframe that doesn't exist — silently broken feedback for every external viewer who mistypes a password.
3. 7 modals across 3 screens bypass the shared `Modal` component, losing entrance animation, focus-trap, and Escape-to-close simultaneously — the single highest-leverage frontend-maturity fix available, since it's one root cause (adopt the shared component) fixing three separate symptoms at once.
4. The app's only responsive CSS is unreachable dead code; the product is effectively desktop-only despite the CSS suggesting otherwise.
5. No spacing scale exists at all, despite a mature color-token system existing right next to where one should be.
6. Icon language (geometric vs. emoji) shifts within a single continuous viewer session depending on which UI element you're looking at.

None of these were fixed this sprint — the two genuine defects (broken shake animation, non-functional arrow keys) are real bugs, and per this sprint's explicit scope ("the objective is no longer fixing bugs... focus only on engineering maturity"), they're documented here and in `TECH_DEBT_REGISTER.md` rather than patched.
