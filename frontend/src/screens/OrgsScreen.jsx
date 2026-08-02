import { C, mono } from '../constants/tokens.js';
import { _errMsg, fmtDate } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { Card, Header, SectionLabel, Chip, Btn, Field, Modal } from '../components/atoms.jsx';
const { useState, useEffect, useCallback } = React;

function CreateOrgModal({ onClose, onCreated }) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) { toast('Name is required.', 'error'); return; }
    setSaving(true);
    try {
      const org = await window.SecureDocAPI.createOrg(name.trim());
      onCreated(org);
    } catch (e) { toast(_errMsg(e, 'Failed to create organization'), 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title="Create Organization" width={420}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Field label="Organization name">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Acme Corp"
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
        </Field>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={handleCreate} disabled={saving}>
            {saving ? 'Creating…' : 'Create'}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

function RenameOrgModal({ org, onClose, onRenamed }) {
  const toast = useToast();
  const [name, setName] = useState(org.name || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) { toast('Name is required.', 'error'); return; }
    setSaving(true);
    try {
      await window.SecureDocAPI.updateOrg(org.id, { name: name.trim() });
      onRenamed({ ...org, name: name.trim() });
    } catch (e) { toast(_errMsg(e, 'Failed to rename organization'), 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title="Rename Organization" width={420}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Field label="New name">
          <input value={name} onChange={e => setName(e.target.value)}
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
        </Field>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Rename'}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

const ORG_ROLES_LIST = ['viewer', 'editor', 'admin', 'owner'];

function InviteMemberModal({ org, onClose, onInvited }) {
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('viewer');
  const [saving, setSaving] = useState(false);

  const handleInvite = async () => {
    if (!email.trim() || !email.includes('@')) { toast('Enter a valid email address', 'error'); return; }
    setSaving(true);
    try {
      await window.SecureDocAPI.inviteOrgMember(org.id, email.trim().toLowerCase(), role);
      toast(`${email.trim()} added as ${role}`, 'success');
      onInvited();
      onClose();
    } catch (e) { toast(_errMsg(e, 'Failed to invite member'), 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Invite Member to ${org.name}`} width={420}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.5 }}>
          The user must already have a SecureDoc account. They will be added immediately.
        </div>
        <Field label="Email address">
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="colleague@company.com" autoFocus
            onKeyDown={e => e.key === 'Enter' && handleInvite()}
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary, width: '100%' }} />
        </Field>
        <Field label="Role">
          <select value={role} onChange={e => setRole(e.target.value)}
            style={{ fontSize: 12, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '7px 10px', color: C.textPrimary }}>
            <option value="viewer">Viewer — can view shared documents</option>
            <option value="editor">Editor — can upload and manage documents</option>
            <option value="admin">Admin — can manage members and settings</option>
            <option value="owner">Owner — full control including delete</option>
          </select>
        </Field>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" size="sm" loading={saving} onClick={handleInvite}>Add Member</Btn>
        </div>
      </div>
    </Modal>
  );
}

function MembersPanel({ org, onClose }) {
  const toast = useToast();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const [changingRoleId, setChangingRoleId] = useState(null);
  const [removeModal, setRemoveModal] = useState(null);

  const fetchMembers = () => {
    setLoading(true);
    window.SecureDocAPI.listOrgMembers(org.id)
      .then(data => setMembers(data?.members || []))
      .catch(e => toast(_errMsg(e, 'Failed to load members'), 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchMembers(); }, [org.id]);

  const handleChangeRole = async (m, newRole) => {
    setChangingRoleId(m.user_id);
    try {
      await window.SecureDocAPI.updateOrgMemberRole(org.id, m.user_id, newRole);
      toast(`Role updated to ${newRole}`, 'success');
      fetchMembers();
    } catch (e) { toast(_errMsg(e, 'Failed to update role'), 'error'); }
    finally { setChangingRoleId(null); }
  };

  const handleRemove = async (m) => {
    setRemovingId(m.user_id);
    try {
      await window.SecureDocAPI.removeOrgMember(org.id, m.user_id);
      toast('Member removed', 'success');
      setMembers(prev => prev.filter(x => x.user_id !== m.user_id));
    } catch (e) { toast(_errMsg(e, 'Failed to remove member'), 'error'); }
    finally { setRemovingId(null); }
  };

  const ownerCount = members.filter(m => m.role === 'owner').length;

  return (
    <>
    <Modal open onClose={onClose} title={`Members — ${org.name}`} width={600}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: -6 }}>
          <div style={{ fontSize: 11, color: C.textMuted }}>{members.length} member{members.length !== 1 ? 's' : ''}</div>
          <Btn variant="primary" size="sm" onClick={() => setShowInvite(true)} style={{ fontSize: 10 }}>+ Invite Member</Btn>
        </div>
        <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
          {loading ? (
            <div style={{ padding: 28, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : members.length === 0 ? (
            <div style={{ padding: 28, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
              No members yet. Use "+ Invite Member" to add your first team member.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['Member', 'Role', 'Joined', ''].map(h => (
                    <th key={h} scope="col" style={{ fontSize: 9, fontWeight: 700, color: C.textMuted, padding: '7px 14px', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '.5px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {members.map((m, i) => (
                  <tr key={m.user_id || i} style={{ borderBottom: i < members.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                    <td style={{ padding: '10px 14px', fontSize: 12, color: C.textPrimary }}>
                      {m.email || <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{(m.user_id || '').slice(0, 12)}…</span>}
                    </td>
                    <td style={{ padding: '8px 14px' }}>
                      <select
                        value={m.role || 'viewer'}
                        disabled={changingRoleId === m.user_id}
                        onChange={e => handleChangeRole(m, e.target.value)}
                        style={{
                          ...mono, fontSize: 10, padding: '3px 8px', borderRadius: 5,
                          background: m.role === 'owner' ? 'rgba(90,200,208,0.1)' : 'rgba(100,100,120,0.15)',
                          color: m.role === 'owner' ? C.teal1 : C.textSecondary,
                          border: `1px solid ${C.border}`, cursor: 'pointer',
                        }}>
                        {ORG_ROLES_LIST.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textMuted }}>{fmtDate(m.joined_at || m.created_at)}</td>
                    <td style={{ padding: '8px 14px' }}>
                      <Btn variant="ghost" size="sm"
                        disabled={removingId === m.user_id || (m.role === 'owner' && ownerCount <= 1)}
                        onClick={() => setRemoveModal(m)}
                        style={{ fontSize: 10, color: C.error }}>
                        {removingId === m.user_id ? '…' : 'Remove'}
                      </Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Modal>
    {showInvite && <InviteMemberModal org={org} onClose={() => setShowInvite(false)} onInvited={fetchMembers} />}

    <Modal open={!!removeModal} onClose={() => setRemoveModal(null)} title="Remove Member" width={400}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{
          background: C.errorBg, border: `1px solid ${C.errorBdr}`,
          borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
        }}>
          <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
          <strong style={{ color: C.textPrimary }}>{removeModal?.email || 'This member'}</strong> will lose access to this organization and its shared documents immediately.
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Btn variant="secondary" onClick={() => setRemoveModal(null)}>Cancel</Btn>
          <Btn variant="danger" loading={removingId === removeModal?.user_id}
            onClick={() => { handleRemove(removeModal); setRemoveModal(null); }}>
            Remove Member
          </Btn>
        </div>
      </div>
    </Modal>
    </>
  );
}

export function OrgsScreen() {
  const toast = useToast();
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [renameOrg, setRenameOrg] = useState(null);
  const [membersOrg, setMembersOrg] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [deleteOrgModal, setDeleteOrgModal] = useState(null);

  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await window.SecureDocAPI.listOrgs();
      setOrgs(data?.organizations || data?.orgs || []);
    } catch (e) { toast(_errMsg(e, 'Failed to load organizations'), 'error'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchOrgs(); }, [fetchOrgs]);

  const handleCreated = (org) => { setShowCreate(false); fetchOrgs(); };

  const handleRenamed = (updated) => {
    setOrgs(prev => prev.map(o => o.id === updated.id ? updated : o));
    setRenameOrg(null);
    toast('Organization renamed', 'success');
  };

  const handleDelete = async (org) => {
    setDeleting(org.id);
    try {
      await window.SecureDocAPI.deleteOrg(org.id);
      toast(`"${org.name}" deleted`, 'success');
      setOrgs(prev => prev.filter(o => o.id !== org.id));
    } catch (e) { toast(_errMsg(e, 'Failed to delete organization'), 'error'); }
    finally { setDeleting(null); }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="orgs">
        <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ New Organization</Btn>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Card style={{ padding: '12px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ fontSize: 18, lineHeight: 1 }}>◉</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.textSecondary, marginBottom: 4 }}>Organizations</div>
            <div style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.6, maxWidth: 560 }}>
              Group users and share resources across your team. Organization members can collaborate on documents and access shared analytics. Optional — skip this if you're working alone.
            </div>
          </div>
        </Card>

        <Card noPad>
          <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Your Organizations</SectionLabel>
            <Chip color={C.textMuted} bg="transparent" border={C.border}>{orgs.length} org{orgs.length !== 1 ? 's' : ''}</Chip>
          </div>

          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading…</div>
          ) : orgs.length === 0 ? (
            <div style={{ padding: '32px 24px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
              <div style={{ fontSize: 28, color: C.textDim }}>◉</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: C.textSecondary }}>No organizations yet</div>
              <div style={{ fontSize: 12, color: C.textMuted, maxWidth: 320, lineHeight: 1.6 }}>Create an organization to collaborate with your team and share documents securely.</div>
              <Btn variant="primary" size="sm" onClick={() => setShowCreate(true)} style={{ marginTop: 4 }}>+ New Organization</Btn>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {orgs.map((org, i) => (
                <div key={org.id} style={{ padding: '14px 16px', borderBottom: i < orgs.length - 1 ? `1px solid ${C.border}` : 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 3 }}>{org.name}</div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      {org.member_count != null && (
                        <span style={{ fontSize: 10, color: C.textMuted }}>{org.member_count} member{org.member_count !== 1 ? 's' : ''}</span>
                      )}
                      {org.role && (
                        <span style={{ ...mono, fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'rgba(90,200,208,0.08)', color: C.teal2 }}>{org.role}</span>
                      )}
                      <span style={{ ...mono, fontSize: 9, color: C.textDim }}>Created {fmtDate(org.created_at)}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Btn variant="ghost" size="sm" onClick={() => setMembersOrg(org)} style={{ fontSize: 10 }}>Members</Btn>
                    <Btn variant="ghost" size="sm" onClick={() => setRenameOrg(org)} style={{ fontSize: 10 }}>Rename</Btn>
                    <Btn variant="ghost" size="sm" onClick={() => setDeleteOrgModal(org)} disabled={deleting === org.id} style={{ fontSize: 10, color: C.error }}>
                      {deleting === org.id ? '…' : 'Delete'}
                    </Btn>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {showCreate && <CreateOrgModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />}
      {renameOrg && <RenameOrgModal org={renameOrg} onClose={() => setRenameOrg(null)} onRenamed={handleRenamed} />}
      {membersOrg && <MembersPanel org={membersOrg} onClose={() => setMembersOrg(null)} />}

      <Modal open={!!deleteOrgModal} onClose={() => setDeleteOrgModal(null)} title="Delete Organization" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
            Deleting <strong style={{ color: C.textPrimary }}>"{deleteOrgModal?.name}"</strong> will permanently remove the organization and all its settings. Members will lose access.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setDeleteOrgModal(null)}>Cancel</Btn>
            <Btn variant="danger" loading={deleting === deleteOrgModal?.id}
              onClick={() => { handleDelete(deleteOrgModal); setDeleteOrgModal(null); }}>
              Delete Organization
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
