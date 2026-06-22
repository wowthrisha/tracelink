export function LinksPanel({ page, pageLinksRef, visitedLinks, onVisit, onClose, C, mono }) {
  const links = pageLinksRef.current[page] || [];
  const visitedCount = links.filter(l => visitedLinks.has(l.url)).length;

  const toggleVisit = url => {
    const next = new Set(visitedLinks);
    if (next.has(url)) next.delete(url); else next.add(url);
    onVisit(next);
  };

  return (
    <div style={{
      position: 'fixed', top: 56, right: 0,
      width: 'clamp(240px, 30vw, 400px)',
      height: 'calc(100vh - 56px)',
      background: 'rgba(9,13,19,0.96)',
      backdropFilter: 'blur(28px)', WebkitBackdropFilter: 'blur(28px)',
      borderLeft: '1px solid rgba(90,200,208,0.18)',
      display: 'flex', flexDirection: 'column',
      zIndex: 505, boxShadow: '-8px 0 40px rgba(0,0,0,0.55)',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
      }}>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
          <path d="M4.5 7.5l3-3M7 3.5l1.5-1.5a2.12 2.12 0 013 3L10 6.5M5 8.5l-1.5 1.5a2.12 2.12 0 01-3-3L2 5.5" stroke="#5ac8d0" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'rgba(220,228,238,0.9)', flex: 1 }}>
          Links — Page {page}
        </span>
        {links.length > 0 && (
          <span style={{ ...mono, fontSize: 9, color: 'rgba(130,142,158,0.6)' }}>
            {visitedCount}/{links.length} visited
          </span>
        )}
        <button onClick={onClose} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'rgba(148,160,176,0.6)', fontSize: 14, padding: '0 2px',
          lineHeight: 1, marginLeft: 4, fontFamily: 'inherit',
        }}>✕</button>
      </div>

      {/* Links list */}
      {links.length === 0 ? (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 8, padding: 24,
        }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" opacity=".25">
            <path d="M9 17H5a4 4 0 010-8h4M15 7h4a4 4 0 010 8h-4M8 12h8" stroke="#5ac8d0" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <div style={{ ...mono, fontSize: 10, color: 'rgba(130,142,158,0.45)', textAlign: 'center' }}>
            No links found on this page
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
          {links.map((link, i) => {
            const visited = visitedLinks.has(link.url);
            const safeUrl = (() => { try { const u = new URL(link.url); return /^https?:$/i.test(u.protocol) ? link.url : null; } catch { return null; } })();
            const domain = safeUrl ? new URL(safeUrl).hostname : '(invalid URL)';
            return (
              <div key={i} style={{
                padding: '7px 12px',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
                display: 'flex', alignItems: 'center', gap: 8,
                background: visited ? 'rgba(90,200,208,0.03)' : 'transparent',
                transition: 'background .15s',
              }}>
                <input
                  type="checkbox"
                  checked={visited}
                  onChange={() => toggleVisit(link.url)}
                  style={{ flexShrink: 0, cursor: 'pointer', accentColor: '#5ac8d0', width: 13, height: 13 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <a
                    href={safeUrl || '#'}
                    target={safeUrl ? '_blank' : undefined}
                    rel="noopener noreferrer"
                    onClick={safeUrl ? () => { const next = new Set(visitedLinks); next.add(link.url); onVisit(next); } : e => e.preventDefault()}
                    style={{
                      display: 'block', fontSize: 11, fontWeight: 500, lineHeight: 1.35,
                      color: visited ? 'rgba(90,200,208,0.45)' : '#5ac8d0',
                      textDecoration: visited ? 'line-through' : 'none',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}
                    title={link.url}
                  >
                    {domain}
                  </a>
                  {link.label && (
                    <div style={{
                      fontSize: 9, color: 'rgba(130,142,158,0.5)', marginTop: 1,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {link.label}
                    </div>
                  )}
                </div>
                <span style={{
                  ...mono, flexShrink: 0, fontSize: 8, letterSpacing: '0.3px',
                  padding: '1px 5px', borderRadius: 3,
                  color: link.type === 'annotation' ? 'rgba(90,200,208,0.55)' : 'rgba(148,160,176,0.45)',
                  background: link.type === 'annotation' ? 'rgba(90,200,208,0.08)' : 'rgba(148,160,176,0.06)',
                  border: `1px solid ${link.type === 'annotation' ? 'rgba(90,200,208,0.15)' : 'rgba(148,160,176,0.1)'}`,
                }}>
                  {link.type === 'annotation' ? 'PDF' : 'text'}{visited ? ' ✓' : ''}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer hint */}
      {links.length > 0 && (
        <div style={{
          padding: '8px 14px', borderTop: '1px solid rgba(255,255,255,0.05)',
          ...mono, fontSize: 9, color: 'rgba(130,142,158,0.35)', flexShrink: 0,
        }}>
          Check links you have reviewed. Updates as you change pages.
        </div>
      )}
    </div>
  );
}
