const { useState, useRef, useEffect } = React;

export function SearchPanel({ session, onClose, onNavigate, onQueryChange, onActiveChange, onResultsChange }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  useEffect(() => {
    onQueryChange?.(query.trim());
    if (!query.trim() || !session) { setResults([]); onActiveChange?.(0); onResultsChange?.([]); return; }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await window.SecureDocAPI.searchDocument(
          session.link_token, query, session.session_id
        );
        const found = data.results || [];
        setResults(found);
        setCurrentIdx(0);
        onActiveChange?.(0);
        onResultsChange?.(found);
        if (found.length > 0) onNavigate(found[0].page);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [query, session?.link_token, session?.session_id]);

  const goTo = (idx, rs) => { const r = (rs || results)[idx]; if (r) { onNavigate(r.page); onActiveChange?.(idx); } };
  const goNext = () => {
    const next = (currentIdx + 1) % Math.max(1, results.length);
    setCurrentIdx(next); goTo(next);
  };
  const goPrev = () => {
    const prev = (currentIdx - 1 + Math.max(1, results.length)) % Math.max(1, results.length);
    setCurrentIdx(prev); goTo(prev);
  };

  const iBtn = {
    background: 'none', border: 'none', cursor: 'pointer', padding: '3px 5px',
    color: 'rgba(148,160,176,0.8)', borderRadius: 4, lineHeight: 1,
    transition: 'color .1s, background .1s', fontSize: 12,
  };

  return (
    <div style={{
      position: 'fixed', top: 56, right: 16, zIndex: 600,
      background: 'rgba(14,18,28,0.9)',
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      border: '1px solid rgba(90,200,208,0.22)',
      borderRadius: 10, padding: '10px 12px', width: 340,
      boxShadow: '0 8px 40px rgba(0,0,0,0.7), 0 0 0 1px rgba(90,200,208,0.08)',
      display: 'flex', flexDirection: 'column', gap: 0,
    }}>
      {/* Input row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ flexShrink: 0, color: '#5ac8d0', opacity: 0.8 }}>
          <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.4" fill="none"/>
          <line x1="8.8" y1="8.8" x2="12" y2="12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') { e.preventDefault(); e.shiftKey ? goPrev() : goNext(); }
            if (e.key === 'Escape') onClose();
          }}
          placeholder="Search entire document…"
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            fontSize: 12.5, color: 'rgba(220,228,238,0.95)',
            fontFamily: "'DM Sans',sans-serif", letterSpacing: '0.01em',
          }}
        />
        <span style={{
          fontFamily: 'ui-monospace,monospace', fontSize: 10,
          color: loading ? '#5ac8d0' : results.length > 0 ? 'rgba(148,160,176,0.85)' : query.trim() ? 'rgba(200,80,80,0.8)' : 'transparent',
          flexShrink: 0, minWidth: 32, textAlign: 'right',
        }}>
          {loading ? '…' : results.length > 0 ? `${currentIdx + 1}/${results.length}` : query.trim() ? '0' : ''}
        </span>
        <div style={{ display: 'flex', gap: 1, borderLeft: '1px solid rgba(255,255,255,0.07)', paddingLeft: 6, marginLeft: 2 }}>
          <button onClick={goPrev} disabled={results.length === 0} title="Previous (Shift+Enter)" style={iBtn}>↑</button>
          <button onClick={goNext} disabled={results.length === 0} title="Next (Enter)" style={iBtn}>↓</button>
          <button onClick={onClose} title="Close (Esc)" style={{ ...iBtn, fontSize: 13 }}>✕</button>
        </div>
      </div>

      {/* Divider + results */}
      {results.length > 0 && (
        <>
          <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '8px -12px' }} />
          <div style={{ maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2, margin: '0 -2px' }}>
            {results.slice(0, 50).map((r, i) => {
              const isActive = i === currentIdx;
              return (
                <div key={i}
                  onClick={() => { setCurrentIdx(i); onNavigate(r.page); }}
                  style={{
                    fontFamily: 'ui-monospace,monospace', fontSize: 10.5,
                    color: isActive ? 'rgba(220,228,238,0.95)' : 'rgba(148,160,176,0.85)',
                    background: isActive ? 'rgba(90,200,208,0.12)' : 'transparent',
                    borderRadius: 5, padding: '5px 8px', lineHeight: 1.55,
                    cursor: 'pointer', transition: 'background .1s',
                    border: isActive ? '1px solid rgba(90,200,208,0.2)' : '1px solid transparent',
                  }}>
                  <span style={{ color: '#5ac8d0', fontWeight: 700, marginRight: 5 }}>p.{r.page}</span>
                  {r.snippet}
                </div>
              );
            })}
          </div>
          {results.length > 50 && (
            <div style={{ fontSize: 9.5, color: 'rgba(100,112,128,0.7)', textAlign: 'center', paddingTop: 6, fontFamily: "'DM Sans',sans-serif" }}>
              Showing 50 of {results.length} results
            </div>
          )}
        </>
      )}

      {!loading && query.trim() && results.length === 0 && (
        <div style={{ fontSize: 11, color: 'rgba(148,160,176,0.6)', padding: '8px 2px 2px', fontFamily: "'DM Sans',sans-serif" }}>
          No matches found
        </div>
      )}
    </div>
  );
}
