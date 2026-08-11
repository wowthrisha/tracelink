import { render, screen, fireEvent } from '@testing-library/react';
import { ViewerToolbar } from '../ViewerToolbar.jsx';

// BUG-005 regression: when download/print are disabled for a viewer session,
// the toolbar buttons used the native `disabled` HTML attribute. Disabled
// buttons are removed from the Tab order entirely (verified live: calling
// .focus() on one does nothing, document.activeElement stays <body>), so
// keyboard/screen-reader users could never reach the button to hear its
// aria-label explaining why the action was blocked. Clicking (for mouse
// users) also silently no-opped in the onDownload/onPrint handlers. The fix
// switches to aria-disabled (keeps the button focusable/clickable, still
// visually inert) and the click handlers now show an explanatory toast
// instead of silently returning — these tests cover the toolbar half of
// that fix (the button stays keyboard-reachable and always fires onClick).

const baseProps = (overrides = {}) => ({
  doc: { group_name: 'General', group_color: '#6b7280' },
  docName: 'Test.pdf',
  isTextDoc: true, // skips the zoom/rotate block, which needs LAYOUT/ZOOM_PRESETS
  page: 1, PAGE_COUNT: 3, pageInputStr: '', setPageInputStr: vi.fn(), setPage: vi.fn(),
  goPrev: vi.fn(), goNext: vi.fn(),
  layoutMode: null, customZoom: null, _zoomBy: vi.fn(), _zoomTo: vi.fn(), _setLayout: vi.fn(),
  LAYOUT: {}, ZOOM_STEP: 10, ZOOM_PRESETS: [],
  showLaser: false, setShowLaser: vi.fn(), showMagnifier: false, setShowMagnifier: vi.fn(),
  showInsights: false, setShowInsights: vi.fn(), hasInsights: false,
  showLinks: false, setShowLinks: vi.fn(), linksCount: 0,
  isFullscreen: false, toggleFullscreen: vi.fn(),
  showToc: false, setShowToc: vi.fn(), showSearch: false, setShowSearch: vi.fn(),
  showInfo: false, setShowInfo: vi.fn(), showPageList: false, setShowPageList: vi.fn(),
  canDownload: false, canPrint: false, canInfo: true, canAnnotate: false,
  onDownload: vi.fn(), onPrint: vi.fn(),
  annotTool: null, setAnnotTool: vi.fn(), annotColor: '#000', setAnnotColor: vi.fn(),
  annotThickness: 2, setAnnotThickness: vi.fn(), annotUndoStack: [], onAnnotUndo: vi.fn(),
  bookmarked: false, onToggleBookmark: vi.fn(),
  rotation: 0, onRotate: vi.fn(), isTwoPage: false, onToggleTwoPage: vi.fn(),
  onBack: vi.fn(),
  C: {}, mono: {},
  ...overrides,
});

describe('ViewerToolbar — blocked download/print feedback (BUG-005)', () => {
  test('download button is not natively disabled when blocked, so it stays keyboard-focusable', () => {
    render(<ViewerToolbar {...baseProps({ canDownload: false })} />);
    const btn = screen.getByLabelText('Download not permitted');
    expect(btn.disabled).toBe(false);
    expect(btn.getAttribute('aria-disabled')).toBe('true');
  });

  test('print button is not natively disabled when blocked, so it stays keyboard-focusable', () => {
    render(<ViewerToolbar {...baseProps({ canPrint: false })} />);
    const btn = screen.getByLabelText('Print not permitted');
    expect(btn.disabled).toBe(false);
    expect(btn.getAttribute('aria-disabled')).toBe('true');
  });

  test('clicking the blocked download button still fires onDownload (so the caller can show feedback)', () => {
    const onDownload = vi.fn();
    render(<ViewerToolbar {...baseProps({ canDownload: false, onDownload })} />);
    fireEvent.click(screen.getByLabelText('Download not permitted'));
    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  test('clicking the blocked print button still fires onPrint (so the caller can show feedback)', () => {
    const onPrint = vi.fn();
    render(<ViewerToolbar {...baseProps({ canPrint: false, onPrint })} />);
    fireEvent.click(screen.getByLabelText('Print not permitted'));
    expect(onPrint).toHaveBeenCalledTimes(1);
  });

  test('blocked buttons remain visually dimmed with a not-allowed cursor (do not look functional)', () => {
    render(<ViewerToolbar {...baseProps({ canDownload: false, canPrint: false })} />);
    const dl = screen.getByLabelText('Download not permitted');
    const pr = screen.getByLabelText('Print not permitted');
    expect(dl.style.opacity).toBe('0.28');
    expect(dl.style.cursor).toBe('not-allowed');
    expect(pr.style.opacity).toBe('0.28');
    expect(pr.style.cursor).toBe('not-allowed');
  });

  test('permitted download/print buttons are fully interactive and not aria-disabled', () => {
    render(<ViewerToolbar {...baseProps({ canDownload: true, canPrint: true })} />);
    const dl = screen.getByLabelText('Download document');
    const pr = screen.getByLabelText('Print document');
    expect(dl.getAttribute('aria-disabled')).toBe('false');
    expect(pr.getAttribute('aria-disabled')).toBe('false');
    expect(dl.style.cursor).toBe('pointer');
    expect(pr.style.cursor).toBe('pointer');
  });
});
