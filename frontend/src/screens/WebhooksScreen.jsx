import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn, Divider, Field } from '../components/atoms.jsx';
const { useState, useEffect, useCallback } = React;

const ALL_EVENTS = ['document.processed', 'link.viewed', 'analytics.completed'];

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function CreateWebhookModal({ onClose, onCreated }) {
  const toast = useToast();
  const [url, setUrl] = useState('');
  const [events, setEvents] = useState([]);
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const toggleEvent = e => setEvents(prev => prev.includes(e) ? prev.filter(x => x !== e) : [...prev, e]);

  const handleCreate = async () => {
    if (!url.trim()) { toast('URL is required', 'error'); return; }
    if (!events.length) { toast('Select at least one event', 'error'); return; }
    setSaving(true);
    try {
      const wh = await window.SecureDocAPI.createWebhook(url.trim(), events, description.trim());
      onCreated(wh);
    } catch (e) { toast(_errMsg(e, 'Failed to create webhook'), 'error'); }
    finally { setSaving(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <Card style={{ width: 480, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <SectionLabel>Register Webhook</SectionLabel>
          <Btn variant="ghost" size="sm" onClick={onClose}>✕</Btn>
        </div>
        <Field label="Endpoint URL">
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://your-server.com/webhook"
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
        </Field>
        <Field label="Description (optional)">
          <input value={description} onChange={e => setDescription(e.target.value)} placeholder="What is this webhook for?"
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
        </Field>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 8 }}>Events to subscribe</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {ALL_EVENTS.map(ev => {
              const active = events.includes(ev);
              return (
                <label key={ev} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input type="checkbox" checked={active} onChange={() => toggleEvent(ev)} />
                  <span style={{ ...mono, fontSize: 11, color: active ? C.teal1 : C.textSecondary }}>{ev}</span>
                </label>
              );
            })}
          </div>
        </div>
        <div style={{ fontSize: 10, color: C.textMuted, lineHeight: 1.6 }}>
          A signing secret is generated at creation and shown once. Use it to verify HMAC-SHA256 signatures on incoming payloads.
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={handleCreate} disabled={saving}>
            {saving ? 'Creating…' : 'Register webhook'}
          </Btn>
        </div>
      </Card>
    </div>
  );
}

function SecretReveal({ webhook, onDismiss }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(webhook.secret).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
    toast('Secret copied', 'success');
  };
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <Card style={{ width: 520, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <SectionLabel style={{ color: C.success }}>✓ Webhook registered</SectionLabel>
        <div style={{ fontSize: 11, color: C.warning, lineHeight: 1.6 }}>Copy your signing secret now — it will not be shown again.</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: C.surface2, borderRadius: 7, padding: '10px 12px', border: `1px solid ${C.border}` }}>
          <code style={{ ...mono, fontSize: 11, color: C.teal1, flex: 1, wordBreak: 'break-all' }}>{webhook.secret}</code>
          <Btn variant="ghost" size="sm" onClick={handleCopy}>{copied ? '✓' : '⧉'}</Btn>
        </div>
        <div style={{ fontSize: 10, color: C.textMuted }}>
          Verify payloads: <code style={mono}>HMAC-SHA256(secret, raw_body)</code>. Header: <code style={mono}>X-SecureDoc-Signature</code>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Btn variant="primary" size="sm" onClick={onDismiss}>Done</Btn>
        </div>
      </Card>
    </div>
  );
}

