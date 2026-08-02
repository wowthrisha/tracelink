import { C, mono } from '../constants/tokens.js';
import { _errMsg, fmtDate } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn, Field, Modal } from '../components/atoms.jsx';
const { useState, useEffect, useCallback } = React;

const ALL_EVENTS = ['document.processed', 'link.viewed', 'analytics.completed'];

function CreateWebhookModal({ onClose, onCreated }) {
  const toast = useToast();
  const [url, setUrl] = useState('');
  const [events, setEvents] = useState([]);
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const toggleEvent = e => setEvents(prev => prev.includes(e) ? prev.filter(x => x !== e) : [...prev, e]);

  const handleCreate = async () => {
    if (!url.trim()) { toast('URL is required.', 'error'); return; }
    if (!url.trim().startsWith('https://')) { toast('Webhook URL must start with https://', 'error'); return; }
    if (!events.length) { toast('Select at least one event.', 'error'); return; }
    setSaving(true);
    try {
      const wh = await window.SecureDocAPI.createWebhook(url.trim(), events, description.trim());
      onCreated(wh);
    } catch (e) { toast(_errMsg(e, 'Failed to create webhook'), 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title="New Webhook" width={480}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
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
      </div>
    </Modal>
  );
}

function SecretReveal({ webhook, onDismiss }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(webhook.secret)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        toast('Secret copied', 'success');
      })
      .catch(() => toast('Failed to copy secret — copy it manually.', 'error'));
  };
  return (
    <Modal open onClose={onDismiss} title="✓ Webhook registered" width={520}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
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
      </div>
    </Modal>
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
    <Modal open onClose={onClose} title="Delivery History" width={600}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ ...mono, fontSize: 10, color: C.textMuted, marginTop: -6 }}>{webhook.url}</div>
        <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
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
      </div>
    </Modal>
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
  const [deleteWebhookModal, setDeleteWebhookModal] = useState(null);
  const [editWebhookModal, setEditWebhookModal] = useState(null);
  const [editUrl, setEditUrl] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editEvents, setEditEvents] = useState([]);
  const [editSaving, setEditSaving] = useState(false);

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
        <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ New Webhook</Btn>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>⇌</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>Webhooks</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              A webhook lets another app get notified automatically when something happens here — for example, when a document is viewed. SecureDoc posts signed JSON payloads to your endpoints when events occur. Payloads are signed with HMAC-SHA256 using your webhook secret. Events: <code style={mono}>document.processed</code>, <code style={mono}>link.viewed</code>, <code style={mono}>analytics.completed</code>.
            </div>
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Registered Webhooks</SectionLabel>
            <Chip color={C.textMuted} bg="transparent" border={C.border}>{webhooks.length} / 20</Chip>
          </div>

          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : webhooks.length === 0 ? (
            <div style={{ padding: '32px 24px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
              <div style={{ fontSize: 26, color: C.textDim }}>⇌</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: C.textSecondary }}>No webhooks registered yet</div>
              <div style={{ fontSize: 12, color: C.textMuted, maxWidth: 320, lineHeight: 1.6 }}>Register a webhook to receive real-time notifications when documents are viewed, downloaded, or processed.</div>
              <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)} style={{ marginTop: 4 }}>+ New Webhook</Btn>
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
                      <Btn variant="ghost" size="sm" onClick={() => { setEditWebhookModal(wh); setEditUrl(wh.url); setEditDescription(wh.description || ''); setEditEvents(wh.events || []); }} style={{ fontSize: 10 }}>Edit</Btn>
                      <Btn variant="ghost" size="sm" onClick={() => setDeliveryWebhook(wh)} style={{ fontSize: 10 }}>History</Btn>
                      <Btn variant="ghost" size="sm" onClick={() => handleTest(wh)} disabled={testing === wh.id || !wh.is_active} style={{ fontSize: 10 }} title={!wh.is_active ? 'Resume webhook to send test pings' : undefined}>
                        {testing === wh.id ? '…' : 'Test'}
                      </Btn>
                      <Btn variant="ghost" size="sm" onClick={() => handleToggle(wh)} disabled={toggling === wh.id} style={{ fontSize: 10 }}>
                        {toggling === wh.id ? '…' : wh.is_active ? 'Pause' : 'Resume'}
                      </Btn>
                      <Btn variant="ghost" size="sm" onClick={() => setDeleteWebhookModal(wh)} disabled={deleting === wh.id} style={{ fontSize: 10, color: C.error }}>
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

      <Modal open={!!editWebhookModal} onClose={() => setEditWebhookModal(null)} title="Edit Webhook" width={480}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Field label="Endpoint URL">
            <input value={editUrl} onChange={e => setEditUrl(e.target.value)}
              placeholder="https://your-server.com/webhook"
              style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%', fontFamily: "'DM Mono',monospace" }} />
          </Field>
          <Field label="Description (optional)">
            <input value={editDescription} onChange={e => setEditDescription(e.target.value)}
              placeholder="e.g. Production notifications"
              style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
          </Field>
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 8 }}>Events</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {ALL_EVENTS.map(ev => {
                const active = editEvents.includes(ev);
                return (
                  <button key={ev} onClick={() => setEditEvents(prev => prev.includes(ev) ? prev.filter(x => x !== ev) : [...prev, ev])}
                    style={{
                      ...mono, fontSize: 10, padding: '4px 10px', borderRadius: 5,
                      border: `1px solid ${active ? C.teal1 : C.border}`,
                      background: active ? 'rgba(90,200,208,0.12)' : C.surface2,
                      color: active ? C.teal1 : C.textMuted, cursor: 'pointer', transition: 'all .12s',
                    }}>{ev}</button>
                );
              })}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setEditWebhookModal(null)}>Cancel</Btn>
            <Btn variant="primary" loading={editSaving}
              onClick={async () => {
                if (!editUrl.trim()) { toast('URL is required.', 'error'); return; }
                if (!editUrl.trim().startsWith('https://')) { toast('Webhook URL must start with https://', 'error'); return; }
                if (!editEvents.length) { toast('Select at least one event.', 'error'); return; }
                setEditSaving(true);
                try {
                  await window.SecureDocAPI.updateWebhook(editWebhookModal.id, { url: editUrl.trim(), description: editDescription.trim(), events: editEvents });
                  toast('Webhook updated', 'success');
                  setEditWebhookModal(null);
                  fetchWebhooks();
                } catch (e) { toast(_errMsg(e, 'Failed to update webhook'), 'error'); }
                finally { setEditSaving(false); }
              }}>
              Save Changes
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!deleteWebhookModal} onClose={() => setDeleteWebhookModal(null)} title="Delete Webhook" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
            The endpoint <strong style={{ color: C.textPrimary }}>"{deleteWebhookModal?.url}"</strong> will be removed and all delivery history will be permanently deleted.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setDeleteWebhookModal(null)}>Cancel</Btn>
            <Btn variant="danger" loading={deleting === deleteWebhookModal?.id}
              onClick={() => { handleDelete(deleteWebhookModal); setDeleteWebhookModal(null); }}>
              Delete Webhook
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
