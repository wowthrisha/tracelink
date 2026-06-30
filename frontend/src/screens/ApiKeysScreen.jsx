import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn, Divider, Field, Modal } from '../components/atoms.jsx';
const { useState, useEffect, useCallback } = React;

const ALL_SCOPES = [
  'documents:read', 'documents:write',
  'links:read', 'links:write',
  'analytics:read',
  'webhooks:read', 'webhooks:write',
];

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function fmtRelative(iso) {
  if (!iso) return 'Never';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function NewKeyModal({ onClose, onCreated }) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState([]);
  const [saving, setSaving] = useState(false);

  const toggleScope = s => setScopes(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);

  const handleCreate = async () => {
    if (!name.trim()) { toast('Name is required.', 'error'); return; }
    if (!scopes.length) { toast('Select at least one scope.', 'error'); return; }
    setSaving(true);
    try {
      const key = await window.SecureDocAPI.createApiKey(name.trim(), scopes);
      onCreated(key);
    } catch (e) { toast(_errMsg(e, 'Failed to create key'), 'error'); }
    finally { setSaving(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <Card style={{ width: 460, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <SectionLabel>Create API Key</SectionLabel>
          <Btn variant="ghost" size="sm" onClick={onClose} aria-label="Close">✕</Btn>
        </div>
        <Field label="Key name">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Production integration"
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
        </Field>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 8 }}>Scopes</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {ALL_SCOPES.map(s => {
              const active = scopes.includes(s);
              return (
                <button key={s} onClick={() => toggleScope(s)} style={{
                  ...mono, fontSize: 10, padding: '4px 10px', borderRadius: 5, border: `1px solid ${active ? C.teal1 : C.border}`,
                  background: active ? 'rgba(90,200,208,0.12)' : C.surface2, color: active ? C.teal1 : C.textMuted,
                  cursor: 'pointer', transition: 'all .12s',
                }}>{s}</button>
              );
            })}
          </div>
        </div>
        <div style={{ fontSize: 10, color: C.textMuted, lineHeight: 1.6 }}>
          The full key is shown only once after creation. Store it securely.
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={handleCreate} disabled={saving}>
            {saving ? 'Creating…' : 'Create key'}
          </Btn>
        </div>
      </Card>
    </div>
  );
}

function NewKeyReveal({ keyData, onDismiss }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(keyData.key).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
    toast('Key copied to clipboard', 'success');
  };
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <Card style={{ width: 520, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <SectionLabel style={{ color: C.success }}>✓ API key created</SectionLabel>
        <div style={{ fontSize: 11, color: C.warning, lineHeight: 1.6 }}>
          Copy this key now. It will not be shown again.
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: C.surface2, borderRadius: 7, padding: '10px 12px', border: `1px solid ${C.border}` }}>
          <code style={{ ...mono, fontSize: 11, color: C.teal1, flex: 1, wordBreak: 'break-all' }}>{keyData.key}</code>
          <Btn variant="ghost" size="sm" onClick={handleCopy}>{copied ? '✓' : '⧉'}</Btn>
        </div>
        <div style={{ fontSize: 10, color: C.textMuted }}>
          Scopes: {(keyData.scopes || []).join(', ') || 'none'}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Btn variant="primary" size="sm" onClick={onDismiss}>Done</Btn>
        </div>
      </Card>
    </div>
  );
}

