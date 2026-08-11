import { render, screen, waitFor } from '@testing-library/react';
import { AppShell } from '../AppShell.jsx';

// OBS-001 regression: a stale token left in localStorage past its `exp`
// claim used to be trusted at face value on the very first render — the
// authenticated shell (Sidebar + UploadScreen) mounted and immediately
// fired /api/documents, /api/groups, and /api/billing/status, all of which
// 401'd, which cleared the token and hard-reloaded the page back to the
// sign-in screen. Reproduced live via the browser (network log showed all
// three calls 401 after the authenticated UI had already mounted). The fix
// checks `exp` synchronously before the first render decision, so an
// expired token goes straight to LoginScreen with no intermediate flash
// and no network round trip.

function makeJwt(payload) {
  const b64 = (obj) => btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_');
  return `${b64({ alg: 'HS256' })}.${b64(payload)}.fakesignature`;
}

describe('AppShell — stale token / sign-in flash (OBS-001)', () => {
  const realFetch = global.fetch;

  beforeEach(() => {
    localStorage.clear();
    global.fetch = vi.fn().mockResolvedValue({ ok: false });
    window.SecureDocAPI.getDocuments = vi.fn().mockResolvedValue({ documents: [] });
    window.SecureDocAPI.getAnalyticsOverview = vi.fn().mockResolvedValue({});
    window.SecureDocAPI.getGroups = vi.fn().mockResolvedValue({ groups: [] });
  });

  afterEach(() => {
    global.fetch = realFetch;
    localStorage.clear();
  });

  test('an expired token goes straight to the sign-in screen on first render, not the authenticated shell', async () => {
    const expired = makeJwt({ email: 'stale@example.com', exp: Math.floor(Date.now() / 1000) - 3600 });
    localStorage.setItem('securedoc_token', expired);

    render(<AppShell />);

    expect(await screen.findByPlaceholderText('you@example.com')).toBeInTheDocument();
    // The authenticated shell (and its data fetches) must never have mounted.
    expect(window.SecureDocAPI.getDocuments).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('an expired token is removed from localStorage immediately, before any API round trip', () => {
    const expired = makeJwt({ email: 'stale@example.com', exp: Math.floor(Date.now() / 1000) - 3600 });
    localStorage.setItem('securedoc_token', expired);

    render(<AppShell />);

    expect(localStorage.getItem('securedoc_token')).toBeNull();
  });

  test('a token with a future exp still renders the authenticated shell normally', async () => {
    const valid = makeJwt({ email: 'active@example.com', exp: Math.floor(Date.now() / 1000) + 3600 });
    localStorage.setItem('securedoc_token', valid);

    render(<AppShell />);

    await waitFor(() => expect(window.SecureDocAPI.getDocuments).toHaveBeenCalled());
    expect(screen.queryByText('Sign In')).not.toBeInTheDocument();
  });

  test('a token with no exp claim at all is treated as valid (unchanged prior behavior)', async () => {
    const noExp = makeJwt({ email: 'noexp@example.com' });
    localStorage.setItem('securedoc_token', noExp);

    render(<AppShell />);

    await waitFor(() => expect(window.SecureDocAPI.getDocuments).toHaveBeenCalled());
    expect(localStorage.getItem('securedoc_token')).toBe(noExp);
  });
});
