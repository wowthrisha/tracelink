import { C, mono } from '../constants/tokens.js';
import { ToastProvider } from '../contexts/toast.jsx';
import { Sidebar } from '../components/atoms.jsx';
import { ViewerErrorBoundary } from '../components/ViewerErrorBoundary.jsx';
import { LoginScreen } from './LoginScreen.jsx';
import { BillingScreen } from './BillingScreen.jsx';
import { StorageScreen } from './StorageScreen.jsx';
import { AnalyticsScreen } from './AnalyticsScreen.jsx';
import { UploadScreen } from './UploadScreen.jsx';
import { AccessScreen } from './AccessScreen.jsx';
import { ViewerScreen } from './ViewerScreen.jsx';
import { ApiKeysScreen } from './ApiKeysScreen.jsx';
import { WebhooksScreen } from './WebhooksScreen.jsx';
import { AuditLogScreen } from './AuditLogScreen.jsx';
import { OrgsScreen } from './OrgsScreen.jsx';
import { NotificationsScreen } from './NotificationsScreen.jsx';
const { useState, useEffect } = React;

function parseJwtEmail(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.email || '';
  } catch { return ''; }
}

// All screens are direct imports. app.jsx is the 5-line entry point.
export function AppShell() {
  const [token, setToken] = useState(() => localStorage.getItem('securedoc_token'));
  const [screen, setScreen] = useState('upload');
  const [activeDoc, setActiveDoc] = useState(null);
  const [plan, setPlan] = useState('free');
  const [feedbackBadge, setFeedbackBadge] = useState(null);

  const userEmail = token ? parseJwtEmail(token) : '';

  const handleViewDoc = doc => { setActiveDoc(doc); setScreen('viewer'); };
  const handleAccessDoc = doc => { setActiveDoc(doc); setScreen('access'); };
  const handleFeedbackDoc = doc => { setActiveDoc(doc); setScreen('feedback'); };
  const handleFeedbackNav = () => { setFeedbackBadge(null); setScreen('feedback'); };
  const handleLogin = (newToken) => {
    setToken(newToken);
    // If redirected back from Stripe checkout, go to billing screen
    const params = new URLSearchParams(window.location.search);
    if (params.get('billing') === 'success') {
      setScreen('billing');
      window.history.replaceState({}, '', window.location.pathname);
    }
  };
  const handleLogout = () => {
    localStorage.removeItem('securedoc_token');
    setToken(null);
  };

  // On mount: if returning from Stripe, go to billing screen
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('billing') === 'success' && token) {
      setScreen('billing');
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  // Fetch the real plan on mount instead of leaving the sidebar badge on its
  // 'free' default until the user happens to visit the Billing screen (which
  // was the only place that ever called setPlan) — a Pro user would otherwise
  // see "FREE" everywhere else in the app for the entire session.
  useEffect(() => {
    if (!token) return;
    fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/status`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setPlan(data.plan || 'free'); })
      .catch(() => {});
  }, [token]);

  // Fetch open (unresolved) feedback count when activeDoc changes
  useEffect(() => {
    if (!activeDoc?.id || !window.SecureDocAPI?.getFeedback) return;
    window.SecureDocAPI.getFeedback(activeDoc.id, { resolved: false })
      .then(data => {
        const items = Array.isArray(data) ? data : (data?.feedback || []);
        const roots = items.filter(a => !a.parent_id);
        setFeedbackBadge(roots.length > 0 ? roots.length : null);
      })
      .catch(() => setFeedbackBadge(null));
  }, [activeDoc?.id]);

  // Block unsupported small-screen layouts — desktop-only beta
  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    return (
      <div style={{
        height: '100vh', width: '100vw', background: '#080B0C',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        padding: 32, textAlign: 'center', gap: 20,
      }}>
        <div style={{ fontSize: 36 }}>◫</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.4px' }}>SecureDoc</div>
        <div style={{ fontSize: 14, color: '#5ac8d0', fontWeight: 600, maxWidth: 280, lineHeight: 1.6 }}>
          SecureDoc beta requires a desktop browser.
        </div>
        <div style={{ fontSize: 12, color: '#64748b', maxWidth: 280, lineHeight: 1.7 }}>
          Please open this link on a laptop or desktop computer running Chrome, Firefox, or Safari.
          Mobile support is planned for a future release.
        </div>
        <div style={{ fontSize: 10, color: '#334155', marginTop: 8, fontFamily: 'monospace' }}>
          min-width: 768px required
        </div>
      </div>
    );
  }

  if (!window.SecureDocAPI) {
    return (
      <ToastProvider>
        <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, background: C.bg, color: C.textMuted }}>
          <div style={{ ...mono, fontSize: 13, color: C.error }}>api.js not found</div>
          <div style={{ fontSize: 12, color: C.textMuted, textAlign: 'center', maxWidth: 380, lineHeight: 1.7 }}>
            Ensure <span style={{ ...mono, color: C.teal2 }}>api.js</span> is in the same directory.<br />
            Serve with: <span style={{ ...mono, color: C.teal2 }}>python3 -m http.server 5500</span>
          </div>
        </div>
      </ToastProvider>
    );
  }

  // Public viewer — bypass auth entirely
  const urlParams = new URLSearchParams(window.location.search);
  const hashToken = window.location.hash.startsWith('#view/') ? window.location.hash.slice(6) : null;
  const publicToken = hashToken || urlParams.get('token');

  if (publicToken) {
    return (
      <ToastProvider>
        <div style={{ height: '100vh', width: '100vw', background: C.bg, display: 'flex', flexDirection: 'column' }}>
          <ViewerErrorBoundary>
            <ViewerScreen doc={{ id: null }} publicToken={publicToken} />
          </ViewerErrorBoundary>
        </div>
      </ToastProvider>
    );
  }

  // Not authenticated — show login
  if (!token) {
    return (
      <ToastProvider>
        <LoginScreen onLogin={handleLogin} />
      </ToastProvider>
    );
  }

  // Authenticated — normal app
  return (
    <ToastProvider>
      <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: C.bg }}>
        <Sidebar active={screen} setActive={(id) => id === 'feedback' ? handleFeedbackNav() : setScreen(id)}
          userEmail={userEmail} onLogout={handleLogout} plan={plan}
          badges={{ feedback: feedbackBadge }} />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {screen === 'upload' && <UploadScreen onViewDoc={handleViewDoc} onAccessDoc={handleAccessDoc} />}
          {screen === 'viewer' && <ViewerErrorBoundary><ViewerScreen doc={activeDoc} onSelectDoc={handleViewDoc} onBack={() => setScreen('upload')} ownerEmail={userEmail} /></ViewerErrorBoundary>}
          {screen === 'access' && <AccessScreen doc={activeDoc} onSelectDoc={handleAccessDoc} />}
          {screen === 'feedback' && <AccessScreen doc={activeDoc} onSelectDoc={handleFeedbackDoc} defaultTab="feedback" />}
          {screen === 'analytics' && <AnalyticsScreen />}
          {screen === 'storage' && <StorageScreen />}
          {screen === 'billing' && <BillingScreen onPlanChange={setPlan} />}
          {screen === 'apikeys' && <ApiKeysScreen />}
          {screen === 'webhooks' && <WebhooksScreen />}
          {screen === 'auditlog' && <AuditLogScreen />}
          {screen === 'orgs' && <OrgsScreen />}
          {screen === 'notifications' && <NotificationsScreen />}
        </main>
      </div>
    </ToastProvider>
  );
}