export function ApiKeysScreen() {
  const toast = useToast();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [revoking, setRevoking] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [revokeKeyModal, setRevokeKeyModal] = useState(null);
  const [deleteKeyModal, setDeleteKeyModal] = useState(null);
  const [editKeyModal, setEditKeyModal] = useState(null);
  const [editName, setEditName] = useState('');
  const [editScopes, setEditScopes] = useState([]);
  const [editSaving, setEditSaving] = useState(false);

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    try {
      const data = await window.SecureDocAPI.listApiKeys();
      setKeys(data?.api_keys || []);
    } catch (e) { toast(_errMsg(e, 'Failed to load API keys'), 'error'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  const handleCreated = (key) => {
    setShowCreate(false);
    setNewKey(key);
    fetchKeys();
  };

  const handleRevoke = async (key) => {
    setRevoking(key.id);
    try {
      await window.SecureDocAPI.revokeApiKey(key.id);
      toast(`"${key.name}" revoked`, 'success');
      fetchKeys();
    } catch (e) { toast(_errMsg(e, 'Failed to revoke key'), 'error'); }
    finally { setRevoking(null); }
  };

  const handleDelete = async (key) => {
    setDeleting(key.id);
    try {
      await window.SecureDocAPI.deleteApiKey(key.id);
      toast(`"${key.name}" deleted`, 'success');
      setKeys(prev => prev.filter(k => k.id !== key.id));
    } catch (e) { toast(_errMsg(e, 'Failed to delete key'), 'error'); }
    finally { setDeleting(null); }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="apikeys">
        <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ New API Key</Btn>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* Info card */}
        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>◈</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>API Keys</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              Use API keys to authenticate programmatic access. Keys use Bearer token auth
              (<code style={mono}>Authorization: Bearer sd_...</code>). Each key has scopes that
              limit what it can do. Full keys are shown once at creation.
            </div>
          </div>
        </Card>

        {/* Key list */}
        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Your Keys</SectionLabel>
            <Chip color={C.textMuted} bg="transparent" border={C.border}>{keys.length} key{keys.length !== 1 ? 's' : ''}</Chip>
          </div>

          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : keys.length === 0 ? (
            <div style={{ padding: '32px 24px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
              <div style={{ fontSize: 26, color: C.textDim }}>⌗</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: C.textSecondary }}>No API keys yet</div>
              <div style={{ fontSize: 12, color: C.textMuted, maxWidth: 320, lineHeight: 1.6 }}>Create an API key to enable programmatic access to your documents and analytics.</div>
              <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)} style={{ marginTop: 4 }}>+ New API Key</Btn>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['Name', 'Prefix', 'Scopes', 'Last used', 'Created', 'Status', ''].map(h => (
                    <th key={h} scope="col" style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, padding: '7px 14px', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keys.map((k, i) => (
                  <tr key={k.id} style={{ borderBottom: i < keys.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                    <td style={{ padding: '10px 14px', fontSize: 12, color: C.textPrimary, fontWeight: 500 }}>{k.name}</td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.teal1 }}>{k.key_prefix}…</td>
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {(k.scopes || []).map(s => (
                          <span key={s} style={{ ...mono, fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'rgba(90,200,208,0.08)', color: C.teal2 }}>{s}</span>
                        ))}
                        {!(k.scopes || []).length && <span style={{ fontSize: 10, color: C.textDim }}>—</span>}
                      </div>
                    </td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textMuted }}>{fmtRelative(k.last_used_at)}</td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textMuted }}>{fmtDate(k.created_at)}</td>
                    <td style={{ padding: '10px 14px' }}>
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 4, textTransform: 'uppercase', letterSpacing: '.5px',
                        background: k.is_active ? 'rgba(52,199,89,0.12)' : 'rgba(100,100,120,0.18)',
                        color: k.is_active ? '#34c759' : '#888',
                      }}>{k.is_active ? 'Active' : 'Revoked'}</span>
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <Btn variant="ghost" size="sm" onClick={() => { setEditKeyModal(k); setEditName(k.name); setEditScopes(k.scopes || []); }}
                          style={{ fontSize: 10 }}>Edit</Btn>
                        {k.is_active && (
                          <Btn variant="ghost" size="sm" disabled={revoking === k.id} onClick={() => setRevokeKeyModal(k)}
                            style={{ fontSize: 10, color: C.warning }}>
                            {revoking === k.id ? '…' : 'Revoke'}
                          </Btn>
                        )}
                        <Btn variant="ghost" size="sm" disabled={deleting === k.id} onClick={() => setDeleteKeyModal(k)}
                          style={{ fontSize: 10, color: C.error }}>
                          {deleting === k.id ? '…' : 'Delete'}
                        </Btn>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {showCreate && <NewKeyModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />}
      {newKey && <NewKeyReveal keyData={newKey} onDismiss={() => setNewKey(null)} />}

      <Modal open={!!editKeyModal} onClose={() => setEditKeyModal(null)} title={`Edit API Key — ${editKeyModal?.name || ''}`} width={460}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Field label="Key name">
            <input value={editName} onChange={e => setEditName(e.target.value)}
              placeholder="e.g. Production integration"
              style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
          </Field>
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 8 }}>Scopes</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {ALL_SCOPES.map(s => {
                const active = editScopes.includes(s);
                return (
                  <button key={s} onClick={() => setEditScopes(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])}
                    style={{
                      ...mono, fontSize: 10, padding: '4px 10px', borderRadius: 5,
                      border: `1px solid ${active ? C.teal1 : C.border}`,
                      background: active ? 'rgba(90,200,208,0.12)' : C.surface2,
                      color: active ? C.teal1 : C.textMuted, cursor: 'pointer', transition: 'all .12s',
                    }}>{s}</button>
                );
              })}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setEditKeyModal(null)}>Cancel</Btn>
            <Btn variant="primary" loading={editSaving}
              onClick={async () => {
                if (!editName.trim()) { toast('Name is required.', 'error'); return; }
                if (!editScopes.length) { toast('Select at least one scope.', 'error'); return; }
                setEditSaving(true);
                try {
                  await window.SecureDocAPI.updateApiKey(editKeyModal.id, { name: editName.trim(), scopes: editScopes });
                  toast(`"${editName.trim()}" updated`, 'success');
                  setEditKeyModal(null);
                  fetchKeys();
                } catch (e) { toast(_errMsg(e, 'Failed to update key'), 'error'); }
                finally { setEditSaving(false); }
              }}>
              Save Changes
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!revokeKeyModal} onClose={() => setRevokeKeyModal(null)} title="Revoke API Key" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: 'rgba(245,158,11,0.08)', border: `1px solid rgba(245,158,11,0.3)`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.warning }}>⚠ This will immediately invalidate the key.</strong><br />
            Any integrations using <strong style={{ color: C.textPrimary }}>"{revokeKeyModal?.name}"</strong> will stop working until updated with a new key.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setRevokeKeyModal(null)}>Cancel</Btn>
            <Btn variant="danger" loading={revoking === revokeKeyModal?.id}
              onClick={() => { handleRevoke(revokeKeyModal); setRevokeKeyModal(null); }}>
              Revoke Key
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!deleteKeyModal} onClose={() => setDeleteKeyModal(null)} title="Delete API Key" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
            <strong style={{ color: C.textPrimary }}>"{deleteKeyModal?.name}"</strong> will be permanently deleted along with its delivery history.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setDeleteKeyModal(null)}>Cancel</Btn>
            <Btn variant="danger" loading={deleting === deleteKeyModal?.id}
              onClick={() => { handleDelete(deleteKeyModal); setDeleteKeyModal(null); }}>
              Delete Key
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
