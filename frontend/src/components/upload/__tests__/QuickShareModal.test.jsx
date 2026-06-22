import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QuickShareModal } from '../QuickShareModal.jsx';

const makeDoc = (overrides = {}) => ({
  id: 'doc-123',
  filename: 'Proposal.pdf',
  status: 'ready',
  ...overrides,
});

const defaultProps = (overrides = {}) => ({
  doc: makeDoc(),
  onClose: vi.fn(),
  onConfigure: vi.fn(),
  ...overrides,
});

describe('QuickShareModal', () => {
  beforeEach(() => {
    window.SecureDocAPI.createLink = vi.fn().mockResolvedValue({
      share_url: 'https://example.com/view/abc123',
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ── Success path ──────────────────────────────────────────────────────────

  test('shows loading state on mount', () => {
    // Never resolves — stays in loading
    window.SecureDocAPI.createLink = vi.fn(() => new Promise(() => {}));
    render(<QuickShareModal {...defaultProps()} />);
    expect(screen.getByText('Creating share link…')).toBeInTheDocument();
  });

  test('calls createLink with correct payload on mount', async () => {
    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() => expect(window.SecureDocAPI.createLink).toHaveBeenCalledTimes(1));
    expect(window.SecureDocAPI.createLink).toHaveBeenCalledWith({
      document_id: 'doc-123',
      label: 'Quick Share',
      permissions: {
        can_download: false,
        can_print: false,
        can_copy: false,
        can_right_click: false,
        watermark_enabled: true,
        can_annotate: false,
        enable_info: true,
      },
    });
  });

  test('displays share URL after successful link creation', async () => {
    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() =>
      expect(screen.getByText('https://example.com/view/abc123')).toBeInTheDocument()
    );
  });

  test('shows copy button in ready state', async () => {
    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() => expect(screen.getByRole('button', { name: /copy link/i })).toBeInTheDocument());
  });

  test('copy button changes to "Copied" after click', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });

    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() => screen.getByRole('button', { name: /copy link/i }));

    fireEvent.click(screen.getByRole('button', { name: /copy link/i }));
    await waitFor(() => expect(screen.getByText(/copied/i)).toBeInTheDocument());
  });

  // ── API failure path ──────────────────────────────────────────────────────

  test('shows error message when createLink fails', async () => {
    window.SecureDocAPI.createLink = vi.fn().mockRejectedValue({
      detail: 'Link quota exceeded',
    });

    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() => expect(screen.getByText('Link quota exceeded')).toBeInTheDocument());
  });

  test('shows generic error when API returns no detail', async () => {
    window.SecureDocAPI.createLink = vi.fn().mockRejectedValue({});

    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() =>
      expect(screen.getByText('Failed to create share link')).toBeInTheDocument()
    );
  });

  test('retry button calls createLink again', async () => {
    window.SecureDocAPI.createLink = vi.fn().mockRejectedValue({ detail: 'Server error' });

    render(<QuickShareModal {...defaultProps()} />);
    await waitFor(() => screen.getByRole('button', { name: /retry/i }));

    // Make next call succeed
    window.SecureDocAPI.createLink = vi.fn().mockResolvedValue({
      share_url: 'https://example.com/view/retry-token',
    });

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() =>
      expect(screen.getByText('https://example.com/view/retry-token')).toBeInTheDocument()
    );
  });

  // ── Loading state / duplicate click guard ─────────────────────────────────

  test('loading spinner is shown while createLink is in-flight', () => {
    window.SecureDocAPI.createLink = vi.fn(() => new Promise(() => {}));
    render(<QuickShareModal {...defaultProps()} />);
    expect(screen.getByText('Creating share link…')).toBeInTheDocument();
    // No URL shown yet
    expect(screen.queryByText(/example\.com/)).not.toBeInTheDocument();
  });

  // ── Configure path ────────────────────────────────────────────────────────

  test('Configure link calls onClose and onConfigure with the doc', async () => {
    const onClose = vi.fn();
    const onConfigure = vi.fn();
    const doc = makeDoc();

    render(<QuickShareModal doc={doc} onClose={onClose} onConfigure={onConfigure} />);
    await waitFor(() => screen.getByText(/configure in access control/i));

    fireEvent.click(screen.getByText(/configure in access control/i));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onConfigure).toHaveBeenCalledWith(doc);
  });

  // ── Modal close ───────────────────────────────────────────────────────────

  test('Close (✕) button calls onClose', async () => {
    const onClose = vi.fn();
    render(<QuickShareModal {...defaultProps({ onClose })} />);
    await waitFor(() => screen.getByText('https://example.com/view/abc123'));

    // The Modal atom renders a ✕ close button
    fireEvent.click(screen.getByText('✕'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('Done button calls onClose', async () => {
    const onClose = vi.fn();
    render(<QuickShareModal {...defaultProps({ onClose })} />);
    await waitFor(() => screen.getByRole('button', { name: /done/i }));

    fireEvent.click(screen.getByRole('button', { name: /done/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // ── Long filename truncation ──────────────────────────────────────────────

  test('truncates very long filenames in modal title', async () => {
    const doc = makeDoc({ filename: 'A'.repeat(60) + '.pdf' });
    render(<QuickShareModal {...defaultProps({ doc })} />);
    // Modal title should be present and not overflow to 60+ chars
    await waitFor(() => {
      const title = screen.getByText(/^Share "/);
      expect(title.textContent.length).toBeLessThan(70);
    });
  });
});
