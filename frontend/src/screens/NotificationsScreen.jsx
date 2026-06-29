import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn } from '../components/atoms.jsx';
const { useState, useEffect, useCallback, useRef } = React;

const POLL_INTERVAL = 30000;
const LS_LAST_SEEN = 'securedoc_notif_last_seen';

function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function eventLabel(ev) {
  const type = ev.event_type || ev.type || '';
  switch (type) {
    case 'opened':               return 'Viewer opened';
    case 'page_viewed':          return 'Page viewed';
    case 'completed':            return 'Document completed';
    case 'download_attempt':     return 'Download attempted';
    case 'printed':              return 'Document printed';
    case 'print_attempt':        return 'Print attempted';
    case 'copy_attempt':         return 'Copy attempted';
    case 'right_click_attempt':  return 'Right-click attempted';
    case 'password_wrong':       return 'Wrong password';
    case 'access_denied':        return 'Access denied';
    case 'ip_blocked':           return 'IP blocked';
    case 'expired':              return 'Link expired';
    case 'revoked':              return 'Link revoked';
    case 'max_views_reached':    return 'Max views reached';
    case 'session_limit_reached':return 'Session limit reached';
    case 'link_view':
    case 'link.viewed':          return 'Link viewed';
    case 'document_view':        return 'Document viewed';
    case 'download':             return 'Document downloaded';
    case 'analytics.completed':  return 'Analytics ready';
    case 'document.processed':   return 'Document processed';
    case 'document.deleted':     return 'Document deleted';
    case 'link.created':         return 'Link created';
    case 'link.revoked':         return 'Link revoked';
    case 'link.updated':         return 'Link updated';
    case 'link.deleted':         return 'Link deleted';
    case 'api_key.created':      return 'API key created';
    case 'api_key.revoked':      return 'API key revoked';
    case 'api_key.deleted':      return 'API key deleted';
    default:                     return type || 'Event';
  }
}

function eventDetail(ev) {
  const parts = [];
  if (ev.document_title) parts.push(ev.document_title);
  if (ev.viewer_email) parts.push(`by ${ev.viewer_email}`);
  if (ev.ip_address) parts.push(`from ${ev.ip_address}`);
  if (ev.country) parts.push(ev.country);
  return parts.join(' · ') || ev.details || '';
}

export function NotificationsScreen() {
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastSeen, setLastSeen] = useState(() => localStorage.getItem(LS_LAST_SEEN) || '');
  const [unread, setUnread] = useState(0);
  const intervalRef = useRef(null);

  const fetchEvents = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await window.SecureDocAPI.getEvents(null, null, 50);
      const rows = data?.events || data?.items || [];
      setEvents(rows);
      const seen = localStorage.getItem(LS_LAST_SEEN) || '';
      const newCount = seen ? rows.filter(ev => {
        const ts = ev.created_at || ev.timestamp || '';
        return ts > seen;
      }).length : 0;
      setUnread(newCount);
    } catch (e) {
      if (!silent) toast(_errMsg(e, 'Failed to load activity'), 'error');
    }
    finally { if (!silent) setLoading(false); }
  }, []);

  useEffect(() => {
    fetchEvents(false);
    intervalRef.current = setInterval(() => fetchEvents(true), POLL_INTERVAL);
    return () => clearInterval(intervalRef.current);
  }, [fetchEvents]);

  const markAllRead = () => {
    const now = new Date().toISOString();
    localStorage.setItem(LS_LAST_SEEN, now);
    setLastSeen(now);
    setUnread(0);
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="notifications">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {unread > 0 && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: '3px 7px', borderRadius: 10, background: C.teal1, color: '#000' }}>
              {unread} new
            </span>
          )}
          {unread > 0 && (
            <Btn variant="ghost" size="sm" onClick={markAllRead} style={{ fontSize: 10 }}>Mark all read</Btn>
          )}
        </div>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>◎</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>Activity Feed</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              Recent activity across your documents — views, downloads, link accesses, and processing events. Refreshes every 30 seconds.
            </div>
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Recent Activity</SectionLabel>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Btn variant="ghost" size="sm" onClick={() => fetchEvents(false)} style={{ fontSize: 10 }}>↻ Refresh</Btn>
              <Chip color={C.textMuted} bg="transparent" border={C.border}>{events.length} events</Chip>
            </div>
          </div>

          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
              No activity yet. Activity will appear here as your documents are accessed.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {events.map((ev, i) => {
                const ts = ev.created_at || ev.timestamp || '';
                const isNew = lastSeen && ts > lastSeen;
                return (
                  <div key={ev.id || i} style={{
                    padding: '12px 16px',
                    borderBottom: i < events.length - 1 ? `1px solid ${C.border}` : 'none',
                    display: 'flex', alignItems: 'flex-start', gap: 12,
                    background: isNew ? 'rgba(90,200,208,0.04)' : 'transparent',
                  }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: '50%', flexShrink: 0, marginTop: 5,
                      background: isNew ? C.teal1 : C.border,
                    }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{eventLabel(ev)}</span>
                        {isNew && <span style={{ fontSize: 8, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: 'rgba(90,200,208,0.15)', color: C.teal1, textTransform: 'uppercase' }}>New</span>}
                      </div>
                      {eventDetail(ev) && (
                        <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 2 }}>{eventDetail(ev)}</div>
                      )}
                      <div style={{ ...mono, fontSize: 10, color: C.textDim }}>{fmtTime(ts)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
