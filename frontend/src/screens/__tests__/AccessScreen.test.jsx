import { render, screen } from '@testing-library/react';
import { AccessScreen } from '../AccessScreen.jsx';
import { ToastProvider } from '../../contexts/toast.jsx';
import { C } from '../../constants/tokens.js';

// BUG-006 regression: the Feedback tab's Export <select> trigger is themed
// (teal background, white text), but its <option> list had no styling at
// all, so clicking it opened the browser's default light-system listbox —
// a jarring light-blue-on-white popup inside an otherwise all-dark UI.
// There's no shared custom-dropdown component in this codebase to swap in
// (atoms.jsx has none), so the fix styles the <option> elements directly
// with the same dark surface tokens used everywhere else, which Chromium/
// Firefox do respect for the popup's own rendering.

// jsdom normalizes inline hex colors to rgb() on read-back.
function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}

function renderScreen(overrides = {}) {
  return render(
    <ToastProvider>
      <AccessScreen doc={{ id: 'doc-1', filename: 'Contract.pdf' }} defaultTab="feedback" {...overrides} />
    </ToastProvider>
  );
}

describe('AccessScreen — Feedback Export dropdown dark theme (BUG-006)', () => {
  beforeEach(() => {
    window.SecureDocAPI.getLinks = vi.fn().mockResolvedValue({ links: [] });
    window.SecureDocAPI.getFeedback = vi.fn().mockResolvedValue({ feedback: [] });
    window.SecureDocAPI.getFeedbackReviewers = vi.fn().mockResolvedValue([]);
  });

  test('every option in the Export dropdown carries an explicit dark background and readable text color', async () => {
    renderScreen();
    const placeholder = await screen.findByText('↓ Export…');
    const options = placeholder.closest('select').querySelectorAll('option');
    expect(options.length).toBe(3);
    options.forEach(opt => {
      expect(opt.style.background).toBe(hexToRgb(C.surface2));
      expect(opt.style.background).not.toBe('');
      expect(opt.style.color).not.toBe('');
    });
  });

  test('Export dropdown options are not left unstyled (would fall back to the light system listbox)', async () => {
    renderScreen();
    const conversations = await screen.findByText('Export Feedback Conversations');
    const reviewerActivity = screen.getByText('Export Reviewer Activity');
    expect(conversations.style.background).toBe(hexToRgb(C.surface2));
    expect(reviewerActivity.style.background).toBe(hexToRgb(C.surface2));
  });

  test('the closed select trigger itself remains themed (teal, unaffected by this fix)', async () => {
    renderScreen();
    const placeholder = await screen.findByText('↓ Export…');
    const select = placeholder.closest('select');
    expect(select.style.background).toBe(hexToRgb(C.teal1));
  });
});
