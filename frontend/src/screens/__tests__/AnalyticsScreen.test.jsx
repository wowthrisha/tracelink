import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnalyticsScreen } from '../AnalyticsScreen.jsx';
import { ToastProvider } from '../../contexts/toast.jsx';

// BUG-003 regression: Overview's "Blocked Attempts" card is scoped to today
// (backend field `blocked_attempts_today`), while the By Document and By
// Group tabs show all-time totals (backend field `blocked_attempts`, no date
// filter) — this is intentional (different, legitimately useful metrics),
// not an aggregation bug, but nothing in the UI said so, so the numbers
// looked like an unexplained contradiction (Overview=0, By Document=24,
// By Group=25 for the same account). The fix labels the Overview card
// "Blocked Attempts (Today)" (matching the existing "Views Today" card's
// naming convention for its own _today-suffixed field) and adds a
// clarifying tooltip to the all-time "Blocked" columns on the other tabs.

const overview = {
  total_documents: 5,
  total_groups: 2,
  total_views_today: 10,
  active_links: 3,
  expiring_soon_count: 0,
  blocked_attempts_today: 0,
  views_last_7_days: [],
};

const documents = [
  { id: 'doc-1', filename: 'Project-Procurement-Management.pdf', total_views: 40, unique_sessions: 12, completion_rate_pct: 80, blocked_attempts: 23, risk_score: 'MEDIUM' },
  { id: 'doc-2', filename: 'CO_PMBOK8.pdf', total_views: 5, unique_sessions: 2, completion_rate_pct: 60, blocked_attempts: 1, risk_score: 'LOW' },
];

const groups = [
  { group_id: 'g1', group_name: 'pmp', group_color: '#6366f1', document_count: 2, total_views: 45, unique_sessions: 14, active_links: 2, blocked_attempts: 25, risk_score: 'MEDIUM' },
];

function renderScreen() {
  return render(
    <ToastProvider>
      <AnalyticsScreen />
    </ToastProvider>
  );
}

describe('AnalyticsScreen — Blocked Attempts labeling (BUG-003)', () => {
  beforeEach(() => {
    window.SecureDocAPI.getAnalyticsOverview = vi.fn().mockResolvedValue(overview);
    window.SecureDocAPI.getDocumentAnalytics = vi.fn().mockResolvedValue({ documents });
    window.SecureDocAPI.getGroupAnalytics = vi.fn().mockResolvedValue({ groups });
  });

  test('Overview KPI card is explicitly labeled "(Today)", matching the Views Today convention', async () => {
    renderScreen();
    await waitFor(() => expect(screen.getByText('Blocked Attempts (Today)')).toBeInTheDocument());
    expect(screen.queryByText('Blocked Attempts')).not.toBeInTheDocument();
    // Baseline: the sibling _today metric already uses this pattern.
    expect(screen.getByText('Views Today')).toBeInTheDocument();
  });

  test('Overview shows 0 for today while all-time totals differ, and this is not treated as a data error', async () => {
    renderScreen();
    const labelEl = await screen.findByText('Blocked Attempts (Today)');
    const card = labelEl.closest('[title]');
    expect(card).not.toBeNull();
    expect(card.textContent).toContain('0');
  });

  test('By Document tab "Blocked" column header carries a tooltip disambiguating it from the Overview card', async () => {
    renderScreen();
    await waitFor(() => expect(window.SecureDocAPI.getDocumentAnalytics).toHaveBeenCalled());
    fireEvent.click(screen.getByText('By Document'));
    const header = await screen.findByText('Blocked', { selector: 'th' });
    expect(header.title).toMatch(/all-time/i);
    expect(header.title).toMatch(/Blocked Attempts \(Today\)/);
  });

  test('By Document tab sums (23 + 1 = 24) render as all-time totals per document', async () => {
    renderScreen();
    fireEvent.click(screen.getByText('By Document'));
    expect(await screen.findByText('23')).toBeInTheDocument();
    expect(await screen.findByText('1', { selector: 'td' })).toBeInTheDocument();
  });

  test('By Group tab "Blocked" table column header carries the same disambiguating tooltip', async () => {
    renderScreen();
    fireEvent.click(screen.getByText('By Group'));
    const header = await screen.findByText('Blocked', { selector: 'th' });
    expect(header.title).toMatch(/all-time/i);
  });

  test('By Group tab card-grid "Blocked" stat also carries the disambiguating tooltip', async () => {
    renderScreen();
    fireEvent.click(screen.getByText('By Group'));
    await waitFor(() => expect(window.SecureDocAPI.getGroupAnalytics).toHaveBeenCalled());
    const label = await screen.findByText('Blocked', { selector: 'div' });
    const statBlock = label.closest('[title]');
    expect(statBlock).not.toBeNull();
    expect(statBlock.title).toMatch(/all-time/i);
  });

  test('By Group tab shows the all-time total of 25, distinct from Overview\'s today-scoped 0', async () => {
    renderScreen();
    fireEvent.click(screen.getByText('By Group'));
    const matches = await screen.findAllByText('25');
    expect(matches.length).toBeGreaterThan(0);
  });
});
