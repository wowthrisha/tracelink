import { C } from '../constants/tokens.js';
import { fmtDate } from '../utils/viewer.js';
const { useState, useEffect } = React;

function authHeaders() {
  const token = localStorage.getItem('securedoc_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export function BillingScreen({ onPlanChange }) {
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState('');
  const [error, setError] = useState('');

  async function load(silent = false) {
    if (!silent) setLoading(true); else setRefreshing(true);
    try {
      const r = await fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/status`, {
        headers: { ...authHeaders() },
      });
      if (r.ok) {
        const data = await r.json();
        setBilling(data);
        if (onPlanChange) onPlanChange(data.plan || 'free');
      }
    } catch {}
    finally { if (!silent) setLoading(false); else setRefreshing(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleUpgrade() {
    setActionLoading('upgrade');
    setError('');
    try {
      const r = await fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/checkout`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });
      if (r.status === 503) {
        setError('Billing is not configured on this server.');
        return;
      }
      if (!r.ok) {
        const d = await r.json();
        setError(d.detail || 'Failed to start checkout.');
        return;
      }
      const { url } = await r.json();
      window.location.href = url;
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setActionLoading('');
    }
  }

  async function handleManage() {
    setActionLoading('manage');
    setError('');
    try {
      const r = await fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/portal`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });
      if (!r.ok) {
        const d = await r.json();
        setError(d.detail || 'Failed to open billing portal.');
        return;
      }
      const { url } = await r.json();
      window.open(url, '_blank');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setActionLoading('');
    }
  }

  const isPro = billing?.plan === 'pro';
  const billingEnabled = billing?.billing_enabled !== false;

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', maxWidth: 640 }}>
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary, marginBottom: 4 }}>Billing & Plan</div>
          <div style={{ fontSize: 12, color: C.textMuted }}>Manage your subscription and usage.</div>
        </div>
        <button onClick={() => load(true)} disabled={refreshing || loading}
          style={{ fontSize: 11, color: C.textMuted, background: 'none', border: 'none', cursor: refreshing ? 'not-allowed' : 'pointer', padding: '4px 8px', opacity: refreshing ? 0.5 : 1 }}
          title="Refresh billing status">
          {refreshing ? '…' : '↻ Refresh'}
        </button>
      </div>

      {loading ? (
        <div style={{ color: C.textMuted, fontSize: 13 }}>Loading billing status…</div>
      ) : (
        <>
          {/* Current plan card */}
          <div style={{
            background: C.surface, border: `1px solid ${isPro ? C.borderMed : C.border}`,
            borderRadius: 12, padding: '20px 22px', marginBottom: 16,
            boxShadow: isPro ? `0 0 24px rgba(90,200,208,0.08)` : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <div>
                <div style={{ fontSize: 11, color: C.textDim, letterSpacing: '0.8px', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>Current Plan</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary }}>{isPro ? 'Pro' : 'Free'}</span>
                  {isPro && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.8px',
                      background: `linear-gradient(135deg, ${C.teal1}, ${C.teal3})`,
                      color: '#080B0C', padding: '2px 7px', borderRadius: 4,
                    }}>ACTIVE</span>
                  )}
                </div>
              </div>
              {billing?.subscription_status && billing.subscription_status !== 'inactive' && (
                <div style={{ fontSize: 11, color: C.textMuted, textAlign: 'right' }}>
                  <div style={{ color: billing.subscription_status === 'active' ? C.success : C.warning }}>
                    {billing.subscription_status.replace('_', ' ').toUpperCase()}
                  </div>
                  {billing.current_period_end && (
                    <div style={{ marginTop: 2 }}>
                      Renews {fmtDate(billing.current_period_end)}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Feature list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {[
                { label: 'Document uploads', value: isPro ? 'Unlimited' : 'Up to 10' },
                { label: 'Share links per document', value: 'Unlimited' },
                { label: 'Access control & password protection', value: 'Included' },
                { label: 'Viewer analytics', value: 'Included' },
                { label: 'Watermarking', value: 'Included' },
                { label: 'Priority support', value: isPro ? 'Included' : '—' },
              ].map(({ label: lbl, value }) => (
                <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: C.textMuted }}>{lbl}</span>
                  <span style={{ color: value === '—' ? C.textDim : C.textPrimary, fontWeight: 500 }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div style={{
              fontSize: 12, color: C.error, background: C.errorBg,
              border: `1px solid ${C.errorBdr}`, borderRadius: 7,
              padding: '9px 12px', marginBottom: 14, lineHeight: 1.5
            }}>{error}</div>
          )}

          {!billingEnabled && (
            <div style={{
              fontSize: 12, color: C.textMuted, background: 'rgba(255,255,255,0.03)',
              border: `1px solid ${C.border}`, borderRadius: 7,
              padding: '9px 12px', marginBottom: 14, lineHeight: 1.5
            }}>
              Billing is not configured on this server. Contact your administrator to enable paid plan upgrades.
            </div>
          )}

          <div style={{ display: 'flex', gap: 10 }}>
            {!isPro && billingEnabled && (
              <button
                onClick={handleUpgrade}
                disabled={actionLoading === 'upgrade'}
                style={{
                  padding: '10px 20px', border: 'none', borderRadius: 8,
                  background: actionLoading === 'upgrade' ? C.teal3 : C.teal2,
                  color: '#080B0C', fontFamily: "'DM Sans', sans-serif",
                  fontSize: 13, fontWeight: 700, cursor: actionLoading === 'upgrade' ? 'not-allowed' : 'pointer',
                }}>
                {actionLoading === 'upgrade' ? 'Redirecting…' : 'Upgrade to Pro'}
              </button>
            )}
            {isPro && billing?.stripe_customer_id && billingEnabled && (
              <button
                onClick={handleManage}
                disabled={actionLoading === 'manage'}
                style={{
                  padding: '10px 20px', border: `1px solid ${C.borderMed}`, borderRadius: 8,
                  background: 'transparent', color: C.teal1,
                  fontFamily: "'DM Sans', sans-serif", fontSize: 13, fontWeight: 600,
                  cursor: actionLoading === 'manage' ? 'not-allowed' : 'pointer',
                }}>
                {actionLoading === 'manage' ? 'Opening…' : 'Manage Subscription'}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
