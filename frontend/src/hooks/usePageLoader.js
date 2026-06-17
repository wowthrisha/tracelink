// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useCallback, useEffect } = React;

/**
 * Manages page image loading, blob URL caching, inflight request deduplication,
 * crossfade transitions, two-page spread loading, and background prefetching.
 *
 * All heavy fetch logic lives here. ViewerScreen receives only the display-ready
 * state values and DOM refs.
 *
 * @param {object}      opts
 * @param {object|null} opts.session     - Validated viewer session object.
 * @param {number}      opts.page        - Current page number.
 * @param {boolean}     opts.twoPageMode - Whether two-page spread is active.
 * @param {boolean}     opts.isTextDoc   - True for txt/md/log; skips image loading.
 * @param {Function}    [opts.onAuth401] - Called when any page fetch returns 401.
 *   ViewerScreen passes `() => reinitRef.current?.()`. Stored in a ref internally
 *   so it does not need to be stable across renders.
 */
export function usePageLoader({ session, page, twoPageMode, isTextDoc, onAuth401 }) {
  const [imgSrc, setImgSrc] = useState('');
  const [imgLoading, setImgLoading] = useState(false);
  const [pageError, setPageError] = useState(null);
  // Phase 7: smooth transitions — keep prev image visible while next loads
  const [prevImgSrc, setPrevImgSrc] = useState('');
  const [imgReady, setImgReady] = useState(false);
  // Two-page view: second page image
  const [imgSrc2, setImgSrc2] = useState('');
  const [imgLoading2, setImgLoading2] = useState(false);
  const [page2Error, setPage2Error] = useState(null);
  const [pageAspectRatio, setPageAspectRatio] = useState(null);

  const pageImgRef = useRef(null);
  const pageContainerRef = useRef(null);
  // Phase 7: request deduplication — one inflight fetch per page key
  const inflightRef = useRef(new Map());
  // Tracks the currently displayed imgSrc so loadPage (empty-deps callback)
  // can capture it for the crossfade background without a stale closure.
  const imgSrcRef = useRef('');
  // Blob URL cache — token:page → blobUrl (capped at MAX_CACHED_PAGES)
  const pageCache = useRef(new Map());

  // Stable ref for the 401 callback — never appears in effect deps.
  const _onAuth401Ref = useRef(onAuth401);
  useEffect(() => { _onAuth401Ref.current = onAuth401; });

  const MAX_CACHED_PAGES = 30;

  const _cacheSet = useCallback((key, blobUrl) => {
    pageCache.current.set(key, blobUrl);
    if (pageCache.current.size > MAX_CACHED_PAGES) {
      // Evict the oldest entry (insertion order) and free its memory
      const firstKey = pageCache.current.keys().next().value;
      const evicted = pageCache.current.get(firstKey);
      URL.revokeObjectURL(evicted);
      pageCache.current.delete(firstKey);
    }
  }, []);

  // Revoke all blob URLs when the viewer unmounts or the session ends
  const _clearPageCache = useCallback(() => {
    for (const url of pageCache.current.values()) {
      URL.revokeObjectURL(url);
    }
    pageCache.current.clear();
  }, []);

  const loadPage = useCallback(async (token, pageNum, sessionId) => {
    if (!token || !sessionId) {
      console.error('[SecureDoc] loadPage: token or sessionId missing',
        { token: token ? '[set]' : '[missing]', pageNum, sessionId: sessionId ? '[set]' : '[missing]' });
      setImgLoading(false);
      return;
    }
    const key = `${token}:${pageNum}`;

    // Cache hit — instant display (no network round-trip; crossfade from current page)
    if (pageCache.current.has(key)) {
      const cached = pageCache.current.get(key);
      setPrevImgSrc(imgSrcRef.current);
      setImgSrc(cached);
      setImgReady(true);
      setImgLoading(false);
      return;
    }

    // Phase 7: request deduplication — if this page is already being fetched,
    // wait for the existing promise instead of firing a second request.
    if (inflightRef.current.has(key)) {
      try { await inflightRef.current.get(key); } catch {}
      if (pageCache.current.has(key)) {
        const cached = pageCache.current.get(key);
        setImgSrc(cached);
        setImgReady(true);
      }
      setImgLoading(false);
      return;
    }

    // Phase 7: smooth transition — save current page as background, keep it visible
    // while the new page fetches. imgReady controls crossfade opacity.
    setPrevImgSrc(imgSrcRef.current);
    setImgReady(false);
    setImgLoading(true);
    setPageError(null);

    const url = window.SecureDocAPI.getPageUrl(token, pageNum);
    const fetchPromise = (async () => {
      try {
        const r = await fetch(url, { headers: window.SecureDocAPI.sessionHeaders(sessionId) });
        if (!r.ok) {
          let detail = null;
          try { detail = (await r.json()).detail; } catch {}
          console.error('[SecureDoc] page fetch HTTP error', r.status, url, detail);
          if (r.status === 401) {
            _onAuth401Ref.current?.();
            return;
          }
          setPageError(detail || `Unable to load page (${r.status})`);
          setImgReady(true);
          return;
        }
        const blobUrl = URL.createObjectURL(await r.blob());
        _cacheSet(key, blobUrl);
        setImgSrc(blobUrl);
        setPageError(null);
        // imgReady set by onLoad handler to trigger crossfade after browser decodes image
      } catch {
        console.warn('[SecureDoc] page fetch network error, falling back to img src', url);
        setImgSrc(url);
        setImgReady(true);
      } finally {
        setImgLoading(false);
        inflightRef.current.delete(key);
      }
    })();

    inflightRef.current.set(key, fetchPromise);
    await fetchPromise;
  }, []);

  const prefetchPage = useCallback((token, pageNum, sessionId, total) => {
    if (pageNum < 1 || pageNum > total) return;
    const key = `${token}:${pageNum}`;
    if (pageCache.current.has(key)) return;
    fetch(window.SecureDocAPI.getPageUrl(token, pageNum), { headers: window.SecureDocAPI.sessionHeaders(sessionId) })
      .then(r => r.ok ? r.blob() : Promise.reject())
      .then(blob => { _cacheSet(key, URL.createObjectURL(blob)); })
      .catch(() => {});
  }, []);

  const loadPage2 = useCallback(async (token, pageNum, sessionId, total) => {
    if (!token || !sessionId || pageNum < 1 || pageNum > total) { setImgSrc2(''); return; }
    const key = `${token}:${pageNum}`;
    if (pageCache.current.has(key)) { setImgSrc2(pageCache.current.get(key)); return; }
    setImgLoading2(true);
    setPage2Error(null);
    try {
      const r = await fetch(window.SecureDocAPI.getPageUrl(token, pageNum), { headers: window.SecureDocAPI.sessionHeaders(sessionId) });
      if (!r.ok) { const d = await r.json().catch(() => ({})); setPage2Error(d.detail || `Error (${r.status})`); return; }
      const blobUrl = URL.createObjectURL(await r.blob());
      _cacheSet(key, blobUrl);
      setImgSrc2(blobUrl);
    } catch { setPage2Error('Network error'); }
    finally { setImgLoading2(false); }
  }, []);

  const PAGE_COUNT = session?.page_count || 1;
  const isTwoPage = twoPageMode;

  // Phase 7: keep imgSrcRef in sync so loadPage (empty-deps callback) can
  // capture the current page URL for the crossfade background layer.
  useEffect(() => { imgSrcRef.current = imgSrc; }, [imgSrc]);

  // Revoke all blob URLs when the viewer unmounts to prevent memory leaks
  useEffect(() => () => _clearPageCache(), []);

  // Load page — checks in-memory blob cache first; fetches on miss.
  // Depends on individual session fields so the effect only re-fires when
  // the token, session_id, or page number actually changes (not on every
  // object re-allocation after a validate call that reused the same slot).
  //
  // Note: page_viewed is logged server-side on every /api/viewer/page request;
  // the frontend only logs client-side events (print_attempt, copy_attempt, etc.)
  useEffect(() => {
    if (!session) return;
    if (isTextDoc) return; // text/md/log handled by text effect below
    // Skip network call entirely when document isn't ready yet — show status inline
    if (session.doc_status && session.doc_status !== 'ready') {
      const msgs = {
        uploaded: 'Document is queued for processing — please wait and refresh.',
        processing: 'Document is still processing — please wait a moment and refresh.',
        error: 'Document processing failed. Please contact the document owner.',
      };
      setPageError(msgs[session.doc_status] || `Document not available (${session.doc_status})`);
      return;
    }
    setPageError(null);
    loadPage(session.link_token, page, session.session_id);
    // Log completion when the viewer reaches the last page (client-side event)
    if (page === session.page_count) {
      window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'completed');
    }
  }, [session?.link_token, session?.session_id, page, session?.doc_status, session?.doc_type, loadPage]);

  // Prefetch the next and previous pages in the background as soon as the
  // current page has finished loading, so navigation feels instantaneous.
  useEffect(() => {
    if (!session || imgLoading || isTextDoc) return;
    prefetchPage(session.link_token, page + 1, session.session_id, PAGE_COUNT);
    if (page > 1) prefetchPage(session.link_token, page - 1, session.session_id, PAGE_COUNT);
  }, [session?.link_token, session?.session_id, page, imgLoading, PAGE_COUNT, prefetchPage, isTextDoc]);

  // Load second page in two-page view mode
  useEffect(() => {
    if (!session || isTextDoc || !isTwoPage) { setImgSrc2(''); return; }
    if (session.doc_status && session.doc_status !== 'ready') return;
    loadPage2(session.link_token, page + 1, session.session_id, PAGE_COUNT);
  }, [session?.link_token, session?.session_id, page, isTwoPage, isTextDoc, PAGE_COUNT, session?.doc_status, loadPage2]);

  // Eagerly prefetch page 2 in parallel with page 1 the moment a session
  // is established, so forward navigation feels instant on page 1.
  useEffect(() => {
    if (!session || isTextDoc) return;
    const pc = session.page_count || 1;
    if (pc >= 2) prefetchPage(session.link_token, 2, session.session_id, pc);
  }, [session?.link_token, session?.session_id, session?.doc_type]); // intentionally omit prefetchPage — stable ref

  return {
    imgSrc,
    imgLoading,
    pageError,
    prevImgSrc,
    imgReady, setImgReady,
    imgSrc2,
    imgLoading2,
    page2Error,
    pageAspectRatio, setPageAspectRatio,
    pageImgRef,
    pageContainerRef,
  };
}
