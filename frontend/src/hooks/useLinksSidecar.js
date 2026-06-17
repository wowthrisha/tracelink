// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useEffect } = React;

/**
 * Manages hyperlink sidecar state for the viewer.
 *
 * Loads the per-page link map once per session, auto-triggers sidecar
 * extraction for documents that predate the feature, and tracks which
 * URLs the viewer has already opened.
 *
 * @param {object|null} session  - Validated viewer session object.
 * @param {string}      docId   - Document ID (owner-only; null for public tokens).
 * @param {boolean}     isTextDoc - True for txt/md/log; skips link loading.
 * @param {object}      [opts]
 * @param {Function}    [opts.onAutoExtractReset] - Called inside the 15-second
 *   post-extract timer alongside the sidecar ref reset. ViewerScreen uses this
 *   to clear search word-position refs that it still owns in this phase.
 */
export function useLinksSidecar(session, docId, isTextDoc, { onAutoExtractReset } = {}) {
  const [linksLoaded, setLinksLoaded] = useState(false);
  const [visitedLinks, setVisitedLinks] = useState(new Set());
  const [sidecarExtracted, setSidecarExtracted] = useState(false);

  // {pageNum: [{x, y, w, h, url, type, label?}, …]}
  const pageLinksRef = useRef({});
  // Fire-once guard: prevents redundant extraction when backend already extracted.
  const autoExtractAttempted = useRef(false);

  // Feature 1: load hyperlink sidecar once when session activates
  useEffect(() => {
    if (!session?.link_token || !session?.session_id || isTextDoc) return;
    window.SecureDocAPI.getDocumentLinks(session.link_token, session.session_id)
      .then(data => {
        const map = {};
        for (const p of (data.pages || [])) map[p.page] = p.links || [];
        pageLinksRef.current = map;
        // If backend signals extraction was already done, skip auto-extract
        if (data.extracted) autoExtractAttempted.current = true;
        setLinksLoaded(true);
      })
      .catch(() => { setLinksLoaded(true); });
  }, [session?.link_token, session?.session_id, isTextDoc]);

  // Auto-extract sidecars when authenticated owner's doc has no extraction yet.
  // `autoExtractAttempted` is set when sidecar has `extracted:true` flag, so this
  // only fires for documents uploaded before the feature was added.
  useEffect(() => {
    if (!linksLoaded || !docId || autoExtractAttempted.current) return;
    autoExtractAttempted.current = true;
    window.SecureDocAPI.extractSidecars(docId).catch(() => {});
    const t = setTimeout(() => {
      pageLinksRef.current = {};
      setLinksLoaded(false);
      onAutoExtractReset?.();
    }, 15000);
    return () => clearTimeout(t);
  }, [linksLoaded, docId]);

  return {
    pageLinksRef,
    linksLoaded,
    setLinksLoaded,
    visitedLinks,
    setVisitedLinks,
    sidecarExtracted,
    setSidecarExtracted,
  };
}
