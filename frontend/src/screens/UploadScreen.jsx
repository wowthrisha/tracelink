import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { label, SectionLabel, StatusDot, Chip, Btn, Card, Modal, Field, Header } from '../components/atoms.jsx';
import { StatCard } from '../components/upload/StatCard.jsx';
import { DocRow } from '../components/upload/DocRow.jsx';
import { QuickShareModal } from '../components/upload/QuickShareModal.jsx';
import { UploadDropZone } from '../components/upload/UploadDropZone.jsx';
import { UploadMetadataPanel } from '../components/upload/UploadMetadataPanel.jsx';
import { UploadProgressPanel } from '../components/upload/UploadProgressPanel.jsx';

const { useState, useEffect, useRef, useCallback } = React;

const MAX_POLL_ATTEMPTS = 150; // 150 × 2s = 5 minutes before giving up

function _detectFileType(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.pdf')) return 'pdf';
  if (name.endsWith('.docx')) return 'docx';
  if (name.endsWith('.doc')) return 'doc';
  if (name.endsWith('.txt')) return 'txt';
  if (name.endsWith('.md')) return 'md';
  if (name.endsWith('.log')) return 'log';
  return null;
}

function _isDocType(ft) { return ft === 'pdf' || ft === 'docx' || ft === 'doc'; }

