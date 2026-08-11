import { render, screen, fireEvent } from '@testing-library/react';
import { InsightsModal } from '../InsightsModal.jsx';

// BUG-002 regression: /reading/document/{id}/viewers and /insights both wrap
// their list in a metadata envelope ({document_id, filename, ..., viewers: [...]}
// / {..., insights: [...]}), the same shape family as /heatmap (whose `.pages`
// ReadingTab already unwraps). ViewerScreen.jsx used to hand the whole envelope
// straight through as `readingData.viewers` / `readingData.insights`, so
// ViewersTab/InsightsTab's `.map()` call crashed with "t.map is not a function"
// the moment a real backend response reached them ({}.length is undefined, so
// the old `!viewers || viewers.length === 0` guard let a bare object through).
// These tests exercise InsightsModal directly with both the corrected bare-array
// shape and the old raw-envelope shape, to prove the tabs render/degrade
// gracefully either way and never crash the surrounding Viewer.

const baseProps = (overrides = {}) => ({
  docName: 'Contract.pdf',
  loading: false,
  data: { pages: [], total_views: 0 },
  readingData: { summary: { total_sessions: 2 }, heatmap: null, insights: null, viewers: null },
  readingLoading: false,
  onClose: vi.fn(),
  C: {},
  mono: {},
  ...overrides,
});

function openTab(label) {
  fireEvent.click(screen.getByText(label));
}

describe('InsightsModal — Viewers tab', () => {
  test('renders multiple viewer sessions from a bare array (correct contract)', () => {
    const viewers = [
      { session_id: 'a1b2c3d4', viewer_email: 'alice@example.com', total_active_ms: 65000, completion_pct: 80, pages_visited: 5 },
      { session_id: 'e5f6a7b8', viewer_email: 'bob@example.com', total_active_ms: 12000, completion_pct: 20, pages_visited: 2 },
    ];
    render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 2 }, insights: null, viewers } })} />);
    openTab('Viewers');
    expect(screen.getByText('2 Sessions')).toBeInTheDocument();
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    expect(screen.getByText('bob@example.com')).toBeInTheDocument();
  });

  test('renders a single viewer session with correct singular label', () => {
    const viewers = [{ session_id: 'a1b2c3d4', viewer_email: 'solo@example.com', total_active_ms: 5000, completion_pct: 10, pages_visited: 1 }];
    render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 1 }, insights: null, viewers } })} />);
    openTab('Viewers');
    expect(screen.getByText('1 Session')).toBeInTheDocument();
  });

  test('shows empty state for an empty viewers array, does not crash', () => {
    render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 0 }, insights: null, viewers: [] } })} />);
    openTab('Viewers');
    expect(screen.getByText('No viewer sessions yet.')).toBeInTheDocument();
  });

  test('shows empty state instead of crashing when viewers is null', () => {
    render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 0 }, insights: null, viewers: null } })} />);
    openTab('Viewers');
    expect(screen.getByText('No viewer sessions yet.')).toBeInTheDocument();
  });

  test('BUG-002 regression: raw envelope object (legacy/malformed shape) degrades to empty state instead of throwing', () => {
    // This is the exact shape the backend returns and the pre-fix bug handed
    // straight to ViewersTab: an object, not an array. `t.map is not a
    // function` would previously throw here and take down the whole Viewer.
    const rawEnvelope = { document_id: 'doc-1', filename: 'x.pdf', total_viewers: 2, viewers: [{ session_id: 'a' }, { session_id: 'b' }], complexity: {} };
    expect(() => {
      render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 2 }, insights: null, viewers: rawEnvelope } })} />);
      openTab('Viewers');
    }).not.toThrow();
    expect(screen.getByText('No viewer sessions yet.')).toBeInTheDocument();
  });
});

describe('InsightsModal — Insights tab', () => {
  test('renders multiple insights from a bare array (correct contract)', () => {
    const insights = [
      { type: 'warning', message: 'Page 4 has a high drop-off rate', confidence: 0.82 },
      { type: 'positive', message: 'Readers finish faster than average', confidence: 0.6 },
    ];
    render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 2 }, insights, viewers: null } })} />);
    openTab('Insights');
    expect(screen.getByText('Page 4 has a high drop-off rate')).toBeInTheDocument();
    expect(screen.getByText('Readers finish faster than average')).toBeInTheDocument();
  });

  test('shows empty state instead of crashing when insights is null', () => {
    render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 0 }, insights: null, viewers: null } })} />);
    openTab('Insights');
    expect(screen.getByText('No insights yet — more reading sessions will generate patterns.')).toBeInTheDocument();
  });

  test('BUG-002-adjacent regression: raw envelope object degrades to empty state instead of throwing', () => {
    const rawEnvelope = { document_id: 'doc-1', filename: 'x.pdf', total_sessions: 2, insights: [{ type: 'info', message: 'x' }], generated_at: '2026-01-01T00:00:00Z' };
    expect(() => {
      render(<InsightsModal {...baseProps({ readingData: { summary: { total_sessions: 2 }, insights: rawEnvelope, viewers: null } })} />);
      openTab('Insights');
    }).not.toThrow();
    expect(screen.getByText('No insights yet — more reading sessions will generate patterns.')).toBeInTheDocument();
  });
});
