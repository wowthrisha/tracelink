const { useState } = React;

const ANNOT_COLORS = ['#FFE066', '#FF6B6B', '#5ac8d0', '#7BC67A', '#B794F4', '#F6AD55', '#FC8181', '#63B3ED'];
const ANNOT_TOOLS = [
  { tool: 'highlight', label: 'Highlight', icon: <svg width="14" height="12" viewBox="0 0 14 12" fill="none"><rect x="0" y="4" width="14" height="5" rx="1.5" fill="#FFE066" opacity="0.75"/><path d="M2 9.5l1.5-6h7l1.5 6" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5"/></svg> },
  { tool: 'draw', label: 'Draw', icon: <svg width="14" height="12" viewBox="0 0 14 12" fill="none"><path d="M1 10 Q3 3 7 6 Q11 9 13 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.9"/></svg> },
  { tool: 'comment', label: 'Comment', icon: <svg width="14" height="12" viewBox="0 0 14 12" fill="none"><path d="M1 1h12v8H7l-3 2V9H1V1z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></svg> },
  { tool: 'sticky_note', label: 'Sticky Note', icon: <svg width="14" height="12" viewBox="0 0 14 12" fill="none"><rect x="1" y="1" width="12" height="10" rx="1.5" fill="#FFE066" opacity="0.25" stroke="#FFE066" strokeWidth="1.2"/><path d="M4 4h6M4 6.5h4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.6"/></svg> },
  { tool: 'rectangle', label: 'Rectangle', icon: <svg width="14" height="12" viewBox="0 0 14 12" fill="none"><rect x="1.5" y="1.5" width="11" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/></svg> },
  { tool: 'arrow', label: 'Arrow', icon: <svg width="14" height="12" viewBox="0 0 14 12" fill="none"><path d="M1 6h11M9 3l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg> },
];

function AnnotToolbar({ btn, on, sep, mono, annotTool, setAnnotTool, annotColor, setAnnotColor, annotThickness, setAnnotThickness, annotUndoStack, onAnnotUndo, bookmarked, onToggleBookmark }) {
  const [showFlyout, setShowFlyout] = useState(false);
  return (<>
    {sep}
    <button onClick={onToggleBookmark} title={bookmarked ? 'Remove bookmark' : 'Bookmark page'}
      aria-label={bookmarked ? 'Remove bookmark from this page' : 'Bookmark this page'} aria-pressed={bookmarked}
      style={{ ...btn, ...(bookmarked ? { color: '#FFE066', opacity: 1 } : {}), padding: '3px 7px' }}>
      <svg width="10" height="13" viewBox="0 0 10 13" fill={bookmarked ? '#FFE066' : 'none'} style={{ flexShrink: 0 }} aria-hidden="true">
        <path d="M1 1h8v11l-4-3-4 3V1z" stroke={bookmarked ? '#FFE066' : 'currentColor'} strokeWidth="1.3" strokeLinejoin="round"/>
      </svg>
    </button>
    <div style={{ position: 'relative', flexShrink: 0 }}>
      <button
        onClick={() => setShowFlyout(v => !v)}
        title="Annotation tools"
        aria-label="Open annotation tools"
        aria-expanded={showFlyout}
        aria-haspopup="true"
        style={{ ...btn, padding: '3px 7px', ...(annotTool || showFlyout ? on : {}) }}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
          <path d="M8.5 1.5L10.5 3.5L4 10H2V8L8.5 1.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" fill="none"/>
          <path d="M7 3L9 5" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
        </svg>
        {annotTool && <span style={{ ...mono, fontSize: 8, marginLeft: 2, color: '#5ac8d0' }}>●</span>}
      </button>
      {showFlyout && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, zIndex: 200, marginTop: 4,
          background: '#10161d', border: '1px solid rgba(90,200,208,0.18)', borderRadius: 8,
          padding: 10, minWidth: 180, boxShadow: '0 8px 32px rgba(0,0,0,0.55)',
          display: 'flex', flexDirection: 'column', gap: 4,
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.7px', textTransform: 'uppercase', color: 'rgba(90,200,208,0.5)', marginBottom: 4, paddingBottom: 4, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Tools</div>
          {ANNOT_TOOLS.map(({ tool, label, icon }) => (
            <button key={tool}
              onClick={() => setAnnotTool(t => t === tool ? null : tool)}
              aria-label={annotTool === tool ? `Deactivate ${label} tool` : `Activate ${label} tool`}
              aria-pressed={annotTool === tool}
              style={{ ...btn, borderRadius: 5, padding: '4px 8px', justifyContent: 'flex-start', gap: 8, width: '100%', ...(annotTool === tool ? on : {}) }}
            >
              {icon}
              <span style={{ fontSize: 11 }}>{label}</span>
              {annotTool === tool && <span style={{ marginLeft: 'auto', fontSize: 9, color: '#5ac8d0' }} aria-hidden="true">active</span>}
            </button>
          ))}
          <div style={{ fontSize: 9, letterSpacing: '0.7px', textTransform: 'uppercase', color: 'rgba(90,200,208,0.5)', marginTop: 6, marginBottom: 4, paddingTop: 4, borderTop: '1px solid rgba(255,255,255,0.06)' }}>Color</div>
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }} role="group" aria-label="Annotation color">
            {ANNOT_COLORS.map(c => (
              <button key={c} onClick={() => setAnnotColor(c)}
                aria-label={`Set annotation color to ${c}`} aria-pressed={annotColor === c}
                style={{ width: 18, height: 18, borderRadius: '50%', background: c, cursor: 'pointer', border: annotColor === c ? '2px solid #fff' : '2px solid transparent', flexShrink: 0, transition: 'border .1s', padding: 0 }}
              />
            ))}
          </div>
          <div style={{ fontSize: 9, letterSpacing: '0.7px', textTransform: 'uppercase', color: 'rgba(90,200,208,0.5)', marginTop: 6, marginBottom: 4, paddingTop: 4, borderTop: '1px solid rgba(255,255,255,0.06)' }}>Thickness</div>
          <div style={{ display: 'flex', gap: 5 }} role="group" aria-label="Stroke thickness">
            {[1, 2, 4, 6].map(t => (
              <button key={t} onClick={() => setAnnotThickness(t)}
                aria-label={`Thickness ${t}px`} aria-pressed={annotThickness === t}
                style={{ ...btn, borderRadius: 4, padding: '3px 8px', ...(annotThickness === t ? on : {}) }}>
                <div style={{ width: 20, height: t, background: 'currentColor', borderRadius: 1 }} aria-hidden="true"/>
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 5, marginTop: 6, paddingTop: 4, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <button onClick={onAnnotUndo} disabled={annotUndoStack.length === 0}
              style={{ ...btn, flex: 1, justifyContent: 'center', borderRadius: 5, opacity: annotUndoStack.length === 0 ? 0.3 : 1 }}
              title="Undo last annotation">
              <svg width="12" height="10" viewBox="0 0 12 10" fill="none"><path d="M1 5h7a3 3 0 010 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><path d="M1 5L4 2M1 5l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
              <span style={{ fontSize: 10, marginLeft: 4 }}>Undo</span>
            </button>
          </div>
        </div>
      )}
    </div>
  </>);
}

export function ViewerToolbar({
  doc, docName, isTextDoc,
  page, PAGE_COUNT, pageInputStr, setPageInputStr, setPage,
  goPrev, goNext,
  layoutMode, customZoom, _zoomBy, _zoomTo, _setLayout,
  LAYOUT, ZOOM_STEP, ZOOM_PRESETS,
  showLaser, setShowLaser, showMagnifier, setShowMagnifier,
  showInsights, setShowInsights, hasInsights,
  showLinks, setShowLinks, linksCount,
  isFullscreen, toggleFullscreen,
  showToc, setShowToc, showSearch, setShowSearch, showInfo, setShowInfo,
  showPageList, setShowPageList,
  canDownload, canPrint, canInfo, canAnnotate, onDownload, onPrint,
  annotTool, setAnnotTool, annotColor, setAnnotColor, annotThickness, setAnnotThickness,
  annotUndoStack, onAnnotUndo,
  bookmarked, onToggleBookmark,
  rotation, onRotate, isTwoPage, onToggleTwoPage,
  onBack,
  C, mono,
}) {
  const btn = {
    background: 'none', border: 'none', cursor: 'pointer',
    color: 'rgba(148,160,176,0.85)', borderRadius: 4, padding: '3px 7px',
    fontSize: 11, lineHeight: '16px', transition: 'color .1s, background .1s',
    display: 'flex', alignItems: 'center', gap: 3, whiteSpace: 'nowrap',
    fontFamily: "'DM Sans', sans-serif", flexShrink: 0,
  };
  const on = { background: 'rgba(90,200,208,0.12)', color: '#5ac8d0' };
  const sep = <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.07)', margin: '0 2px', flexShrink: 0 }} />;

  const groupName = doc?.group_name || 'General';
  const groupColor = doc?.group_color || '#6b7280';

  const commitPage = () => {
    const p = parseInt(pageInputStr, 10);
    if (!isNaN(p) && p >= 1 && p <= PAGE_COUNT) setPage(p);
    setPageInputStr('');
  };

  return (
    <div data-viewer-toolbar style={{
      height: 42, background: '#10151d',
      borderBottom: '1px solid rgba(255,255,255,0.055)',
      display: 'flex', alignItems: 'center', padding: '0 8px',
      flexShrink: 0, userSelect: 'none', gap: 0, zIndex: 50,
      boxShadow: '0 1px 0 rgba(0,0,0,0.35)',
    }}>

      {/* ── FAR LEFT: back to documents ── */}
      {onBack && (
        <button onClick={onBack} title="Back to Documents"
          style={{ ...btn, paddingRight: 10, marginRight: 2, borderRight: '1px solid rgba(255,255,255,0.07)' }}>
          <svg width="12" height="10" viewBox="0 0 12 10" fill="none" style={{ flexShrink: 0 }}>
            <path d="M5 1L1 5l4 4M1 5h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span style={{ fontSize: 10, letterSpacing: '0.4px' }}>Docs</span>
        </button>
      )}

      {/* ── LEFT: sidebar toggles ── */}
      <button onClick={() => setShowToc(v => !v)} title="Table of Contents"
        style={{ ...btn, ...(showToc ? on : {}) }}>
        <svg width="13" height="10" viewBox="0 0 13 10" fill="none" style={{ flexShrink: 0 }}>
          <rect x="0" y="0" width="3" height="2" rx="0.5" fill="currentColor" opacity=".7"/>
          <rect x="5" y="0" width="8" height="2" rx="0.5" fill="currentColor"/>
          <rect x="0" y="4" width="3" height="2" rx="0.5" fill="currentColor" opacity=".7"/>
          <rect x="5" y="4" width="8" height="2" rx="0.5" fill="currentColor"/>
          <rect x="0" y="8" width="3" height="2" rx="0.5" fill="currentColor" opacity=".7"/>
          <rect x="5" y="8" width="5" height="2" rx="0.5" fill="currentColor"/>
        </svg>
        <span className="toolbar-btn-label">TOC</span>
      </button>

      {!isTextDoc && (
        <button onClick={() => setShowPageList(v => !v)} title="Page list"
          style={{ ...btn, ...(showPageList ? on : {}) }}>
          <svg width="11" height="12" viewBox="0 0 11 12" fill="none" style={{ flexShrink: 0 }}>
            <rect x="1" y="0" width="9" height="11" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none"/>
            <rect x="3" y="3" width="5" height="1" rx="0.4" fill="currentColor"/>
            <rect x="3" y="5.5" width="5" height="1" rx="0.4" fill="currentColor"/>
            <rect x="3" y="8" width="3" height="1" rx="0.4" fill="currentColor"/>
          </svg>
          <span className="toolbar-btn-label">Pages</span>
        </button>
      )}

      <button onClick={() => setShowSearch(v => !v)} title="Search (Ctrl+F)"
        style={{ ...btn, ...(showSearch ? on : {}) }}>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
          <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.3" fill="none"/>
          <line x1="7.8" y1="7.8" x2="11" y2="11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
        </svg>
        <span className="toolbar-btn-label">Search</span>
      </button>

      {sep}

      {/* ── Doc breadcrumb: Group › Filename ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0, overflow: 'hidden', flexShrink: 1 }}>
        <span style={{
          fontSize: 10, padding: '1px 7px', borderRadius: 10,
          background: `${groupColor}1a`, color: groupColor,
          border: `1px solid ${groupColor}33`,
          fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: '0.02em',
          whiteSpace: 'nowrap', flexShrink: 0,
        }}>{groupName}</span>
        <svg width="5" height="9" viewBox="0 0 5 9" fill="none" style={{ flexShrink: 0, opacity: 0.35 }}>
          <path d="M1 1l3 3.5L1 8" stroke="rgba(180,190,200,1)" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span style={{
          fontSize: 11.5, fontWeight: 500, color: 'rgba(210,218,228,0.9)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          fontFamily: "'DM Sans',sans-serif",
        }} title={docName}>{docName || '—'}</span>
      </div>

      <div style={{ flex: 1, minWidth: 12 }} />

      {/* ── CENTER: page navigation ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
        <button onClick={goPrev} disabled={page <= 1} title="Previous (←)" aria-label="Previous page"
          style={{ ...btn, opacity: page <= 1 ? 0.25 : 1, padding: '3px 5px', fontSize: 15 }}>‹</button>
        <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.055)', borderRadius: 4, border: '1px solid rgba(255,255,255,0.09)', overflow: 'hidden' }}>
          <input
            type="text"
            value={pageInputStr !== '' ? pageInputStr : String(page)}
            onChange={e => setPageInputStr(e.target.value)}
            onFocus={e => { setPageInputStr(String(page)); e.target.select(); }}
            onBlur={commitPage}
            onKeyDown={e => {
              if (e.key === 'Enter') { commitPage(); e.target.blur(); }
              if (e.key === 'Escape') { setPageInputStr(''); e.target.blur(); }
            }}
            style={{
              ...mono, fontSize: 11, fontWeight: 700, color: 'rgba(220,228,238,1)',
              background: 'transparent', border: 'none',
              padding: '3px 0 3px 6px', textAlign: 'center', width: 28, outline: 'none',
            }}
          />
          <span style={{ ...mono, fontSize: 11, color: 'rgba(100,112,128,0.9)', padding: '0 6px 0 2px' }}>/ {PAGE_COUNT}</span>
        </div>
        <button onClick={goNext} disabled={page >= PAGE_COUNT} title="Next (→)" aria-label="Next page"
          style={{ ...btn, opacity: page >= PAGE_COUNT ? 0.25 : 1, padding: '3px 5px', fontSize: 15 }}>›</button>
      </div>

      {!isTextDoc && (<>
        {sep}
        {/* ── View group: zoom pill (W · H · − · zoom · +) + 2P + rotate ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 2, flexShrink: 0 }}>
          {/* Unified zoom control: AUTO | W | H | 100% | − | label | + */}
          <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.045)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 5, overflow: 'hidden', flexShrink: 0 }}>
            <button onClick={() => _setLayout(LAYOUT.AUTO)} title="Auto fit"
              style={{ ...btn, borderRadius: 0, padding: '3px 6px', fontSize: 9, fontWeight: 700, borderRight: '1px solid rgba(255,255,255,0.07)', ...(layoutMode === LAYOUT.AUTO ? on : {}) }}>
              AUTO
            </button>
            <button onClick={() => _setLayout(LAYOUT.FIT_WIDTH)} title="Fit to width"
              style={{ ...btn, borderRadius: 0, padding: '3px 6px', fontSize: 10, fontWeight: 700, borderRight: '1px solid rgba(255,255,255,0.07)', ...(layoutMode === LAYOUT.FIT_WIDTH ? on : {}) }}>
              W
            </button>
            <button onClick={() => _setLayout(LAYOUT.FIT_HEIGHT)} title="Fit to height"
              style={{ ...btn, borderRadius: 0, padding: '3px 6px', fontSize: 10, fontWeight: 700, borderRight: '1px solid rgba(255,255,255,0.07)', ...(layoutMode === LAYOUT.FIT_HEIGHT ? on : {}) }}>
              H
            </button>
            <button onClick={() => _setLayout(LAYOUT.ACTUAL)} title="Actual size (100%)"
              style={{ ...btn, borderRadius: 0, padding: '3px 5px', fontSize: 9, fontWeight: 700, borderRight: '1px solid rgba(255,255,255,0.07)', ...(layoutMode === LAYOUT.ACTUAL ? on : {}) }}>
              100%
            </button>
            <button onClick={() => _zoomBy(-ZOOM_STEP)} title="Zoom out" aria-label="Zoom out"
              style={{ ...btn, borderRadius: 0, padding: '3px 6px', fontSize: 14, borderRight: '1px solid rgba(255,255,255,0.07)' }}>−</button>
            <select
              value={layoutMode === LAYOUT.CUSTOM ? customZoom : layoutMode === LAYOUT.FIT_WIDTH ? 'fw' : layoutMode === LAYOUT.FIT_HEIGHT ? 'fh' : layoutMode === LAYOUT.AUTO ? 'auto' : layoutMode === LAYOUT.ACTUAL ? 'actual' : customZoom}
              onChange={e => {
                const v = e.target.value;
                if (v === 'auto') _setLayout(LAYOUT.AUTO);
                else if (v === 'fw') _setLayout(LAYOUT.FIT_WIDTH);
                else if (v === 'fh') _setLayout(LAYOUT.FIT_HEIGHT);
                else if (v === 'actual') _setLayout(LAYOUT.ACTUAL);
                else _zoomTo(parseInt(v, 10));
              }}
              title="Zoom level"
              style={{
                ...mono, fontSize: 10, color: 'rgba(165,175,188,0.9)',
                background: 'transparent', border: 'none',
                padding: '3px 2px', cursor: 'pointer',
                width: 42, textAlign: 'center', appearance: 'none', WebkitAppearance: 'none', outline: 'none',
              }}>
              {ZOOM_PRESETS.map(p => <option key={p} value={p}>{p}%</option>)}
              {layoutMode === LAYOUT.CUSTOM && !ZOOM_PRESETS.includes(customZoom) && (
                <option value={customZoom}>{customZoom}%</option>
              )}
              {layoutMode === LAYOUT.AUTO && <option value="auto">AUTO</option>}
              {layoutMode === LAYOUT.FIT_WIDTH && <option value="fw">W</option>}
              {layoutMode === LAYOUT.FIT_HEIGHT && <option value="fh">H</option>}
              {layoutMode === LAYOUT.ACTUAL && <option value="actual">100%</option>}
            </select>
            <button onClick={() => _zoomBy(ZOOM_STEP)} title="Zoom in" aria-label="Zoom in"
              style={{ ...btn, borderRadius: 0, padding: '3px 6px', fontSize: 14, borderLeft: '1px solid rgba(255,255,255,0.07)' }}>+</button>
          </div>

          {/* Two-page toggle */}
          <button onClick={PAGE_COUNT > 1 ? onToggleTwoPage : undefined}
            disabled={PAGE_COUNT <= 1}
            title={PAGE_COUNT <= 1 ? 'Two-page view requires more than one page' : 'Two-page view'}
            style={{ ...btn, ...(isTwoPage ? on : {}), padding: '3px 8px', marginLeft: 2, ...(PAGE_COUNT <= 1 ? { opacity: 0.35, cursor: 'not-allowed' } : {}) }}>
            <svg width="15" height="11" viewBox="0 0 15 11" fill="none" style={{ flexShrink: 0 }}>
              <rect x="0.5" y="0.5" width="6" height="10" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none"/>
              <rect x="8.5" y="0.5" width="6" height="10" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none"/>
            </svg>
            <span className="toolbar-btn-label" style={{ marginLeft: 3 }}>2P</span>
          </button>

          {/* Rotate */}
          <button onClick={onRotate} title={`Rotate clockwise (${rotation}°)`}
            style={{ ...btn, ...(rotation !== 0 ? on : {}), padding: '3px 7px' }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
              <path d="M9.5 2.5A5 5 0 1 0 11 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" fill="none"/>
              <path d="M11 2.5h-2v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {rotation !== 0 && <span style={{ ...mono, fontSize: 9, marginLeft: 2 }}>{rotation}°</span>}
          </button>
        </div>

        {sep}

        {/* ── Tools: magnifier + laser (icon only) ── */}
        <button onClick={() => { setShowMagnifier(v => !v); if (showLaser) setShowLaser(false); }}
          title="Magnifier" aria-label={showMagnifier ? 'Hide magnifier' : 'Show magnifier'} aria-pressed={showMagnifier}
          style={{ ...btn, ...(showMagnifier ? on : {}), padding: '3px 7px' }}>
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.3" fill="none"/>
            <line x1="8.8" y1="8.8" x2="12" y2="12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="3.5" y1="5.5" x2="7.5" y2="5.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity=".6"/>
            <line x1="5.5" y1="3.5" x2="5.5" y2="7.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity=".6"/>
          </svg>
        </button>
        <button onClick={() => { setShowLaser(v => !v); if (showMagnifier) setShowMagnifier(false); }}
          title="Laser pointer" aria-label={showLaser ? 'Turn off laser pointer' : 'Turn on laser pointer'} aria-pressed={showLaser}
          style={{ ...btn, ...(showLaser ? { ...on, color: '#ff4444' } : {}), padding: '3px 7px' }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="6" cy="6" r="3" fill={showLaser ? '#ff4444' : 'currentColor'} opacity={showLaser ? 1 : 0.7}/>
            <circle cx="6" cy="6" r="5" stroke={showLaser ? '#ff4444' : 'currentColor'} strokeWidth="1" fill="none" opacity="0.4"/>
          </svg>
        </button>
      </>)}

      <div style={{ flex: 1, minWidth: 8 }} />

      {/* ── RIGHT: info + actions (icon only, with tooltips) ── */}
      {!isTextDoc && (
        <button onClick={() => setShowLinks(v => !v)} title="Links on this page"
          aria-label={showLinks ? 'Hide links panel' : 'Show links on this page'} aria-pressed={showLinks}
          style={{ ...btn, ...(showLinks ? on : {}), padding: '3px 8px', position: 'relative' }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
            <path d="M4.5 7.5l3-3M7 3.5l1.5-1.5a2.12 2.12 0 013 3L10 6.5M5 8.5l-1.5 1.5a2.12 2.12 0 01-3-3L2 5.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="toolbar-btn-label">Links</span>
          {linksCount > 0 && (
            <span style={{
              position: 'absolute', top: 2, right: 2,
              background: '#5ac8d0', color: '#060809',
              borderRadius: 8, fontSize: 8, fontWeight: 700,
              padding: '0 3px', lineHeight: '11px', minWidth: 11, textAlign: 'center',
            }}>{linksCount}</span>
          )}
        </button>
      )}
      {hasInsights && (
        <button onClick={() => setShowInsights(v => !v)} title="Page insights"
          aria-label={showInsights ? 'Hide page insights' : 'Show page insights'} aria-pressed={showInsights}
          style={{ ...btn, ...(showInsights ? on : {}), padding: '3px 8px' }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
            <rect x="1" y="7" width="2" height="4" rx="0.5" fill="currentColor" opacity=".9"/>
            <rect x="5" y="4" width="2" height="7" rx="0.5" fill="currentColor" opacity=".9"/>
            <rect x="9" y="1" width="2" height="10" rx="0.5" fill="currentColor" opacity=".9"/>
          </svg>
          <span className="toolbar-btn-label">Insights</span>
        </button>
      )}
      {sep}
      <button onClick={toggleFullscreen} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
        style={{ ...btn, padding: '3px 7px' }}>
        {isFullscreen
          ? <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M4 1H1v3M8 1h3v3M4 11H1V8M8 11h3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
          : <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M1 4V1h3M8 1h3v3M11 8v3H8M4 11H1V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
        }
      </button>
      {/* ── Annotation tools — only when can_annotate is on ── */}
      {canAnnotate && (
        <AnnotToolbar
          btn={btn} on={on} sep={sep} mono={mono}
          annotTool={annotTool} setAnnotTool={setAnnotTool}
          annotColor={annotColor} setAnnotColor={setAnnotColor}
          annotThickness={annotThickness} setAnnotThickness={setAnnotThickness}
          annotUndoStack={annotUndoStack} onAnnotUndo={onAnnotUndo}
          bookmarked={bookmarked} onToggleBookmark={onToggleBookmark}
        />
      )}
      {sep}
      {/* BUG-005: native `disabled` removes these from the Tab order entirely,
          so keyboard/screen-reader users could never reach them to hear the
          aria-label explaining why the action is blocked — and either way,
          clicking (or Enter/Space on a disabled button, which never even
          fires) gave no feedback. Using aria-disabled instead of disabled
          keeps the button focusable and clickable — still visually inert via
          the same dimmed opacity plus a not-allowed cursor — so onDownload/
          onPrint (which now show an explanatory toast when blocked, see
          ViewerScreen.jsx) actually run for every input method. */}
      <button onClick={onDownload} aria-disabled={!canDownload} title={canDownload ? 'Download document' : 'Download not allowed'} aria-label={canDownload ? 'Download document' : 'Download not permitted'} style={{ ...btn, opacity: canDownload ? 1 : 0.28, cursor: canDownload ? 'pointer' : 'not-allowed', padding: '3px 7px' }}>
        <svg width="11" height="12" viewBox="0 0 11 12" fill="none" style={{ flexShrink: 0 }}>
          <path d="M5.5 1v7M2.5 5.5l3 3 3-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M1 10h9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
        </svg>
      </button>
      <button onClick={onPrint} aria-disabled={!canPrint} title={canPrint ? 'Print document' : 'Print not allowed'} aria-label={canPrint ? 'Print document' : 'Print not permitted'} style={{ ...btn, opacity: canPrint ? 1 : 0.28, cursor: canPrint ? 'pointer' : 'not-allowed', padding: '3px 7px' }}>
        <svg width="12" height="11" viewBox="0 0 12 11" fill="none" style={{ flexShrink: 0 }}>
          <rect x="2" y="4" width="8" height="5" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none"/>
          <path d="M3 4V2h6v2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          <rect x="3.5" y="6" width="5" height="1" rx="0.4" fill="currentColor" opacity=".7"/>
          <rect x="3.5" y="7.8" width="3" height="1" rx="0.4" fill="currentColor" opacity=".7"/>
        </svg>
      </button>
      {canInfo && (
        <button onClick={() => setShowInfo(v => !v)} title="Document info" style={{ ...btn, ...(showInfo ? on : {}), padding: '3px 7px' }}>
          <svg width="11" height="13" viewBox="0 0 11 13" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="5.5" cy="3" r="1.2" fill="currentColor"/>
            <rect x="4.5" y="6" width="2" height="5" rx="0.8" fill="currentColor"/>
          </svg>
        </button>
      )}
    </div>
  );
}