export function UploadScreen({ onViewDoc, onAccessDoc }) {
  const toast = useToast();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadDone, setUploadDone] = useState(false);
  const [uploadedDoc, setUploadedDoc] = useState(null);
  const [search, setSearch] = useState('');
  const [deleteModal, setDeleteModal] = useState(null);
  const [docs, setDocs] = useState([]);
  const [overview, setOverview] = useState(null);
  const [docsLoading, setDocsLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [groups, setGroups] = useState([]);
  const [activeGroupFilter, setActiveGroupFilter] = useState(null);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [groupModal, setGroupModal] = useState(null); // null | 'new' | {id,name,color,description}
  const [groupForm, setGroupForm] = useState({ name: '', color: '#6366f1', description: '' });
  const [groupSaving, setGroupSaving] = useState(false);
  const [retentionPolicy, setRetentionPolicy] = useState('never');
  const [quickShareDoc, setQuickShareDoc] = useState(null);
  const fileRef = useRef();
  const pollRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    try {
      const data = await window.SecureDocAPI.getDocuments();
      setDocs(data.documents || []);
      const ov = await window.SecureDocAPI.getAnalyticsOverview();
      setOverview(ov);
    } catch (e) { toast(_errMsg(e, 'Failed to load documents'), 'error'); }
    finally { setDocsLoading(false); }
  }, []);

  const fetchGroups = useCallback(async () => {
    try {
      const data = await window.SecureDocAPI.getGroups();
      setGroups(data.groups || []);
    } catch (e) { /* non-critical */ }
  }, []);


  useEffect(() => { fetchDocs(); fetchGroups(); }, []);

  const startPoll = useCallback((docId, fileType = 'pdf') => {
    clearInterval(pollRef.current);
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts += 1;
      if (attempts > MAX_POLL_ATTEMPTS) {
        clearInterval(pollRef.current);
        setUploading(false);
        toast('Processing is taking longer than expected. Check back later.', 'error');
        return;
      }
      try {
        const s = await window.SecureDocAPI.pollDocumentStatus(docId);
        if (s.status === 'ready' || s.status === 'error') {
          clearInterval(pollRef.current);
          setUploading(false);
          await fetchDocs();
          if (s.status === 'ready') {
            setUploadDone(true);
            const unit = (fileType === 'pdf' || fileType === 'docx' || fileType === 'doc') ? 'pages' : 'chunks';
            toast(`Upload complete — ${s.page_count} ${unit} ready`, 'success');
          } else toast(`Processing error: ${s.error_message || 'unknown'}`, 'error');
        }
      } catch { }
    }, 2000);
  }, [fetchDocs]);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const simulate = async (file) => {
    if (!file) return;
    const fileType = _detectFileType(file);
    if (!fileType) {
      toast('Supported formats: PDF, DOCX, DOC, TXT, MD, LOG', 'error'); return;
    }
    const sizeLimit = _isDocType(fileType) ? 100 * 1024 * 1024 : 10 * 1024 * 1024;
    const sizeLabelMB = _isDocType(fileType) ? 100 : 10;
    if (file.size > sizeLimit) {
      toast(`File exceeds ${sizeLabelMB} MB limit.`, 'error'); return;
    }
    setUploading(true); setProgress(0); setUploadDone(false);
    try {
      const res = await window.SecureDocAPI.uploadDocument(file, p => setProgress(p), selectedGroupId || null, retentionPolicy);
      setUploadedDoc(res);
      toast(_isDocType(fileType) ? 'Upload complete — converting pages to images' : 'Upload complete — preparing text document', 'info');
      startPoll(res.id, fileType);
      await fetchDocs();
    } catch (e) {
      setUploading(false);
      const msg = (e && (e.detail || e.message)) || 'Upload failed';
      toast(msg, 'error');
    }
  };

  const handleSaveGroup = async () => {
    if (!groupForm.name.trim()) { toast('Group name is required', 'error'); return; }
    setGroupSaving(true);
    try {
      if (groupModal === 'new') {
        await window.SecureDocAPI.createGroup(groupForm);
        toast(`Group "${groupForm.name}" created`, 'success');
      } else {
        await window.SecureDocAPI.updateGroup(groupModal.id, groupForm);
        toast(`Group "${groupForm.name}" updated`, 'success');
      }
      await fetchGroups();
      setGroupModal(null);
    } catch (e) {
      toast(_errMsg(e, 'Failed to save group'), 'error');
    } finally { setGroupSaving(false); }
  };

  const handleDeleteGroup = async (g) => {
    try {
      await window.SecureDocAPI.deleteGroup(g.id);
      toast(`Group "${g.name}" deleted`, 'success');
      if (activeGroupFilter === g.id) setActiveGroupFilter(null);
      await fetchGroups(); await fetchDocs();
    } catch (e) { toast(_errMsg(e, 'Failed to delete group'), 'error'); }
  };

  const handleAssignGroup = async (doc, gid) => {
    try {
      if (gid) {
        await window.SecureDocAPI.assignDocumentsToGroup(gid, [doc.id]);
      } else if (doc.group_id) {
        await window.SecureDocAPI.removeDocumentFromGroup(doc.group_id, doc.id);
      }
      await fetchDocs(); await fetchGroups();
      toast(gid ? 'Document added to group' : 'Removed from group', 'success');
    } catch (e) { toast(_errMsg(e, 'Failed to assign group'), 'error'); }
  };

  const handleDelete = async (doc) => {
    setDeleting(true);
    try {
      await window.SecureDocAPI.deleteDocument(doc.id);
      setDeleteModal(null);
      await fetchDocs();
      toast('Document deleted.', 'success');
    } catch (e) { toast(_errMsg(e, 'Delete failed'), 'error'); }
    finally { setDeleting(false); }
  };

  const handleReprocess = async (doc) => {
    try {
      await window.SecureDocAPI.reprocessDocument(doc.id);
      toast('Reprocessing started…', 'info');
      await fetchDocs();
      startPoll(doc.id, doc.file_type || 'pdf');
    } catch (e) { toast(_errMsg(e, 'Failed to reprocess'), 'error'); }
  };

  const filtered = docs.filter(d =>
    (d.filename || d.name || '').toLowerCase().includes(search.toLowerCase()) &&
    (!activeGroupFilter || d.group_id === activeGroupFilter)
  );

  const weekViews = (overview?.views_last_7_days || []).reduce((a, d) => a + d.count, 0);
  const highRiskCount = docs.filter(d => d.risk === 'HIGH').length;

  const stats = [
    { label: 'Total Documents', value: (overview?.total_documents || 0).toString(), sub: `${docs.filter(d => d.status === 'ready').length} ready`, icon: '◫', color: C.teal2 },
    { label: 'Active Shares', value: (overview?.active_links || 0).toString(), sub: `${overview?.expiring_soon_count || 0} expiring within 14d`, icon: '◈', color: C.teal2 },
    { label: 'Views Today', value: (overview?.total_views_today || 0).toLocaleString(), sub: `+${weekViews} this week`, icon: '▦', color: C.success },
    { label: 'Blocked Attempts', value: (overview?.blocked_attempts_today || 0).toString(), sub: `${highRiskCount} high-risk docs`, icon: '⊗', color: C.warning },
  ];

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="upload">
        <Btn variant="primary" size="sm" onClick={() => fileRef.current.click()}>↑ Upload</Btn>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
          {stats.map(s => <StatCard key={s.label} s={s} />)}
        </div>

        {/* Upload zone / progress */}
        {!uploading && !uploadDone && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <UploadDropZone dragging={dragging} setDragging={setDragging} simulate={simulate} fileRef={fileRef} />
            <UploadMetadataPanel selectedGroupId={selectedGroupId} setSelectedGroupId={setSelectedGroupId} groups={groups} retentionPolicy={retentionPolicy} setRetentionPolicy={setRetentionPolicy} setGroupModal={setGroupModal} setGroupForm={setGroupForm} />
          </div>
        )}

        {(uploading || uploadDone) && (
          <UploadProgressPanel uploading={uploading} uploadDone={uploadDone} progress={progress} uploadedDoc={uploadedDoc} setUploadDone={setUploadDone} onAccessDoc={onAccessDoc} />
        )}

        {/* Groups filter strip */}
        {groups.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <SectionLabel>Groups</SectionLabel>
            <button onClick={() => setActiveGroupFilter(null)}
              style={{
                fontSize: 10, padding: '3px 10px', borderRadius: 20,
                border: `1px solid ${!activeGroupFilter ? C.teal2 : C.border}`,
                background: !activeGroupFilter ? C.accentBg : 'transparent',
                color: !activeGroupFilter ? C.teal1 : C.textMuted, cursor: 'pointer'
              }}>All</button>
            {groups.map(g => (
              <div key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <button onClick={() => setActiveGroupFilter(activeGroupFilter === g.id ? null : g.id)}
                  style={{
                    fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer',
                    border: `1px solid ${activeGroupFilter === g.id ? g.color : C.border}`,
                    background: activeGroupFilter === g.id ? `${g.color}22` : 'transparent',
                    color: activeGroupFilter === g.id ? g.color : C.textMuted, display: 'flex', alignItems: 'center', gap: 5
                  }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: g.color, display: 'inline-block' }} />
                  {g.name} <span style={{ opacity: 0.6 }}>({g.document_count})</span>
                </button>
                <button onClick={() => { setGroupForm({ name: g.name, color: g.color, description: g.description || '' }); setGroupModal(g); }}
                  style={{ fontSize: 9, padding: '2px 5px', borderRadius: 4, border: `1px solid ${C.border}`, background: 'transparent', color: C.textDim, cursor: 'pointer' }}>✎</button>
                <button onClick={() => handleDeleteGroup(g)}
                  style={{ fontSize: 9, padding: '2px 5px', borderRadius: 4, border: `1px solid ${C.border}`, background: 'transparent', color: C.textDim, cursor: 'pointer' }}>✕</button>
              </div>
            ))}
            <Btn variant="ghost" size="sm" onClick={() => { setGroupForm({ name: '', color: '#6366f1', description: '' }); setGroupModal('new'); }}>+ Group</Btn>
          </div>
        )}

        {/* Documents table */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <SectionLabel>Documents</SectionLabel>
              <Chip color={C.textMuted} bg="transparent" border={C.border}>{filtered.length}</Chip>
              {activeGroupFilter && (() => { const g = groups.find(x => x.id === activeGroupFilter); return g ? <Chip color={g.color} bg={`${g.color}22`} border="transparent">{g.name}</Chip> : null; })()}
            </div>
            <input style={{ width: 200, fontSize: 12 }} placeholder="Search documents…"
              value={search} onChange={e => setSearch(e.target.value)} />
          </div>

          <Card noPad>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['Document', 'Status', 'Risk', 'Pages', 'Views', 'Expires', ''].map(h => (
                    <th key={h} style={{ ...label(9), padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: C.textDim }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {docsLoading ? (
                  <tr><td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: C.textMuted, fontSize: 13 }}>
                    Loading documents…
                  </td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: C.textMuted, fontSize: 13 }}>
                    {docs.length === 0 ? 'No documents yet — upload your first PDF above' : 'No documents match your search'}
                  </td></tr>
                ) : filtered.map((d, i) => (
                  <DocRow key={d.id} doc={d} isLast={i === filtered.length - 1}
                    onView={() => onViewDoc(d)} onAccess={() => onAccessDoc(d)}
                    onDelete={() => setDeleteModal(d)}
                    onReprocess={() => handleReprocess(d)}
                    onQuickShare={setQuickShareDoc}
                    groups={groups} onAssignGroup={handleAssignGroup} />
                ))}
              </tbody>
            </table>
          </Card>
        </div>

        {/* Footer hint */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0' }}>
          <StatusDot status="active" size={5} />
          <span style={{ fontSize: 10, color: C.textMuted }}>All documents converted to images — download disabled by default</span>
        </div>

      </div>

      <Modal open={!!deleteModal} onClose={() => setDeleteModal(null)} title="Delete Document" width={400}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
            All share links for <strong style={{ color: C.textPrimary }}>"{deleteModal?.filename || deleteModal?.name}"</strong> will be permanently revoked.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setDeleteModal(null)}>Cancel</Btn>
            <Btn variant="danger" onClick={() => handleDelete(deleteModal)}>Delete Document</Btn>
          </div>
        </div>
      </Modal>

      {quickShareDoc && (
        <QuickShareModal
          doc={quickShareDoc}
          onClose={() => setQuickShareDoc(null)}
          onConfigure={doc => { setQuickShareDoc(null); onAccessDoc(doc); }}
        />
      )}

      {/* Group create / edit modal */}
      <Modal open={!!groupModal} onClose={() => setGroupModal(null)}
        title={groupModal === 'new' ? 'New Group' : `Edit Group: ${groupForm.name}`} width={380}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Field label="Name">
            <input value={groupForm.name} onChange={e => setGroupForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Q4 Reports" autoFocus />
          </Field>
          <Field label="Color">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <input type="color" value={groupForm.color}
                onChange={e => setGroupForm(f => ({ ...f, color: e.target.value }))}
                style={{ width: 40, height: 32, padding: 2, borderRadius: 6, border: `1px solid ${C.border}`, cursor: 'pointer', background: 'transparent' }} />
              <span style={{ ...mono, fontSize: 11, color: C.textMuted }}>{groupForm.color}</span>
              {['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316'].map(c => (
                <button key={c} onClick={() => setGroupForm(f => ({ ...f, color: c }))}
                  style={{ width: 18, height: 18, borderRadius: '50%', background: c, border: groupForm.color === c ? `2px solid ${C.textPrimary}` : 'none', cursor: 'pointer', padding: 0 }} />
              ))}
            </div>
          </Field>
          <Field label="Description (optional)">
            <input value={groupForm.description}
              onChange={e => setGroupForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Brief description" />
          </Field>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setGroupModal(null)}>Cancel</Btn>
            <Btn variant="primary" loading={groupSaving} onClick={handleSaveGroup}>
              {groupModal === 'new' ? 'Create Group' : 'Save Changes'}
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
