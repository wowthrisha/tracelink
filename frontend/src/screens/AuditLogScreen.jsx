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
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [eventType, setEventType] = useState('');
  const [availableEventTypes, setAvailableEventTypes] = useState([]);
  const [exporting, setExporting] = useState(false);

  const fetchPage = useCallback(async (off, filters = {}) => {
    setLoading(true);
    try {
      const data = await window.SecureDocAPI.getAuditLog(null, PAGE_SIZE, off, {
        dateFrom: filters.dateFrom ?? dateFrom,
        dateTo: filters.dateTo ?? dateTo,
        eventType: filters.eventType ?? eventType,
      });
      const rows = data?.events || data?.items || data?.audit_log || [];
      if (off === 0) {
        setEvents(rows);
      } else {
        setEvents(prev => [...prev, ...rows]);
      }
      if (data?.total != null) setTotal(data.total);
      if (data?.available_event_types) setAvailableEventTypes(data.available_event_types);
      setHasMore(rows.length === PAGE_SIZE);
      setOffset(off + rows.length);
    } catch (e) { toast(_errMsg(e, 'Failed to load audit log'), 'error'); }
    finally { setLoading(false); }
  }, [dateFrom, dateTo, eventType]);

  useEffect(() => { fetchPage(0); }, []);

  const applyFilters = () => {
    setOffset(0);
    setHasMore(true);
    fetchPage(0);
  };

  const clearFilters = () => {
    setDateFrom('');
    setDateTo('');
    setEventType('');
    setOffset(0);
    setHasMore(true);
    fetchPage(0, { dateFrom: '', dateTo: '', eventType: '' });
  };

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      // Fetch all matching events up to 500 (backend max)
      const data = await window.SecureDocAPI.getAuditLog(null, 500, 0, { dateFrom, dateTo, eventType });
      const rows = data?.events || [];
      const headers = ['Time', 'Event Type', 'Target Type', 'Target ID', 'Actor ID'];
      const csvRows = [
        headers.join(','),
        ...rows.map(ev => [
          ev.created_at || '',
          ev.event_type || '',
          ev.target_type || '',
          ev.target_id || '',
          ev.actor_user_id || '',
        ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')),
      ];
      const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast(`Exported ${rows.length} events`, 'success');
    } catch (e) { toast(_errMsg(e, 'Export failed'), 'error'); }
    finally { setExporting(false); }
  };

  const hasActiveFilters = dateFrom || dateTo || eventType;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="auditlog">
        <Btn variant="secondary" size="sm" loading={exporting} onClick={handleExportCSV} style={{ fontSize: 10 }}>
          ↓ Export CSV
        </Btn>
      </Header>

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

        {/* Filters */}
        <Card style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px' }}>From</span>
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '5px 8px', color: C.textPrimary }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px' }}>To</span>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '5px 8px', color: C.textPrimary }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px' }}>Event Type</span>
              <select value={eventType} onChange={e => setEventType(e.target.value)}
                style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '5px 8px', color: eventType ? C.textPrimary : C.textMuted }}>
                <option value="">All events</option>
                {availableEventTypes.map(et => (
                  <option key={et} value={et}>{et}</option>
                ))}
              </select>
            </div>
            <Btn variant="primary" size="sm" onClick={applyFilters} disabled={loading} style={{ fontSize: 11 }}>Apply</Btn>
            {hasActiveFilters && (
              <Btn variant="ghost" size="sm" onClick={clearFilters} style={{ fontSize: 11, color: C.textMuted }}>Clear</Btn>
            )}
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Events</SectionLabel>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {hasActiveFilters && <Chip color={C.teal2} bg="rgba(90,200,208,0.08)" border="rgba(90,200,208,0.2)">Filtered</Chip>}
              {total != null && (
                <Chip color={C.textMuted} bg="transparent" border={C.border}>{total.toLocaleString()} events</Chip>
              )}
            </div>
          </div>

          {loading && events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
              {hasActiveFilters ? 'No events match the current filters.' : 'No audit events yet.'}
            </div>
          ) : (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {['Time', 'Action', 'Resource', 'Actor', 'IP / Context'].map(h => (
                      <th key={h} scope="col" style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, padding: '7px 14px', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev, i) => (
                    <tr key={ev.id || i} style={{ borderBottom: i < events.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textDim, whiteSpace: 'nowrap' }}>{fmtTime(ev.created_at || ev.timestamp)}</td>
                      <td style={{ padding: '9px 14px' }}>
                        <span style={{ ...mono, fontSize: 10, fontWeight: 600, color: actionColor(ev.event_type || ev.action) }}>{ev.event_type || ev.action || '—'}</span>
                      </td>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textSecondary }}>
                        {ev.target_type && <span style={{ marginRight: 4, color: C.textMuted }}>{ev.target_type}</span>}
                        {ev.target_id && <span style={{ color: C.teal2 }}>{String(ev.target_id).slice(0, 8)}…</span>}
                        {(ev.resource_type || ev.resource_id) && (
                          <>
                            {ev.resource_type && <span style={{ marginRight: 4, color: C.textMuted }}>{ev.resource_type}</span>}
                            {ev.resource_id && <span style={{ color: C.teal2 }}>{String(ev.resource_id).slice(0, 8)}…</span>}
                          </>
                        )}
                        {!ev.target_type && !ev.target_id && !ev.resource_type && !ev.resource_id && <span style={{ color: C.textDim }}>—</span>}
                      </td>
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textSecondary }}>
                        {ev.actor_email || (ev.api_key_id ? `API Key (${String(ev.api_key_id).slice(0, 8)}…)` : null) || (ev.actor_user_id && String(ev.actor_user_id).slice(0, 8) + '…') || ev.actor_id || '—'}
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
