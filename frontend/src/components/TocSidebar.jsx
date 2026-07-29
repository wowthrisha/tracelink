import { C, mono } from '../constants/tokens.js';

const { useState, useEffect } = React;

export function TocSidebar({ linkToken, sessionId, currentPage, docType, pageCount, onNavigate, onClose }) {
  const [toc, setToc] = useState([]);
  const [loading, setLoading] = useState(true);
  const isImageDoc = docType === 'pdf' || docType === 'docx' || docType === 'doc';

  useEffect(() => {
    if (!linkToken || !sessionId) return;
    setLoading(true);
    window.SecureDocAPI.getToc(linkToken, sessionId)
      .then(data => setToc(data.toc || []))
      .catch(() => setToc([]))
      .finally(() => setLoading(false));
  }, [linkToken, sessionId]);

  const navTarget = (entry) => isImageDoc
    ? (entry.page != null ? entry.page : null)
    : (entry.chunk != null ? entry.chunk : null);

  const isCurrent = (entry) => navTarget(entry) === currentPage;

  return (
    <div style={{
      width: 240, background: C.surfaceAlt, borderRight: `1px solid ${C.border}`,
      display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0
    }}>
      <div style={{
        padding: '10px 12px', borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0
      }}>
        <span style={{ ...mono, fontSize: 10, color: C.teal2, letterSpacing: '0.6px' }}>
          TABLE OF CONTENTS
        </span>
        <button
          onClick={onClose}
          aria-label="Close TOC"
          style={{ background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', fontSize: 14, padding: '2px 4px' }}>
          ✕
        </button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '6px 0' }}>
        {loading ? (
          <div style={{ padding: '16px 12px', color: C.textMuted, fontSize: 11 }}>Loading…</div>
        ) : toc.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            <div style={{ padding: '8px 12px 4px', fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'rgba(130,142,158,0.5)' }}>
              Pages
            </div>
            {Array.from({ length: pageCount || 0 }, (_, i) => i + 1).map(p => (
              <div key={p} onClick={() => onNavigate(p)} style={{
                padding: '5px 14px',
                fontSize: 11, color: p === currentPage ? C.teal2 : C.textSecondary,
                background: p === currentPage ? 'rgba(90,200,208,0.09)' : 'transparent',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                borderLeft: p === currentPage ? `2px solid ${C.teal2}` : '2px solid transparent',
                transition: 'background .1s',
              }}>
                <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 10, color: 'rgba(130,142,158,0.6)', minWidth: 24 }}>{p}</span>
                <span style={{ fontSize: 10, color: p === currentPage ? C.teal2 : 'rgba(148,160,176,0.5)' }}>Page {p}</span>
              </div>
            ))}
          </div>
        ) : toc.map((entry, i) => {
          const target = navTarget(entry);
          const active = isCurrent(entry);
          const indent = 12 + (entry.level - 1) * 10;
          return (
            <div
              key={entry.id || i}
              role="button"
              tabIndex={0}
              aria-label={`Go to: ${entry.title}`}
              onClick={() => target != null && onNavigate(target)}
              onKeyDown={e => e.key === 'Enter' && target != null && onNavigate(target)}
              style={{
                padding: `5px ${indent}px 5px ${indent}px`,
                cursor: target != null ? 'pointer' : 'default',
                fontSize: 11, lineHeight: 1.45,
                color: active ? C.teal1 : C.textSecondary,
                background: active ? C.accentBg : 'transparent',
                borderLeft: active ? `2px solid ${C.teal2}` : '2px solid transparent',
                transition: 'all .1s',
                fontWeight: entry.level <= 2 ? 600 : 400,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(90,200,208,0.05)'; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              title={entry.title}>
              {entry.level > 1 && (
                <span style={{ color: C.textDim, flexShrink: 0, fontSize: 9 }}>
                  {'›'.repeat(entry.level - 1)}
                </span>
              )}
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                {entry.title}
              </span>
              {isImageDoc && entry.page != null && (
                <span style={{ color: C.textDim, fontSize: 9, flexShrink: 0, marginLeft: 4 }}>
                  {entry.page}
                </span>
              )}
            </div>
          );
        })}
      </div>
      {!loading && toc.length > 0 && (
        <div style={{ padding: '6px 12px', borderTop: `1px solid ${C.border}`, fontSize: 9, color: C.textDim }}>
          {toc.length} section{toc.length !== 1 ? 's' : ''}
          {isImageDoc ? ' · click to jump' : ' · click to jump to chunk'}
        </div>
      )}
    </div>
  );
}
