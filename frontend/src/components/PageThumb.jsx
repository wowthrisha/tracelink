import { C, mono } from '../constants/tokens.js';

const { useState, useRef, useEffect } = React;

// Thumbnail fetch semaphore — limits concurrent HTTP requests to backend.
// Without throttling, the sidebar mounts all PAGE_COUNT PageThumb components
// simultaneously, firing every thumbnail request at once. For a 60-page document
// that is 60 simultaneous HTTP requests — even with the browser's 6-conn/domain
// limit that is 10 sequential rounds that hammer the backend connection pool.
//
// Queue slot is released only after the browser has fully loaded (or errored on)
// the image, not just when the HTTP request fires.
const _THUMB_CONCURRENCY = 6;
const _thumbQueue = (() => {
  let running = 0;
  const pending = [];
  function drain() {
    while (running < _THUMB_CONCURRENCY && pending.length > 0) {
      const { resolve } = pending.shift();
      running++;
      resolve(() => { running--; drain(); });
    }
  }
  return { acquire: () => new Promise(resolve => { pending.push({ resolve }); drain(); }) };
})();

export function PageThumb({ p, active, onClick, token, sessionId, docReady }) {
  const [hov, setHov] = useState(false);
  const [thumbSrc, setThumbSrc] = useState(null);
  const [thumbError, setThumbError] = useState(false);
  const containerRef = useRef(null);

  // IntersectionObserver lazy loading — thumbnails only enter the semaphore
  // queue when scrolled into the visible area of the sidebar.
  useEffect(() => {
    if (!token || !sessionId || !docReady) return;
    let cancelled = false;
    let observer = null;

    const startLoad = () => {
      if (cancelled || thumbSrc) return;
      setThumbError(false);

      _thumbQueue.acquire().then(release => {
        if (cancelled) { release(); return; }
        const url = window.SecureDocAPI.getThumbUrl(token, p);
        fetch(url, { headers: window.SecureDocAPI.sessionHeaders(sessionId) })
          .then(r => r.ok ? r.blob() : Promise.reject())
          .then(blob => {
            if (!cancelled) setThumbSrc(URL.createObjectURL(blob));
            release();
          })
          .catch(() => { if (!cancelled) setThumbError(true); release(); });
      }).catch(() => {});
    };

    if (typeof IntersectionObserver !== 'undefined' && containerRef.current) {
      observer = new IntersectionObserver(
        entries => { if (entries[0].isIntersecting) { startLoad(); observer.disconnect(); } },
        { rootMargin: '200px' }
      );
      observer.observe(containerRef.current);
    } else {
      startLoad();
    }

    return () => {
      cancelled = true;
      if (observer) observer.disconnect();
    };
  }, [token, sessionId, p, docReady]);

  const showImg = thumbSrc && !thumbError;

  return (
    <div ref={containerRef} onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        width: '100%', aspectRatio: '8.5/11', background: C.surface2,
        border: `1px solid ${active ? C.teal2 : hov ? C.borderMed : C.border}`,
        borderRadius: 4, cursor: 'pointer', position: 'relative', overflow: 'hidden',
        transition: 'border-color .1s', flexShrink: 0
      }}>
      {showImg ? (
        <img
          src={thumbSrc}
          draggable={false}
          onError={() => setThumbError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', pointerEvents: 'none' }}
          alt={`Page ${p}`}
        />
      ) : (
        <div style={{ position: 'absolute', inset: '5px 4px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {[65, 80, 55, 75, 60, 50, 70, 58, 48].map((w, i) => (
            <div key={i} style={{
              height: i === 0 ? 3 : 1.5, width: `${w + (p * 7 + i * 3) % 20}%`,
              background: active ? 'rgba(90,200,208,0.3)' : 'rgba(176,196,200,0.15)',
              borderRadius: 1
            }} />
          ))}
        </div>
      )}
      <div style={{
        ...mono, fontSize: 7, color: active ? C.teal2 : C.textDim,
        position: 'absolute', bottom: 2, right: 3
      }}>{p}</div>
    </div>
  );
}