function DeliveryPanel({ webhook, onClose }) {
  const toast = useToast();
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    window.SecureDocAPI.getWebhookDeliveries(webhook.id)
      .then(d => setDeliveries(d?.deliveries || []))
      .catch(e => toast(_errMsg(e, 'Failed to load deliveries'), 'error'))
      .finally(() => setLoading(false));
  }, [webhook.id]);

  const statusColor = s => ({ success: C.success, failed: C.error, pending: C.warning, skipped: C.textMuted }[s] || C.textMuted);

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <Card style={{ width: 600, maxHeight: '80vh', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <SectionLabel>Delivery History</SectionLabel>
            <div style={{ ...mono, fontSize: 10, color: C.textMuted, marginTop: 2 }}>{webhook.url}</div>
          </div>
          <Btn variant="ghost" size="sm" onClick={onClose}>✕</Btn>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : deliveries.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>No deliveries yet. Events will appear here when fired.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['Event', 'Status', 'HTTP', 'Attempts', 'Sent'].map(h => (
                    <th key={h} style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, padding: '7px 14px', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deliveries.map((d, i) => (
                  <tr key={d.id} style={{ borderBottom: i < deliveries.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                    <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textSecondary }}>{d.event_type}</td>
                    <td style={{ padding: '9px 14px' }}>
                      <span style={{ fontSize: 9, fontWeight: 700, color: statusColor(d.status), textTransform: 'uppercase' }}>{d.status}</span>
                    </td>
                    <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: d.response_status >= 200 && d.response_status < 300 ? C.success : C.error }}>{d.response_status || '—'}</td>
                    <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textMuted }}>{d.attempts}</td>
                    <td style={{ ...mono, padding: '9px 14px', fontSize: 10, color: C.textMuted }}>
                      {d.last_attempt_at ? new Date(d.last_attempt_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}

export function WebhooksScreen() {
  const toast = useToast();
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newWebhook, setNewWebhook] = useState(null);
  const [deliveryWebhook, setDeliveryWebhook] = useState(null);
  const [testing, setTesting] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [toggling, setToggling] = useState(null);

  const fetchWebhooks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await window.SecureDocAPI.listWebhooks();
      setWebhooks(data?.webhooks || []);
    } catch (e) { toast(_errMsg(e, 'Failed to load webhooks'), 'error'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchWebhooks(); }, [fetchWebhooks]);

  const handleCreated = (wh) => { setShowCreate(false); setNewWebhook(wh); fetchWebhooks(); };

  const handleToggle = async (wh) => {
    setToggling(wh.id);
    try {
      await window.SecureDocAPI.updateWebhook(wh.id, { is_active: !wh.is_active });
      toast(wh.is_active ? 'Webhook paused' : 'Webhook resumed', 'success');
      fetchWebhooks();
    } catch (e) { toast(_errMsg(e, 'Failed to update webhook'), 'error'); }
    finally { setToggling(null); }
  };

  const handleTest = async (wh) => {
    setTesting(wh.id);
    try {
      await window.SecureDocAPI.testWebhook(wh.id);
      toast('Test ping sent — check delivery history', 'success');
    } catch (e) { toast(_errMsg(e, 'Test ping failed'), 'error'); }
    finally { setTesting(null); }
  };

  const handleDelete = async (wh) => {
    setDeleting(wh.id);
    try {
      await window.SecureDocAPI.deleteWebhook(wh.id);
      toast('Webhook deleted', 'success');
      setWebhooks(prev => prev.filter(w => w.id !== wh.id));
    } catch (e) { toast(_errMsg(e, 'Failed to delete webhook'), 'error'); }
    finally { setDeleting(null); }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="webhooks">
        <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ Register Webhook</Btn>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>⇌</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>Webhooks</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              SecureDoc posts signed JSON payloads to your endpoints when events occur. Payloads are signed with HMAC-SHA256 using your webhook secret. Events: <code style={mono}>document.processed</code>, <code style={mono}>link.viewed</code>, <code style={mono}>analytics.completed</code>.
            </div>
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Registered Endpoints</SectionLabel>
            <Chip color={C.textMuted} bg="transparent" border={C.border}>{webhooks.length} / 20</Chip>
          </div>

          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : webhooks.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
              No webhooks registered yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {webhooks.map((wh, i) => (
                <div key={wh.id} style={{ padding: '14px 16px', borderBottom: i < webhooks.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{
                          fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase', letterSpacing: '.5px',
                          background: wh.is_active ? 'rgba(52,199,89,0.12)' : 'rgba(100,100,120,0.18)',
                          color: wh.is_active ? '#34c759' : '#888',
                        }}>{wh.is_active ? 'Active' : 'Paused'}</span>
                        {wh.description && <span style={{ fontSize: 11, color: C.textSecondary }}>{wh.description}</span>}
                        <span style={{ ...mono, fontSize: 9, color: C.textDim }}>Created {fmtDate(wh.created_at)}</span>
                      </div>
                      <div style={{ ...mono, fontSize: 11, color: C.teal1, marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{wh.url}</div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {(wh.events || []).map(ev => (
                          <span key={ev} style={{ ...mono, fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'rgba(90,200,208,0.08)', color: C.teal2 }}>{ev}</span>
                        ))}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <Btn variant="ghost" size="sm" onClick={() => setDeliveryWebhook(wh)} style={{ fontSize: 10 }}>History</Btn>
                      <Btn variant="ghost" size="sm" onClick={() => handleTest(wh)} disabled={testing === wh.id} style={{ fontSize: 10 }}>
                        {testing === wh.id ? '…' : 'Test'}
                      </Btn>
                      <Btn variant="ghost" size="sm" onClick={() => handleToggle(wh)} disabled={toggling === wh.id} style={{ fontSize: 10 }}>
                        {toggling === wh.id ? '…' : wh.is_active ? 'Pause' : 'Resume'}
                      </Btn>
                      <Btn variant="ghost" size="sm" onClick={() => handleDelete(wh)} disabled={deleting === wh.id} style={{ fontSize: 10, color: C.error }}>
                        {deleting === wh.id ? '…' : 'Delete'}
                      </Btn>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {showCreate && <CreateWebhookModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />}
      {newWebhook && <SecretReveal webhook={newWebhook} onDismiss={() => setNewWebhook(null)} />}
      {deliveryWebhook && <DeliveryPanel webhook={deliveryWebhook} onClose={() => setDeliveryWebhook(null)} />}
    </div>
  );
}
