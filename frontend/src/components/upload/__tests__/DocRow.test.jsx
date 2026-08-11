import { render } from '@testing-library/react';
import { DocRow } from '../DocRow.jsx';
import { C } from '../../../constants/tokens.js';

// BUG-004 regression: the Documents-list "Expires" column read `doc.expires`
// (a field that never existed on the API response — the real field is
// `expires_at`) and compared against a hardcoded absolute date
// ('2026-05-16') instead of a rolling window, so the column silently showed
// "—" for every document forever, and the "expiring soon" warning color was
// permanently dead code. These tests exercise the corrected `expires_at`/
// `lifecycle_state`-driven rendering directly.

const makeDoc = (overrides = {}) => ({
  id: 'doc-123',
  filename: 'Contract.pdf',
  status: 'ready',
  page_count: 5,
  file_size_bytes: 1024 * 1024,
  total_views: 3,
  lifecycle_state: 'active',
  expires_at: null,
  ...overrides,
});

const defaultProps = (overrides = {}) => ({
  doc: makeDoc(),
  isLast: false,
  onView: vi.fn(),
  onAccess: vi.fn(),
  onDelete: vi.fn(),
  onReprocess: vi.fn(),
  onQuickShare: vi.fn(),
  groups: [],
  onAssignGroup: vi.fn(),
  ...overrides,
});

function renderRow(props) {
  return render(
    <table><tbody><DocRow {...defaultProps(props)} /></tbody></table>
  );
}

// jsdom normalizes inline hex colors to rgb() on read-back.
function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}

// The Expires cell is always the 6th <td> (Document, Status, Risk, Pages, Views, Expires, Actions).
function expiresCell(container) {
  return container.querySelectorAll('td')[5];
}

describe('DocRow — Expires column (BUG-004)', () => {
  test('renders "—" when the document has no expiry (retention_policy=never)', () => {
    const { container } = renderRow({ doc: makeDoc({ expires_at: null, lifecycle_state: 'active' }) });
    expect(expiresCell(container).textContent).toBe('—');
  });

  test('renders a formatted date for a future expires_at, not raw ISO text', () => {
    const future = new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toISOString();
    const { container } = renderRow({ doc: makeDoc({ expires_at: future, lifecycle_state: 'active' }) });
    const expectedText = new Date(future).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    expect(expiresCell(container).textContent).toBe(expectedText);
    expect(expiresCell(container).textContent).not.toBe(future);
  });

  test('shows "Expired" (not a stale date string) once lifecycle_state is expired', () => {
    const past = new Date(Date.now() - 27 * 24 * 60 * 60 * 1000).toISOString();
    const { container } = renderRow({ doc: makeDoc({ expires_at: past, lifecycle_state: 'expired' }) });
    expect(expiresCell(container).textContent).toBe('Expired');
  });

  test('shows "Expired" even if lifecycle_state is still active but expires_at has passed (pre-cleanup-job window)', () => {
    const past = new Date(Date.now() - 1000).toISOString();
    const { container } = renderRow({ doc: makeDoc({ expires_at: past, lifecycle_state: 'active' }) });
    expect(expiresCell(container).textContent).toBe('Expired');
  });

  test('expired documents render the date cell in the error color', () => {
    const { container } = renderRow({ doc: makeDoc({ lifecycle_state: 'expired' }) });
    expect(expiresCell(container).style.color).toBe(hexToRgb(C.error));
  });

  test('a document expiring within 7 days renders in the warning color', () => {
    const soon = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString();
    const { container } = renderRow({ doc: makeDoc({ expires_at: soon, lifecycle_state: 'active' }) });
    expect(expiresCell(container).style.color).toBe(hexToRgb(C.warning));
  });

  test('a document expiring well in the future does not use the warning color', () => {
    const farFuture = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
    const { container } = renderRow({ doc: makeDoc({ expires_at: farFuture, lifecycle_state: 'active' }) });
    const color = expiresCell(container).style.color;
    expect(color).not.toBe(hexToRgb(C.warning));
    expect(color).not.toBe(hexToRgb(C.error));
  });
});
