import { C, mono } from '../../constants/tokens.js';
import { _errMsg } from '../../utils/viewer.js';
import { useToast } from '../../contexts/toast.jsx';
import { label, SectionLabel, Chip, Btn, Card, RiskBadge } from '../atoms.jsx';
const { useState, useCallback, useEffect } = React;

export function AccessLog({ docId }) {
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchEvents = useCallback(() => {
    if (!docId) { setLoading(false); return; }
    setLoading(true);
    window.SecureDocAPI.getEvents(docId, null, 50)
      .then(data => setEvents(data.events || []))
      .catch(e => toast(_errMsg(e, 'Failed to load events'), 'error'))
      .finally(() => setLoading(false));
  }, [docId]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  return (
    <Card noPad>
      <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <SectionLabel>Access Log — Last 50 Events</SectionLabel>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Chip color={C.textMuted} bg="transparent" border={C.border}>{events.length} events</Chip>
          <Btn variant="ghost" size="sm" onClick={fetchEvents} style={{ fontSize: 11 }}>⟳ Refresh</Btn>
        </div>
      </div>
      {loading ? <div style={{ padding: '24px', color: C.textMuted, fontSize: 13 }}>Loading…</div> : events.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: C.textMuted, fontSize: 13 }}>No events yet</div> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: `1px solid ${C.border}` }}>
            {['Time', 'Email', 'Session', 'Event', 'Page', 'Risk'].map(h => (
              <th key={h} style={{ ...label(9), padding: '9px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>{events.map((e, i) => {
            const isBlocked = ['print_attempt', 'copy_attempt', 'right_click_attempt', 'download_attempt'].includes(e.event_type);
            return (
              <tr key={e.id || i} style={{ borderBottom: i === events.length - 1 ? 'none' : `1px solid ${C.border}`, background: isBlocked ? 'rgba(224,90,69,0.04)' : 'transparent' }}>
                <td style={{ ...mono, padding: '10px 14px', fontSize: 9, color: C.textMuted }}>{e.created_at?.slice(0, 16) || '—'}</td>
                <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textSecondary }}>{e.viewer_email || '—'}</td>
                <td style={{ ...mono, padding: '10px 14px', fontSize: 9, color: C.textMuted }}>{e.session_id?.slice(0, 8) || '—'}</td>
                <td style={{ padding: '10px 14px' }}><span style={{ fontSize: 10, fontWeight: 600, color: isBlocked ? C.error : C.success }}>{isBlocked ? '✕ ' : ''}{e.event_type.replace(/_/g, ' ')}</span></td>
                <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textMuted }}>{e.page_number || '—'}</td>
                <td style={{ padding: '10px 14px' }}><RiskBadge level={isBlocked ? 'HIGH' : 'LOW'} /></td>
              </tr>
            );
          })}</tbody>
        </table>
      )}
    </Card>
  );
}
