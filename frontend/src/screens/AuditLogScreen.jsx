import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn } from '../components/atoms.jsx';
const { useState, useEffect, useCallback, useRef } = React;

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
  const [search, setSearch] = useState('');
  const [availableEventTypes, setAvailableEventTypes] = useState([]);
  const [exporting, setExporting] = useState(false);
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');

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

  const _fetchAllForExport = async () => {
    const data = await window.SecureDocAPI.getAuditLog(null, 500, 0, { dateFrom, dateTo, eventType });
    return data?.events || [];
  };

  const handleExportCSV = async () => {
    setExporting('csv');
    try {
      const rows = await _fetchAllForExport();
      const headers = ['Time', 'Event Type', 'Target Type', 'Target ID', 'Actor', 'Details'];
      const csvRows = [
        headers.join(','),
        ...rows.map(ev => [
          ev.created_at || '',
          ev.event_type || ev.action || '',
          ev.target_type || ev.resource_type || '',
          ev.target_id || ev.resource_id || '',
          ev.actor_email || ev.actor_user_id || '',
          ev.details ? JSON.stringify(ev.details) : '',
        ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')),
      ];
      const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast(total != null && rows.length < total
        ? `Exported ${rows.length} of ${total.toLocaleString()} events (CSV export is capped at 500 — narrow your date range to get the rest).`
        : `Exported ${rows.length} events as CSV`, total != null && rows.length < total ? 'warning' : 'success');
    } catch (e) { toast(_errMsg(e, 'Export failed'), 'error'); }
    finally { setExporting(false); }
  };

  const handleExportJSON = async () => {
    setExporting('json');
    try {
      const rows = await _fetchAllForExport();
      const blob = new Blob([JSON.stringify({ audit_log: rows, exported_at: new Date().toISOString(), count: rows.length, total_matching: total }, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast(total != null && rows.length < total
        ? `Exported ${rows.length} of ${total.toLocaleString()} events (JSON export is capped at 500 — narrow your date range to get the rest).`
        : `Exported ${rows.length} events as JSON`, total != null && rows.length < total ? 'warning' : 'success');
    } catch (e) { toast(_errMsg(e, 'Export failed'), 'error'); }
    finally { setExporting(false); }
  };

  const hasActiveFilters = dateFrom || dateTo || eventType || search;

  // Client-side search filter (applied after fetch to avoid extra round-trips)
  const filteredEvents = search.trim()
    ? events.filter(ev => {
        const q = search.toLowerCase();
        return (
          (ev.event_type || ev.action || '').toLowerCase().includes(q) ||
          (ev.target_type || ev.resource_type || '').toLowerCase().includes(q) ||
          (ev.actor_email || '').toLowerCase().includes(q) ||
          (ev.actor_user_id || '').toLowerCase().includes(q) ||
          JSON.stringify(ev.details || {}).toLowerCase().includes(q)
        );
      })
    : events;

  // Client-side sort
  const sortedEvents = [...filteredEvents].sort((a, b) => {
    let av = a[sortKey] || a.timestamp || '';
    let bv = b[sortKey] || b.timestamp || '';
    if (sortKey === 'event_type') { av = a.event_type || a.action || ''; bv = b.event_type || b.action || ''; }
    if (sortKey === 'actor') { av = a.actor_email || a.actor_user_id || ''; bv = b.actor_email || b.actor_user_id || ''; }
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span style={{ opacity: 0.25, marginLeft: 3 }}>↕</span>;
    return <span style={{ marginLeft: 3, color: C.teal1 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  // Scroll-affordance for the events table: show a right-edge fade only while
  // there's more table content to the right that isn't yet visible, so a
  // first-time user has a visual hint the Details column continues off-screen
  // (rather than a table that just appears to end there).
  const tableScrollRef = useRef(null);
  const [showScrollFade, setShowScrollFade] = useState(false);
  const checkTableOverflow = useCallback(() => {
    const el = tableScrollRef.current;
    if (!el) return;
    setShowScrollFade(el.scrollWidth - el.clientWidth - el.scrollLeft > 4);
  }, []);
  useEffect(() => {
    checkTableOverflow();
    window.addEventListener('resize', checkTableOverflow);
    return () => window.removeEventListener('resize', checkTableOverflow);
  }, [checkTableOverflow, sortedEvents.length]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="auditlog">
        <div style={{ display: 'flex', gap: 6 }}>
          <Btn variant="secondary" size="sm" loading={exporting === 'json'} disabled={!!exporting} onClick={handleExportJSON} style={{ fontSize: 10 }}>
            ↓ JSON
          </Btn>
          <Btn variant="secondary" size="sm" loading={exporting === 'csv'} disabled={!!exporting} onClick={handleExportCSV} style={{ fontSize: 10 }}>
            ↓ CSV
          </Btn>
        </div>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>≡</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>Audit Log</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              A permanent history of who did what in your account — useful for tracking down accidental deletions or unauthorized access. Includes API key usage, document operations, configuration changes, and admin actions.
              {total != null && <span style={{ color: C.textSecondary }}> {total.toLocaleString()} total events.</span>}
            </div>
          </div>
        </Card>

        {/* Filters */}
        <Card style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 160 }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px' }}>Search</span>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search events, actors, details…"
                style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '5px 8px', color: C.textPrimary }} />
            </div>
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
              <Btn variant="ghost" size="sm" onClick={() => { setSearch(''); clearFilters(); }} style={{ fontSize: 11, color: C.textMuted }}>Clear</Btn>
            )}
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Events</SectionLabel>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {hasActiveFilters && <Chip color={C.teal2} bg="rgba(90,200,208,0.08)" border="rgba(90,200,208,0.2)">Filtered</Chip>}
              {search.trim() && (
                <Chip color={C.teal2} bg="rgba(90,200,208,0.08)" border="rgba(90,200,208,0.2)">{sortedEvents.length} match{sortedEvents.length !== 1 ? 'es' : ''}</Chip>
              )}
              {total != null && !search.trim() && (
                <Chip color={C.textMuted} bg="transparent" border={C.border}>{total.toLocaleString()} events</Chip>
              )}
            </div>
          </div>

          {loading && events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : sortedEvents.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
              {hasActiveFilters ? 'No events match the current filters.' : 'No audit events yet.'}
            </div>
          ) : (
            <>
              <div style={{ position: 'relative' }}>
              <div ref={tableScrollRef} onScroll={checkTableOverflow} style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {[
                      { label: 'Time', key: 'created_at' },
                      { label: 'Action', key: 'event_type' },
                      { label: 'Resource', key: null },
                      { label: 'Actor', key: 'actor' },
                      { label: 'Details', key: null },
                    ].map(({ label: h, key }) => (
                      <th key={h} scope="col" onClick={key ? () => handleSort(key) : undefined}
                        style={{
                          fontSize: 9, fontWeight: 700, color: sortKey === key ? C.teal1 : C.textMuted,
                          padding: '7px 14px', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px',
                          cursor: key ? 'pointer' : 'default', userSelect: 'none',
                        }}>
                        {h}{key && <SortIcon col={key} />}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sortedEvents.map((ev, i) => (
                    <tr key={ev.id || i} style={{ borderBottom: i < sortedEvents.length - 1 ? `1px solid ${C.border}` : 'none' }}>
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
                      <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textDim, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ev.details
                          ? Object.entries(ev.details).map(([k, v]) => `${k}: ${String(v).slice(0, 40)}`).join(' · ')
                          : (ev.ip_address || ev.metadata?.ip || ev.context || '—')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              {showScrollFade && (
                <div aria-hidden="true" style={{
                  position: 'absolute', top: 0, right: 0, bottom: 0, width: 28,
                  background: `linear-gradient(90deg, transparent, ${C.surface})`,
                  pointerEvents: 'none',
                }} />
              )}
              </div>
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
