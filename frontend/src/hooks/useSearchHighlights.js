// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useCallback, useEffect } = React;

/**
 * Manages search highlight state, word-position data, and the
 * highlight computation effect for the document viewer.
 *
 * @param {object|null} session - Validated viewer session object.
 * @param {number}      page    - Current page number.
 */
export function useSearchHighlights(session, page) {
  const [searchHighlightQuery, setSearchHighlightQuery] = useState('');
  const [searchHighlights, setSearchHighlights] = useState([]);
  const [searchResultPages, setSearchResultPages] = useState(new Set());
  const [activeHighlightIdx, setActiveHighlightIdx] = useState(0);

  // {pageNum: [{t, x, y, w, h}, …]} — fetched once per session, keyed by page
  const wordPositionsRef = useRef({});
  // Guards against re-fetching when word positions have already been loaded
  const wordPositionsFetched = useRef(false);

  const _computeHighlights = useCallback((pageNum, query) => {
    if (!query) { setSearchHighlights([]); return; }
    const words = wordPositionsRef.current[pageNum] || [];
    const ql = query.toLowerCase();
    setSearchHighlights(words.filter(w => w.t && w.t.toLowerCase().includes(ql)));
  }, []);

  useEffect(() => {
    if (!searchHighlightQuery || !session?.link_token) {
      setSearchHighlights([]);
      return;
    }
    // If already fetched (even if empty), just recompute from what we have
    if (wordPositionsFetched.current) {
      _computeHighlights(page, searchHighlightQuery);
      return;
    }
    wordPositionsFetched.current = true;
    window.SecureDocAPI.getWordPositions(session.link_token, session.session_id)
      .then(data => {
        const map = {};
        for (const p of (data.pages || [])) map[p.page] = p.words || [];
        wordPositionsRef.current = map;
        _computeHighlights(page, searchHighlightQuery);
      })
      .catch(() => {});
  }, [searchHighlightQuery, page, session?.link_token, session?.session_id, _computeHighlights]);

  return {
    searchHighlightQuery,
    setSearchHighlightQuery,
    searchHighlights,
    searchResultPages,
    setSearchResultPages,
    activeHighlightIdx,
    setActiveHighlightIdx,
    wordPositionsRef,
    wordPositionsFetched,
  };
}
