import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { buildFeedbackFilters } from '../utils/feedback.js';
import { label, SectionLabel, StatusDot, RiskBadge, Chip, Btn, Card, Modal, Toggle, Field, Header } from '../components/atoms.jsx';
import { AccessLog } from '../components/access/AccessLog.jsx';
import { TabBtn } from '../components/access/TabBtn.jsx';
import { DocumentPicker } from '../components/DocumentPicker.jsx';

const { useState, useEffect, useCallback } = React;

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

// The 3 audit-trail timestamps below (annotation, reply, visual-annotation
// creation) all want locale date+time, not just date; consolidated here
// instead of repeating `new Date(x).toLocaleString()` 3 times (ENG-024).
const fmtDateTime = (iso) => iso ? new Date(iso).toLocaleString() : '';

export function AccessScreen({ doc, onSelectDoc, defaultTab }) {
  const toast = useToast();
  const [tab, setTab] = useState(defaultTab || 'policy');
  const [links, setLinks] = useState([]);
  const [linksLoading, setLinksLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [revokeModal, setRevokeModal] = useState(false);
  const [quickLinkModal, setQuickLinkModal] = useState(false);
  const [editLinkModal, setEditLinkModal] = useState(null); // link object being edited, or null
  const [editSaving, setEditSaving] = useState(false);
  const [revokeLinkModal, setRevokeLinkModal] = useState(null);
  const [deleteLinkModal, setDeleteLinkModal] = useState(null);
  const [revokingLink, setRevokingLink] = useState(null);
  const [deletingLink, setDeletingLink] = useState(null);
  const [linkCopied, setLinkCopied] = useState(null);
  const [renamingLinkId, setRenamingLinkId] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [saved, setSaved] = useState(false);
  // Feedback tab state (comment + sticky_note)
  const [feedbackItems, setFeedbackItems] = useState([]);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackFilter, setFeedbackFilter] = useState('all'); // 'all'|'open'|'resolved'
  const [feedbackViewerFilter, setFeedbackViewerFilter] = useState(''); // free-text search: root + replies
  const [feedbackDateFrom, setFeedbackDateFrom] = useState('');
  const [feedbackDateTo, setFeedbackDateTo] = useState('');
  const [feedbackPage, setFeedbackPage] = useState('');
  const [feedbackRoleFilter, setFeedbackRoleFilter] = useState('all'); // 'all'|'viewer'|'uploader'
  const [feedbackReviewerFilter, setFeedbackReviewerFilter] = useState(''); // selected reviewer email, '' = all
  const [feedbackReviewers, setFeedbackReviewers] = useState([]); // [{email, name}] for the dropdown
  const [feedbackFiltersOpen, setFeedbackFiltersOpen] = useState(false); // collapsed by default
  const [feedbackAdvancedOpen, setFeedbackAdvancedOpen] = useState(false); // Advanced Filters disclosure, collapsed by default
  const [replyDraft, setReplyDraft] = useState(null);
  const [replyText, setReplyText] = useState('');
  // Annotations tab state (highlight + draw + rectangle + arrow)
  const [visualAnnotations, setVisualAnnotations] = useState([]);
  const [visualLoading, setVisualLoading] = useState(false);
  const [visualTypeFilter, setVisualTypeFilter] = useState('all');

  // Policy form
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [expiry, setExpiry] = useState('');
  const [maxViews, setMaxViews] = useState('');
  const [maxConcurrentSessions, setMaxConcurrentSessions] = useState('');
  const [allowedEmails, setAllowedEmails] = useState('');
  const [allowedDomains, setAllowedDomains] = useState('');
  const [ipAllowlist, setIpAllowlist] = useState('');
  const [label_txt, setLabel] = useState('');
  const [permissions, setPermissions] = useState({
    can_download: false,
    can_print: false,
    can_copy: false,
    can_right_click: false,
    watermark_enabled: true,
    can_annotate: false,
    enable_info: true,
  });

  const docName = doc?.filename || doc?.name || 'Document';
  const docId = doc?.id || '';

  const fetchLinks = useCallback(async () => {
    if (!docId) { setLinksLoading(false); return; }
    try {
      const data = await window.SecureDocAPI.getLinks(docId);
      setLinks(data.links || []);
    } catch (e) { toast(_errMsg(e, 'Failed to load links'), 'error'); }
    finally { setLinksLoading(false); }
  }, [docId]);

  const fetchFeedback = useCallback(async () => {
    if (!docId) return;
    setFeedbackLoading(true);
    try {
      const filters = buildFeedbackFilters({ feedbackFilter, feedbackViewerFilter, feedbackDateFrom, feedbackDateTo, feedbackPage, feedbackRoleFilter, feedbackReviewerFilter });
      const data = await window.SecureDocAPI.getFeedback(docId, filters);
      setFeedbackItems(Array.isArray(data) ? data : (data?.feedback || []));
    } catch (e) { toast(_errMsg(e, 'Failed to load feedback'), 'error'); }
    finally { setFeedbackLoading(false); }
  }, [docId, feedbackFilter, feedbackViewerFilter, feedbackDateFrom, feedbackDateTo, feedbackPage, feedbackRoleFilter, feedbackReviewerFilter]);

  const fetchFeedbackReviewers = useCallback(async () => {
    if (!docId) return;
    try {
      const reviewers = await window.SecureDocAPI.getFeedbackReviewers(docId);
      setFeedbackReviewers(Array.isArray(reviewers) ? reviewers : []);
    } catch { /* non-fatal: dropdown just stays empty */ }
  }, [docId]);

  const fetchVisualAnnotations = useCallback(async () => {
    if (!docId) return;
    setVisualLoading(true);
    try {
      const data = await window.SecureDocAPI.getVisualAnnotations(docId);
      setVisualAnnotations(Array.isArray(data) ? data : (data?.annotations || []));
    } catch (e) { toast(_errMsg(e, 'Failed to load annotations'), 'error'); }
    finally { setVisualLoading(false); }
  }, [docId]);

  useEffect(() => { fetchLinks(); }, [fetchLinks]);
  // Re-run server-side filtering whenever a filter changes (debounced for the free-text search box).
  // Also covers the initial fetch on first switch to the Feedback tab.
  useEffect(() => {
    if (tab !== 'feedback') return;
    const t = setTimeout(() => fetchFeedback(), 350);
    return () => clearTimeout(t);
  }, [tab, feedbackFilter, feedbackViewerFilter, feedbackDateFrom, feedbackDateTo, feedbackPage, feedbackRoleFilter, feedbackReviewerFilter]);
  useEffect(() => { if (tab === 'feedback' && feedbackReviewers.length === 0) fetchFeedbackReviewers(); }, [tab]);
  useEffect(() => { if (tab === 'annotations' && visualAnnotations.length === 0 && !visualLoading) fetchVisualAnnotations(); }, [tab]);

  const activeLinks = links.filter(l => !l.revoked_at && (!l.expires_at || new Date(l.expires_at) > new Date()));

  const handleSave = async () => {
    if (expiry && new Date(expiry) < new Date(new Date().toDateString())) {
      toast('Expiry date cannot be in the past.', 'error'); return;
    }
    if (maxViews && parseInt(maxViews) < 1) {
      toast('Max view count must be at least 1, or leave blank for unlimited.', 'error'); return;
    }
    setCreating(true);
    try {
      const payload = { document_id: docId };
      if (label_txt) payload.label = label_txt;
      if (password) payload.password = password;
      if (maxViews && parseInt(maxViews) >= 1) payload.max_views = parseInt(maxViews);
      if (maxConcurrentSessions) payload.max_concurrent_sessions = parseInt(maxConcurrentSessions);
      if (expiry) payload.expires_at = new Date(expiry + 'T23:59:59').toISOString();
      if (allowedEmails) payload.allowed_emails = allowedEmails.split('\n').map(e => e.trim()).filter(Boolean);
      if (allowedDomains) payload.allowed_domains = allowedDomains.split(',').map(d => d.trim()).filter(Boolean);
      if (ipAllowlist) payload.ip_allowlist = ipAllowlist.split(',').map(i => i.trim()).filter(Boolean);
      payload.permissions = permissions;
      await window.SecureDocAPI.createLink(payload);
      setSaved(true); setTimeout(() => setSaved(false), 2500);
      toast('New share link created', 'success');
      await fetchLinks(); setTab('link');
    } catch (e) { toast(_errMsg(e, 'Failed to create link'), 'error'); }
    finally { setCreating(false); }
  };

  const handleRevoke = async () => {
    setRevokeModal(false);
    for (const l of activeLinks) { try { await window.SecureDocAPI.revokeLink(l.id); } catch { } }
    toast('All access revoked. Share links are now invalid.', 'error');
    await fetchLinks();
  };

  const handleCopy = (text, lbl) => {
    try { navigator.clipboard.writeText(text); } catch { }
    setLinkCopied(text);
    setTimeout(() => setLinkCopied(null), 2200);
    toast(`${lbl} copied to clipboard`, 'success');
  };

  const handleRename = async (linkId) => {
    const trimmed = renameValue.trim();
    setRenamingLinkId(null);
    try {
      await window.SecureDocAPI.updateLink(linkId, { label: trimmed || null });
      await fetchLinks();
      toast('Link renamed', 'success');
    } catch (e) { toast(_errMsg(e, 'Failed to rename'), 'error'); }
  };

  const TABS = [
    { id: 'policy', label: 'Create Link' },
    { id: 'link', label: 'Links' },
    { id: 'log', label: 'View History' },
    { id: 'feedback', label: 'Feedback' },
    { id: 'annotations', label: 'Annotations' },
  ];

  // No document selected — show inline picker so user stays on this tab.
  if (!docId) {
    return (
      <div data-testid="access-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Header screen="access" />
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          <DocumentPicker onSelect={(d) => { if (onSelectDoc) onSelectDoc(d); }} />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="access-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="access" breadcrumb={docName.length > 32 ? docName.slice(0, 32) + '…' : docName}>
        {activeLinks.length > 0
          ? <Btn variant="outline-danger" size="sm" onClick={() => setRevokeModal(true)}>✕ Revoke All Access</Btn>
          : <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 6, padding: '4px 10px'
          }}>
            <StatusDot status="error" size={5} />
            <span style={{ ...mono, fontSize: 10, color: C.error, letterSpacing: '0.5px' }}>NO ACTIVE LINKS</span>
          </div>
        }
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* Document identity bar */}
        <Card style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 38, height: 38, background: C.accentBg,
                border: `1px solid ${C.borderMed}`, borderRadius: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 15, color: C.teal2
              }}>◫</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 2 }}>{docName}</div>
                <div style={{ ...mono, fontSize: 9, color: C.textMuted }}>{docId}</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <StatusDot status={activeLinks.length === 0 ? 'error' : 'active'} />
                <span style={{ fontSize: 11, color: activeLinks.length === 0 ? C.error : C.success, fontWeight: 600 }}>
                  {activeLinks.length === 0 ? 'Revoked' : 'Active'}
                </span>
              </div>
              <RiskBadge level={doc?.risk} />
              <Chip color={C.textMuted} bg="transparent" border={C.border}>
                {doc?.total_views ?? 0} views
              </Chip>
            </div>
          </div>
        </Card>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0, borderBottom: `1px solid ${C.border}`, marginBottom: -2 }}>
          {TABS.map(t => <TabBtn key={t.id} tab={t} active={tab === t.id} onClick={() => setTab(t.id)} />)}
        </div>

        {tab === 'policy' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="fade-in">
            {/* Auth card */}
            <Card>
              <SectionLabel style={{ marginBottom: 14 }}>Authentication</SectionLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Field label="Password Protection">
                  <div style={{ position: 'relative' }}>
                    <input type={showPass ? 'text' : 'password'} value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="Leave blank to disable" style={{ paddingRight: 52 }} />
                    <button onClick={() => setShowPass(v => !v)}
                      style={{
                        position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                        background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer',
                        fontSize: 10, fontWeight: 600, letterSpacing: '0.5px', fontFamily: "'DM Mono',monospace"
                      }}>
                      {showPass ? 'HIDE' : 'SHOW'}
                    </button>
                  </div>
                </Field>
                <Field label="Allowed Domains" hint="Comma-separated, e.g. @acme.io">
                  <input value={allowedDomains} onChange={e => setAllowedDomains(e.target.value)} placeholder="@acme.io, @partner.com" />
                </Field>
                <Field label="Allowed Emails">
                  <textarea value={allowedEmails} onChange={e => setAllowedEmails(e.target.value)}
                    rows={3} style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, resize: 'vertical' }} />
                </Field>
              </div>
            </Card>

            {/* Limits card */}
            <Card>
              <SectionLabel style={{ marginBottom: 14 }}>Access Limits</SectionLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Field label="Expiry Date">
                  <input type="date" value={expiry} onChange={e => setExpiry(e.target.value)} />
                </Field>
                <Field label="View Limit" hint="Total number of times this link can be opened">
                  <input type="number" value={maxViews} onChange={e => setMaxViews(e.target.value)} placeholder="Unlimited" />
                </Field>
                <Field label="Max Simultaneous Viewers" hint="How many people can view at the same time">
                  <input type="number" value={maxConcurrentSessions} onChange={e => setMaxConcurrentSessions(e.target.value)} placeholder="Unlimited" min="1" />
                </Field>
                <Field label="IP Allowlist" hint="CIDR or exact, e.g. 10.0.0.0/24">
                  <input value={ipAllowlist} onChange={e => setIpAllowlist(e.target.value)} placeholder="10.0.0.0/24, 192.168.1.1" />
                </Field>
              </div>
            </Card>

            {/* Permissions + Link Name + action buttons */}
            <Card style={{ gridColumn: '1 / -1' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <SectionLabel style={{ marginBottom: 12 }}>Document Permissions</SectionLabel>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                    {Object.entries({
                      can_download: 'Download',
                      can_print: 'Print',
                      can_copy: 'Copy Text',
                      can_right_click: 'Right Click',
                      watermark_enabled: 'Watermark',
                      can_annotate: 'Annotations',
                      enable_info: 'Info Panel',
                    }).map(([key, labelText]) => (
                      <div key={key} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '8px 10px', background: 'rgba(90,200,208,0.03)',
                        border: `1px solid ${C.border}`, borderRadius: 7
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          <span style={{ fontSize: 13, color: permissions[key] ? C.teal1 : C.textMuted }}>{permissions[key] ? '✓' : '—'}</span>
                          <span style={{ fontSize: 12, color: permissions[key] ? C.textPrimary : C.textMuted, fontWeight: 500 }}>{labelText}</span>
                        </div>
                        <Toggle enabled={permissions[key]} onChange={() => setPermissions(p => ({ ...p, [key]: !p[key] }))} />
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginLeft: 20, flexShrink: 0, minWidth: 160 }}>
                  <Field label="Link Name">
                    <input
                      value={label_txt}
                      onChange={e => setLabel(e.target.value)}
                      placeholder="e.g. Client Review, Tender Submission"
                      style={{ fontSize: 12 }}
                    />
                  </Field>
                  <Btn variant="primary" onClick={handleSave} disabled={creating} style={{ minWidth: 130 }}>
                    {saved ? '✓ Created' : creating ? '…' : 'Create Share Link'}
                  </Btn>
                  <Btn variant="secondary" disabled={creating || !docId} onClick={() => setQuickLinkModal(true)} style={{ minWidth: 130 }}>
                    + Quick Link
                  </Btn>
                </div>
              </div>
            </Card>
          </div>
        )}

        {tab === 'link' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} className="fade-in">
            {linksLoading ? (
              <div style={{ padding: '24px', color: C.textMuted, fontSize: 13 }}>Loading links…</div>
            ) : links.length === 0 ? (
              <Card><div style={{ textAlign: 'center', color: C.textMuted, fontSize: 13, padding: '12px 0' }}>No share links yet — create one in the Create Link tab.</div></Card>
            ) : links.map(link => (
              <Card key={link.id}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <StatusDot status={link.revoked_at ? 'error' : 'active'} />
                    {renamingLinkId === link.id ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={e => setRenameValue(e.target.value)}
                        onBlur={() => handleRename(link.id)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleRename(link.id);
                          if (e.key === 'Escape') setRenamingLinkId(null);
                        }}
                        style={{
                          fontSize: 12, fontWeight: 600, background: C.surface2,
                          border: `1px solid ${C.teal1}`, borderRadius: 5,
                          padding: '2px 7px', color: C.textPrimary, minWidth: 140,
                        }}
                      />
                    ) : (
                      <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>
                        {link.label || 'Untitled Link'}
                      </span>
                    )}
                    {!link.revoked_at && renamingLinkId !== link.id && (
                      <button
                        onClick={() => { setRenamingLinkId(link.id); setRenameValue(link.label || ''); }}
                        title="Rename link" aria-label="Rename link"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: C.textDim, fontSize: 11, padding: '0 2px', lineHeight: 1 }}
                      >✎</button>
                    )}
                    {link.has_password && <Chip color={C.warning} bg={C.warningBg} border={C.warningBdr}>PASSWORD</Chip>}
                    {link.revoked_at && <Chip color={C.error} bg={C.errorBg} border={C.errorBdr}>REVOKED</Chip>}
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {!link.revoked_at && (
                      <>
                        <Btn variant="ghost" size="sm" onClick={() => setEditLinkModal(link)}>Edit</Btn>
                        <Btn variant="ghost" size="sm" onClick={() => setRevokeLinkModal(link)} style={{ color: C.error }}>Revoke</Btn>
                      </>
                    )}
                    {link.revoked_at && (
                      <Btn variant="ghost" size="sm" disabled={deletingLink === link.id}
                        onClick={() => setDeleteLinkModal(link)} style={{ color: C.error }}>
                        {deletingLink === link.id ? '…' : 'Delete'}
                      </Btn>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                  <div style={{
                    flex: 1, ...mono, fontSize: 11,
                    background: C.surfaceAlt, border: `1px solid ${C.border}`, borderRadius: 7,
                    padding: '9px 12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                  }}>
                    {link.revoked_at
                      ? <span style={{ color: C.error }}>— link revoked —</span>
                      : <a href={link.share_url} target="_blank" rel="noopener noreferrer"
                           style={{ color: C.teal1, textDecoration: 'none' }}
                           onMouseEnter={e => e.target.style.textDecoration = 'underline'}
                           onMouseLeave={e => e.target.style.textDecoration = 'none'}>
                          {link.share_url}
                        </a>
                    }
                  </div>
                  <Btn variant={linkCopied === link.share_url ? 'secondary' : 'primary'} size="sm"
                    onClick={() => handleCopy(link.share_url, 'Share link')} disabled={!!link.revoked_at}>
                    {linkCopied === link.share_url ? '✓ Copied' : '⧉ Copy'}
                  </Btn>
                  {!link.revoked_at && (
                    <Btn variant="ghost" size="sm" onClick={() => window.open(link.share_url, '_blank')}
                      title="Open link in new tab" aria-label="Open share link in new tab">↗</Btn>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                  {(() => {
                    const expiresVal = link.expires_at ? fmtDate(link.expires_at) : 'Never';
                    const expiringSoon = link.expires_at && !link.revoked_at &&
                      (new Date(link.expires_at) - Date.now()) < 3 * 24 * 60 * 60 * 1000;
                    const emailCount = (link.allowed_emails || []).length;
                    const domainCount = (link.allowed_domains || []).length;
                    const watermark = link.permissions?.watermark_enabled !== false;
                    return [
                      { k: 'Views', v: `${link.view_count}${link.max_views ? ' / ' + link.max_views : ''}` },
                      { k: 'Expires', v: expiresVal, warn: expiringSoon },
                      { k: 'Emails', v: emailCount > 0 ? `${emailCount} allowed` : 'Any' },
                      { k: 'Domains', v: domainCount > 0 ? `${domainCount} allowed` : 'Any' },
                      { k: 'Watermark', v: watermark ? 'On' : 'Off' },
                      { k: 'Created', v: fmtDate(link.created_at) },
                    ].map(({ k, v, warn }) => (
                      <div key={k} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <span style={{ ...label(8) }}>{k}</span>
                        <span style={{ ...mono, fontSize: 11, color: warn ? C.warning : C.textSecondary }}>{v}</span>
                      </div>
                    ));
                  })()}
                </div>
                {!link.revoked_at && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ background: C.surfaceAlt, borderRadius: 7, padding: 14, border: `1px solid ${C.border}` }}>
                      <SectionLabel style={{ marginBottom: 8 }}>Embed Code</SectionLabel>
                      <pre style={{ ...mono, fontSize: 10, color: C.textSecondary, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                        {`<iframe\n  src="${link.share_url}"\n  width="100%" height="600"\n  frameborder="0" sandbox="allow-scripts allow-same-origin">\n</iframe>`}
                      </pre>
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}

        {tab === 'log' && (
          <div className="fade-in">
            <AccessLog docId={docId} />
          </div>
        )}

        {/* ── FEEDBACK TAB: comment + sticky_note only ── */}
        {tab === 'feedback' && (
          <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <Btn variant="ghost" size="sm" onClick={fetchFeedback}>↺ Refresh</Btn>
              <select
                value=""
                onChange={e => {
                  const mode = e.target.value;
                  const filters = buildFeedbackFilters({ feedbackFilter, feedbackViewerFilter, feedbackDateFrom, feedbackDateTo, feedbackPage, feedbackRoleFilter, feedbackReviewerFilter });
                  if (mode === 'conversations') window.SecureDocAPI.exportFeedback(docId, filters);
                  else if (mode === 'reviewer_activity') window.SecureDocAPI.exportReviewerActivity(docId);
                  e.target.value = '';
                }}
                style={{ fontSize: 11, background: C.teal1, border: `1px solid ${C.teal1}`, borderRadius: 6, padding: '4px 8px', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
              >
                <option value="" disabled>↓ Export…</option>
                <option value="conversations">Export Feedback Conversations</option>
                <option value="reviewer_activity">Export Reviewer Activity</option>
              </select>
              <Btn variant={feedbackFiltersOpen ? 'primary' : 'ghost'} size="sm" onClick={() => setFeedbackFiltersOpen(o => !o)}>
                ⚙ Filters {feedbackFiltersOpen ? '▲' : '▼'}
              </Btn>
              <span style={{ ...mono, fontSize: 10, color: C.textMuted, marginLeft: 'auto' }}>
                {feedbackItems.length} thread{feedbackItems.length !== 1 ? 's' : ''}
              </span>
            </div>

            {feedbackFiltersOpen && (
              <Card noPad>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: 12 }}>
                  <input
                    placeholder="Search comments…"
                    value={feedbackViewerFilter}
                    onChange={e => setFeedbackViewerFilter(e.target.value)}
                    title="Searches the conversation text"
                    style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary, width: 200 }}
                  />
                  <select value={feedbackFilter} onChange={e => setFeedbackFilter(e.target.value)}
                    style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary }}>
                    <option value="all">All status</option>
                    <option value="open">Open only</option>
                    <option value="resolved">Resolved only</option>
                  </select>
                  <select value={feedbackReviewerFilter} onChange={e => setFeedbackReviewerFilter(e.target.value)}
                    style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary }}>
                    <option value="">All reviewers</option>
                    {feedbackReviewers.map(r => (
                      <option key={r.email} value={r.email}>{r.name || r.email}</option>
                    ))}
                  </select>
                  <input
                    type="number" min="1" placeholder="Page #"
                    value={feedbackPage}
                    onChange={e => setFeedbackPage(e.target.value)}
                    style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary, width: 70 }}
                  />
                  <Btn variant="ghost" size="sm" onClick={() => {
                    setFeedbackFilter('all'); setFeedbackRoleFilter('all'); setFeedbackPage('');
                    setFeedbackDateFrom(''); setFeedbackDateTo(''); setFeedbackViewerFilter(''); setFeedbackReviewerFilter('');
                  }}>Clear filters</Btn>
                </div>
                <div style={{ borderTop: `1px solid ${C.border}` }}>
                  <button
                    onClick={() => setFeedbackAdvancedOpen(o => !o)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: C.textMuted, fontSize: 11, padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 4 }}
                  >
                    Advanced Filters {feedbackAdvancedOpen ? '▲' : '▼'}
                  </button>
                  {feedbackAdvancedOpen && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: '0 12px 12px' }}>
                      <input
                        type="date" value={feedbackDateFrom}
                        onChange={e => setFeedbackDateFrom(e.target.value)}
                        title="From date"
                        style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary }}
                      />
                      <input
                        type="date" value={feedbackDateTo}
                        onChange={e => setFeedbackDateTo(e.target.value)}
                        title="To date"
                        style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary }}
                      />
                      <select value={feedbackRoleFilter} onChange={e => setFeedbackRoleFilter(e.target.value)}
                        title="Match if ANY message in the thread (root or reply) was authored by this role"
                        style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary }}>
                        <option value="all">All authors</option>
                        <option value="viewer">Viewer messages</option>
                        <option value="uploader">Uploader messages</option>
                      </select>
                    </div>
                  )}
                </div>
              </Card>
            )}

            <Card noPad>
              {feedbackLoading ? (
                <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 13 }}>Loading feedback…</div>
              ) : (() => {
                const shown = feedbackItems;
                if (shown.length === 0) return (
                  <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 13 }}>No feedback yet. Viewers can leave comments when they view this document.</div>
                );
                return (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                        {['Reviewer', 'Page', 'Comment', 'Replies', 'Status', 'Created At', ''].map(h => (
                          <th key={h} style={{ ...label(9), padding: '9px 14px', textAlign: 'left', fontWeight: 600, color: C.textDim }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {shown.map((a) => (
                        <React.Fragment key={a.id}>
                          {/* Top-level feedback row */}
                          <tr style={{ borderTop: `1px solid ${C.border}`, background: a.resolved_at ? C.successBg : 'transparent' }}>
                            <td style={{ padding: '9px 14px', fontSize: 11, ...mono }}>
                              <span
                                onClick={() => { if (a.viewer_email) { setFeedbackReviewerFilter(a.viewer_email); setFeedbackFiltersOpen(true); } }}
                                title={a.viewer_email ? 'Filter feedback by this reviewer' : undefined}
                                style={{
                                  cursor: a.viewer_email ? 'pointer' : 'default',
                                  color: a.viewer_email ? C.teal2 : C.textPrimary,
                                  fontWeight: 600,
                                  textDecoration: a.viewer_email ? 'underline' : 'none',
                                }}
                              >
                                {a.display_name || 'Anonymous Viewer'}
                              </span>
                              <div style={{ fontSize: 10, color: C.textMuted, marginTop: 2 }}>{a.viewer_email || '—'}</div>
                              <div style={{ fontSize: 9, color: C.textDim, marginTop: 2 }}>{a.annotation_type}</div>
                            </td>
                            <td style={{ padding: '9px 14px', fontSize: 11, color: C.textSecondary, whiteSpace: 'nowrap' }}>p.{a.page_number}</td>
                            <td style={{ padding: '9px 14px', fontSize: 12, color: C.textPrimary, maxWidth: 280 }}>
                              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {a.comment_text || <span style={{ color: C.textDim }}>—</span>}
                              </div>
                            </td>
                            <td style={{ padding: '9px 14px', fontSize: 11, color: a.reply_count > 0 ? C.teal2 : C.textMuted, ...mono }}>
                              {a.reply_count || 0}
                            </td>
                            <td style={{ padding: '9px 14px', whiteSpace: 'nowrap' }}>
                              {a.resolved_at
                                ? <Chip color={C.success} bg={C.successBg} border="transparent">Resolved</Chip>
                                : <Chip color={C.textMuted} bg="transparent" border={C.border}>Open</Chip>}
                            </td>
                            <td style={{ padding: '9px 14px', fontSize: 10, color: C.textMuted, ...mono, whiteSpace: 'nowrap' }}>
                              {fmtDateTime(a.created_at)}
                            </td>
                            <td style={{ padding: '9px 14px', whiteSpace: 'nowrap' }}>
                              <div style={{ display: 'flex', gap: 4 }}>
                                <Btn variant="ghost" size="sm" onClick={() => setReplyDraft(replyDraft === a.id ? null : a.id)}>
                                  {replyDraft === a.id ? '✕' : '↩ Reply'}
                                </Btn>
                                <Btn variant={a.resolved_at ? 'secondary' : 'ghost'} size="sm" onClick={async () => {
                                  try {
                                    await window.SecureDocAPI.resolveFeedback(docId, a.id);
                                    await fetchFeedback();
                                  } catch (err) { toast(_errMsg(err, 'Failed to update'), 'error'); }
                                }}>
                                  {a.resolved_at ? '↺ Reopen' : '✓ Resolve'}
                                </Btn>
                              </div>
                            </td>
                          </tr>
                          {/* Existing replies (indented) */}
                          {(a.replies || []).map(r => (
                            <tr key={r.id} style={{ borderTop: `1px solid ${C.border}`, background: C.surfaceAlt }}>
                              <td style={{ padding: '7px 14px 7px 28px', fontSize: 11, ...mono }}>
                                <span style={{ color: C.teal3, marginRight: 6 }}>↳</span>
                                <span style={{ color: r.author_role === 'uploader' ? C.teal2 : C.textPrimary, fontWeight: 600 }}>
                                  {r.display_name}{r.author_role === 'uploader' ? ' (you)' : ''}
                                </span>
                                {r.viewer_email && <span style={{ marginLeft: 6, color: C.textDim, fontSize: 10 }}>{r.viewer_email}</span>}
                              </td>
                              <td style={{ padding: '7px 14px', fontSize: 11, color: C.textSecondary }}>p.{r.page_number}</td>
                              <td colSpan={3} style={{ padding: '7px 14px', fontSize: 11, color: C.textPrimary }}>
                                {r.comment_text || '—'}
                              </td>
                              <td style={{ padding: '7px 14px', fontSize: 10, color: C.textMuted, ...mono, whiteSpace: 'nowrap' }}>
                                {fmtDateTime(r.created_at)}
                              </td>
                              <td />
                            </tr>
                          ))}
                          {/* Inline reply composer */}
                          {replyDraft === a.id && (
                            <tr style={{ background: C.surfaceMid }}>
                              <td colSpan={7} style={{ padding: '8px 14px 10px 28px' }}>
                                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                                  <span style={{ color: C.teal3, fontSize: 14, marginTop: 6 }}>↳</span>
                                  <textarea
                                    value={replyText}
                                    onChange={e => setReplyText(e.target.value)}
                                    placeholder="Write your reply…"
                                    autoFocus
                                    style={{
                                      flex: 1, fontSize: 11, resize: 'vertical', minHeight: 52,
                                      background: C.surface3, border: `1px solid ${C.borderMed}`,
                                      borderRadius: 5, padding: '6px 8px', color: C.textPrimary,
                                      fontFamily: "'DM Sans',sans-serif", outline: 'none',
                                    }}
                                    onKeyDown={e => e.key === 'Escape' && setReplyDraft(null)}
                                  />
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    <Btn variant="primary" size="sm" onClick={async () => {
                                      if (!replyText.trim()) return;
                                      try {
                                        await window.SecureDocAPI.replyToFeedback(docId, a.id, replyText.trim());
                                        setReplyDraft(null);
                                        setReplyText('');
                                        await fetchFeedback();
                                        toast('Reply posted', 'success');
                                      } catch (err) { toast(_errMsg(err, 'Failed to post reply'), 'error'); }
                                    }}>Send</Btn>
                                    <Btn variant="ghost" size="sm" onClick={() => setReplyDraft(null)}>Cancel</Btn>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                );
              })()}
            </Card>
          </div>
        )}

        {/* ── ANNOTATIONS TAB: highlight + draw + rectangle + arrow only ── */}
        {tab === 'annotations' && (
          <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <select value={visualTypeFilter} onChange={e => setVisualTypeFilter(e.target.value)}
                style={{ fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 8px', color: C.textSecondary }}>
                <option value="all">All types</option>
                <option value="highlight">Highlight</option>
                <option value="draw">Draw</option>
                <option value="rectangle">Rectangle</option>
                <option value="arrow">Arrow</option>
              </select>
              <Btn variant="ghost" size="sm" onClick={fetchVisualAnnotations}>↺ Refresh</Btn>
              <Btn variant="ghost" size="sm" onClick={() => window.SecureDocAPI.exportVisualAnnotations(docId)}>↓ Export CSV</Btn>
              <span style={{ ...mono, fontSize: 10, color: C.textMuted, marginLeft: 'auto' }}>
                {visualAnnotations.length} annotation{visualAnnotations.length !== 1 ? 's' : ''}
              </span>
            </div>

            <Card noPad>
              {visualLoading ? (
                <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 13 }}>Loading annotations…</div>
              ) : (() => {
                const shown = visualAnnotations.filter(a =>
                  visualTypeFilter === 'all' || a.annotation_type === visualTypeFilter
                );
                if (shown.length === 0) return (
                  <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 13 }}>No visual annotations yet</div>
                );
                return (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                        {['Viewer', 'Page', 'Type', 'Color', 'Created'].map(h => (
                          <th key={h} style={{ ...label(9), padding: '9px 14px', textAlign: 'left', fontWeight: 600, color: C.textDim }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {shown.map((a, i) => (
                        <tr key={a.id} style={{ borderTop: `1px solid ${C.border}` }}>
                          <td style={{ padding: '8px 14px', fontSize: 11, color: C.textMuted, ...mono }}>
                            {a.viewer_email_masked || (a.session_id?.slice(0, 8) + '…')}
                          </td>
                          <td style={{ padding: '8px 14px', fontSize: 11, color: C.textSecondary, whiteSpace: 'nowrap' }}>p.{a.page_number}</td>
                          <td style={{ padding: '8px 14px', fontSize: 10, ...mono, color: C.teal3 }}>{a.annotation_type}</td>
                          <td style={{ padding: '8px 14px' }}>
                            {a.color && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 14, height: 14, borderRadius: 3, background: a.color, border: `1px solid ${C.border}`, flexShrink: 0 }} />
                                <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{a.color}</span>
                              </div>
                            )}
                          </td>
                          <td style={{ padding: '8px 14px', fontSize: 10, color: C.textMuted, ...mono, whiteSpace: 'nowrap' }}>
                            {fmtDateTime(a.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                );
              })()}
            </Card>
          </div>
        )}
      </div>

      {/* Edit Link modal */}
      {editLinkModal && (
        <EditLinkModal
          link={editLinkModal}
          saving={editSaving}
          onClose={() => setEditLinkModal(null)}
          onSave={async (patch) => {
            setEditSaving(true);
            try {
              await window.SecureDocAPI.updateLink(editLinkModal.id, patch);
              setEditLinkModal(null);
              await fetchLinks();
              toast('Link updated', 'success');
            } catch (e) { toast(_errMsg(e, 'Failed to update link'), 'error'); }
            finally { setEditSaving(false); }
          }}
        />
      )}

      {/* Revoke confirmation modal */}
      <Modal open={quickLinkModal} onClose={() => setQuickLinkModal(false)} title="Create Unrestricted Link" width={440}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: 'rgba(245,158,11,0.08)', border: `1px solid rgba(245,158,11,0.3)`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.warning }}>⚠ This creates a link with no restrictions.</strong><br />
            Anyone with the link can view the document with no password, no expiry, and no view limit. Use "Create Share Link" above to configure restrictions.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setQuickLinkModal(false)}>Cancel</Btn>
            <Btn variant="primary" loading={creating}
              onClick={async () => {
                setQuickLinkModal(false);
                setCreating(true);
                try {
                  await window.SecureDocAPI.createLink({ document_id: docId });
                  await fetchLinks();
                  setTab('link');
                  toast('Unrestricted share link created', 'success');
                } catch (e) { toast(_errMsg(e, 'Failed to create link'), 'error'); }
                finally { setCreating(false); }
              }}>
              Create Anyway
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!revokeLinkModal} onClose={() => setRevokeLinkModal(null)} title="Revoke Share Link" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: 'rgba(245,158,11,0.08)', border: `1px solid rgba(245,158,11,0.3)`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.warning }}>⚠ This will immediately terminate all active sessions for this link.</strong><br />
            Anyone currently viewing through <strong style={{ color: C.textPrimary }}>"{revokeLinkModal?.label || 'Untitled Link'}"</strong> will be disconnected.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setRevokeLinkModal(null)}>Cancel</Btn>
            <Btn variant="danger" loading={revokingLink === revokeLinkModal?.id}
              onClick={async () => {
                const link = revokeLinkModal;
                setRevokeLinkModal(null);
                setRevokingLink(link.id);
                try { await window.SecureDocAPI.revokeLink(link.id); toast('Link revoked', 'info'); await fetchLinks(); }
                catch (e) { toast(_errMsg(e, 'Failed'), 'error'); }
                finally { setRevokingLink(null); }
              }}>
              Revoke Link
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={!!deleteLinkModal} onClose={() => setDeleteLinkModal(null)} title="Delete Share Link" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
            <strong style={{ color: C.textPrimary }}>"{deleteLinkModal?.label || 'Untitled Link'}"</strong> and all its view history will be permanently deleted.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setDeleteLinkModal(null)}>Cancel</Btn>
            <Btn variant="danger" loading={deletingLink === deleteLinkModal?.id}
              onClick={async () => {
                const link = deleteLinkModal;
                setDeleteLinkModal(null);
                setDeletingLink(link.id);
                try { await window.SecureDocAPI.deleteLink(link.id); toast('Link deleted', 'info'); await fetchLinks(); }
                catch (e) { toast(_errMsg(e, 'Failed to delete link'), 'error'); }
                finally { setDeletingLink(null); }
              }}>
              Delete Link
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={revokeModal} onClose={() => setRevokeModal(false)} title="Revoke All Access" width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
          }}>
            <strong style={{ color: C.error }}>⚠ This action is immediate and irreversible.</strong><br />
            All active share links for <strong style={{ color: C.textPrimary }}>"{docName}"</strong> will stop working instantly. Viewers mid-session will be kicked out.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {['All share links invalidated', 'Active sessions terminated', 'Access log preserved'].map(item => (
              <div key={item} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, color: C.textMuted }}>
                <span style={{ color: C.error, fontWeight: 700 }}>✕</span> {item}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" onClick={() => setRevokeModal(false)}>Cancel</Btn>
            <Btn variant="danger" onClick={handleRevoke}>Revoke All Access</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function EditLinkModal({ link, saving, onClose, onSave }) {
  const [label_txt, setLabel] = useState(link.label || '');
  const [password, setPassword] = useState('');
  const [expiry, setExpiry] = useState(link.expires_at ? link.expires_at.slice(0, 10) : '');
  const [maxViews, setMaxViews] = useState(link.max_views != null ? String(link.max_views) : '');
  const [maxConcurrentSessions, setMaxConcurrentSessions] = useState(
    link.max_concurrent_sessions != null ? String(link.max_concurrent_sessions) : ''
  );
  const [allowedEmails, setAllowedEmails] = useState((link.allowed_emails || []).join('\n'));
  const [allowedDomains, setAllowedDomains] = useState((link.allowed_domains || []).join(', '));
  const [ipAllowlist, setIpAllowlist] = useState((link.ip_allowlist || []).join(', '));
  const [permissions, setPermissions] = useState(link.permissions || {
    can_download: false, can_print: false, can_copy: false, can_right_click: false,
    watermark_enabled: true, can_annotate: false, enable_info: true,
  });

  const toast = useToast();
  const handleSubmit = () => {
    if (expiry && new Date(expiry) < new Date(new Date().toDateString())) {
      toast('Expiry date cannot be in the past.', 'error'); return;
    }
    if (maxViews && parseInt(maxViews) < 1) {
      toast('Max view count must be at least 1.', 'error'); return;
    }
    const patch = {};
    patch.label = label_txt || null;
    if (password) patch.password = password;
    patch.expires_at = expiry ? new Date(expiry + 'T23:59:59').toISOString() : null;
    patch.max_views = maxViews && parseInt(maxViews) >= 1 ? parseInt(maxViews) : null;
    patch.max_concurrent_sessions = maxConcurrentSessions ? parseInt(maxConcurrentSessions) : null;
    patch.allowed_emails = allowedEmails ? allowedEmails.split('\n').map(e => e.trim()).filter(Boolean) : null;
    patch.allowed_domains = allowedDomains ? allowedDomains.split(',').map(d => d.trim()).filter(Boolean) : null;
    patch.ip_allowlist = ipAllowlist ? ipAllowlist.split(',').map(i => i.trim()).filter(Boolean) : null;
    patch.permissions = permissions;
    onSave(patch);
  };

  return (
    <Modal open={true} onClose={onClose} title={`Edit Link — ${link.label || 'Untitled'}`} width={520}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Label">
            <input value={label_txt} onChange={e => setLabel(e.target.value)} placeholder="Untitled Link" />
          </Field>
          <Field label="New Password" hint="Leave blank to keep existing">
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="unchanged" />
          </Field>
          <Field label="Expiry Date">
            <input type="date" value={expiry} onChange={e => setExpiry(e.target.value)} />
          </Field>
          <Field label="Max Views">
            <input type="number" value={maxViews} onChange={e => setMaxViews(e.target.value)} placeholder="Unlimited" />
          </Field>
          <Field label="Max Simultaneous Viewers" hint="Viewers at the same time">
            <input type="number" value={maxConcurrentSessions} onChange={e => setMaxConcurrentSessions(e.target.value)} placeholder="Unlimited" min="1" />
          </Field>
          <Field label="Allowed Domains" hint="Comma-separated">
            <input value={allowedDomains} onChange={e => setAllowedDomains(e.target.value)} placeholder="@acme.io, @partner.com" />
          </Field>
        </div>
        <Field label="Allowed Emails" hint="One per line">
          <textarea value={allowedEmails} onChange={e => setAllowedEmails(e.target.value)}
            rows={3} style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, resize: 'vertical' }} />
        </Field>
        <Field label="IP Allowlist" hint="CIDR or exact, comma-separated">
          <input value={ipAllowlist} onChange={e => setIpAllowlist(e.target.value)} placeholder="10.0.0.0/24, 192.168.1.1" />
        </Field>
        <div>
          <SectionLabel style={{ marginBottom: 8 }}>Permissions</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 6 }}>
            {Object.entries({
              can_download: 'Download', can_print: 'Print', can_copy: 'Copy Text',
              can_right_click: 'Right Click', watermark_enabled: 'Watermark',
              can_annotate: 'Annotations', enable_info: 'Info Panel',
            }).map(([key, labelText]) => (
              <div key={key} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 10px', background: 'rgba(90,200,208,0.03)',
                border: `1px solid ${C.border}`, borderRadius: 7
              }}>
                <span style={{ fontSize: 11, color: permissions[key] ? C.textPrimary : C.textMuted }}>{labelText}</span>
                <Toggle enabled={permissions[key]} onChange={() => setPermissions(p => ({ ...p, [key]: !p[key] }))} />
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" onClick={handleSubmit} disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</Btn>
        </div>
      </div>
    </Modal>
  );
}
