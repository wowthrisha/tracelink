import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn } from '../components/atoms.jsx';
const { useState, useEffect, useCallback } = React;

const PAGE_SIZE = 50;

function fmtTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

const ACTION_COLORS = {
  create: C.success,
  update: C.teal1,
  delete: C.error,
  view: C.textMuted,
  login: C.textSecondary,
  export: C.warning,
};

function actionColor(action) {
  if (!action) return C.textDim;
  const key = Object.keys(ACTION_COLORS).find(k => action.toLowerCase().includes(k));
  return key ? ACTION_COLORS[key] : C.textMuted;
}

export function AuditLogScreen() {
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(null);

  const fetchPage = useCallback(async (off) => {
    setLoading(true);
    try {
      const data = await window.SecureDocAPI.getAuditLog(null, PAGE_SIZE, off);
      const rows = data?.events || data?.items || data?.audit_log || [];
      if (off === 0) {
        setEvents(rows);
      } else {
        setEvents(prev => [...prev, ...rows]);
      }
      if (data?.total != null) setTotal(data.total);
      setHasMore(rows.length === PAGE_SIZE);
      setOffset(off + rows.length);
    } catch (e) { toast(_errMsg(e, 'Failed to load audit log'), 'error'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchPage(0); }, [fetchPage]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="auditlog" />

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>≡</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>Audit Log</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              Immutable record of all actions performed in your account. Includes API key usage, document operations, configuration changes, and admin actions.
              {total != null && <span style={{ color: C.textSecondary }}> {total.toLocaleString()} total events.</span>}
            </div>
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Events</SectionLabel>
            {total != null && (
              <Chip color={C.textMuted} bg="transparent" border={C.border}>{total.toLocaleString()} events</Chip>
            )}
          </div>

          {loading && events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>No audit events yet.</div>
          ) : (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {['Time', 'Action', 'Resource', 'Actor', 'IP / Context'].map(h => (
                      <th key={h} style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, padding: '7px 14px', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev, i) => (
                    <tr key={ev.id || i} style={{ borderBottom: i < events.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textDim, whiteSpace: 'nowrap' }}>{fmtTime(ev.created_at || ev.timestamp)}</td>
                      <td style={{ padding: '9px 14px' }}>
                        <span style={{ ...mono, fontSize: 10, fontWeight: 600, color: actionColor(ev.action) }}>{ev.action || '—'}</span>
                      </td>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textSecondary }}>
                        {ev.resource_type && <span style={{ marginRight: 4, color: C.textMuted }}>{ev.resource_type}</span>}
                        {ev.resource_id && <span style={{ color: C.teal2 }}>{String(ev.resource_id).slice(0, 8)}…</span>}
                        {!ev.resource_type && !ev.resource_id && <span style={{ color: C.textDim }}>—</span>}
                      </td>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textSecondary }}>
                        {ev.actor_email || ev.actor_id || '—'}
                      </td>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textDim }}>
                        {ev.ip_address || ev.metadata?.ip || ev.context || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {hasMore && (
                <div style={{ padding: '12px 16px', borderTop: `1px solid ${C.border}`, display: 'flex', justifyContent: 'center' }}>
                  <Btn variant="ghost" size="sm" onClick={() => fetchPage(offset)} disabled={loading} style={{ fontSize: 11 }}>
                    {loading ? 'Loading…' : 'Load more'}
                  </Btn>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
