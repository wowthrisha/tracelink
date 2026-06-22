import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header } from '../components/atoms.jsx';
const { useState, useEffect } = React;

function fmtBytes(b) {
  if (!b) return '0 B';
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(2)} MB`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function lifecycleBadge(state) {
  const styles = {
    active:   { background: 'rgba(52,199,89,0.12)',  color: '#34c759' },
    archived: { background: 'rgba(100,100,120,0.18)', color: '#888' },
    expired:  { background: 'rgba(255,69,58,0.12)',  color: '#ff453a' },
    deleted:  { background: 'rgba(255,69,58,0.08)',  color: '#ff453a' },
  };
  const s = styles[state] || styles.active;
  return (
    <span style={{ ...s, fontSize: 9, fontWeight: 700, borderRadius: 4, padding: '2px 6px', textTransform: 'uppercase', letterSpacing: '.5px' }}>
      {state}
    </span>
  );
}

export function StorageScreen() {
  const toast = useToast();
  const [dashboard, setDashboard] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);

  useEffect(() => {
    Promise.all([
      window.SecureDocAPI.getStorageDashboard(),
      window.SecureDocAPI.getStorageForecast(),
    ]).then(([d, f]) => { setDashboard(d); setForecast(f); })
      .catch(e => toast(_errMsg(e, 'Failed to load storage data'), 'error'))
      .finally(() => setLoading(false));
  }, []);

  const handleRetentionChange = async (docId, policy) => {
    setUpdatingId(docId);
    try {
      await window.SecureDocAPI.updateRetention(docId, policy);
      const d = await window.SecureDocAPI.getStorageDashboard();
      setDashboard(d);
      toast('Retention policy updated', 'success');
    } catch (e) { toast(_errMsg(e, 'Update failed'), 'error'); }
    finally { setUpdatingId(null); }
  };

  if (loading) return <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.textMuted, fontSize: 13 }}>Loading…</div>;

  const totalBytes = dashboard?.total_bytes || 0;
  const maxBytes = Math.max(...(dashboard?.by_document || []).map(d => d.storage_bytes), 1);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="storage">
        <span style={{ ...mono, fontSize: 11, color: C.textMuted }}>
          {fmtBytes(totalBytes)} used · {dashboard?.document_count || 0} documents
        </span>
      </Header>
      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Summary cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
          {[
            { label: 'Total Storage', value: fmtBytes(totalBytes), sub: `${dashboard?.document_count ?? 0} docs`, color: C.teal2 },
            { label: '30-Day Projection', value: fmtBytes(forecast?.projected_30d_bytes || 0), sub: `+${fmtBytes(forecast?.daily_growth_bytes || 0)}/day`, color: C.textSecondary },
            { label: '90-Day Projection', value: fmtBytes(forecast?.projected_90d_bytes || 0), sub: forecast?.planned_deletions_90d_bytes ? `−${fmtBytes(forecast.planned_deletions_90d_bytes)} planned deletions` : 'No scheduled deletions', color: forecast?.planned_deletions_90d_bytes ? C.warning : C.textMuted },
          ].map(s => (
            <Card key={s.label} style={{ padding: '14px 18px' }}>
              <div style={{ fontSize: 10, color: C.textMuted, fontWeight: 600, letterSpacing: '.5px', textTransform: 'uppercase', marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color, marginBottom: 2 }}>{s.value}</div>
              <div style={{ ...mono, fontSize: 10, color: C.textMuted }}>{s.sub}</div>
            </Card>
          ))}
        </div>

        {/* Per-org breakdown */}
        {(dashboard?.by_org || []).length > 1 && (
          <Card style={{ padding: '14px 18px' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.textSecondary, marginBottom: 10 }}>Storage by Organization</div>
            {(dashboard.by_org || []).map(org => (
              <div key={org.org_id} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <div style={{ ...mono, fontSize: 11, color: C.textMuted, width: 120, flexShrink: 0 }}>
                  {org.org_id === '_personal' ? 'Personal' : org.org_id.slice(0, 8) + '…'}
                </div>
                <div style={{ flex: 1, height: 6, background: C.surface3, borderRadius: 3 }}>
                  <div style={{ height: '100%', width: `${Math.min(100, (org.total_bytes / totalBytes) * 100)}%`, background: C.teal2, borderRadius: 3 }} />
                </div>
                <div style={{ ...mono, fontSize: 11, color: C.textSecondary, width: 70, textAlign: 'right' }}>{fmtBytes(org.total_bytes)}</div>
              </div>
            ))}
          </Card>
        )}

        {/* Per-document table */}
        <Card style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 18px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.textSecondary }}>Storage by Document</div>
            <div style={{ ...mono, fontSize: 10, color: C.textMuted }}>Retention policy · delete after</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: C.surface2 }}>
                  {['Document', 'State', 'Size', 'Usage', 'Expires', 'Delete after'].map(h => (
                    <th key={h} style={{ ...mono, fontSize: 9, color: C.textMuted, padding: '6px 14px', textAlign: 'left', fontWeight: 600, letterSpacing: '.5px', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(dashboard?.by_document || []).map(doc => (
                  <tr key={doc.id} style={{ borderTop: `1px solid ${C.border}` }}>
                    <td style={{ padding: '8px 14px', maxWidth: 220 }}>
                      <div style={{ fontSize: 12, color: C.textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.filename}</div>
                      <div style={{ ...mono, fontSize: 9, color: C.textMuted }}>{doc.id.slice(0, 8)}…</div>
                    </td>
                    <td style={{ padding: '8px 14px' }}>{lifecycleBadge(doc.lifecycle_state)}</td>
                    <td style={{ ...mono, padding: '8px 14px', fontSize: 11, color: C.textSecondary }}>{fmtBytes(doc.storage_bytes)}</td>
                    <td style={{ padding: '8px 14px', minWidth: 100 }}>
                      <div style={{ height: 4, background: C.surface3, borderRadius: 2 }}>
                        <div style={{ height: '100%', width: `${Math.min(100, (doc.storage_bytes / maxBytes) * 100)}%`, background: C.teal2, borderRadius: 2 }} />
                      </div>
                    </td>
                    <td style={{ ...mono, padding: '8px 14px', fontSize: 10, color: doc.expires_at ? C.warning : C.textMuted }}>
                      {doc.expires_at ? new Date(doc.expires_at).toLocaleDateString() : '—'}
                    </td>
                    <td style={{ padding: '8px 14px' }}>
                      <select
                        disabled={updatingId === doc.id}
                        value={doc.retention_policy}
                        onChange={e => handleRetentionChange(doc.id, e.target.value)}
                        style={{
                          fontSize: 10, background: C.surface2, border: `1px solid ${C.border}`,
                          borderRadius: 5, padding: '3px 6px', color: C.textSecondary,
                          opacity: updatingId === doc.id ? 0.5 : 1,
                        }}>
                        <option value="never">Never</option>
                        <option value="30_days">30 days</option>
                        <option value="60_days">60 days</option>
                        <option value="90_days">90 days</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

      </div>
    </div>
  );
}
