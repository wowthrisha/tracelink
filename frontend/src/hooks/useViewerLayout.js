// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useCallback, useEffect } = React;
import { LAYOUT, ZOOM_MIN, ZOOM_MAX, _saveLayoutPref, _loadLayoutPref } from '../constants/viewer.js';

/**
 * Manages viewer layout, navigation, zoom, fullscreen, and keyboard/touch
 * interaction state. Also owns session-state persistence to sessionStorage.
 *
 * Must be called before any hook that consumes `page` (useTextLoader,
 * useSearchHighlights, useAnnotations) so that `page` is in scope.
 *
 * @param {object|null} session              - Validated viewer session object.
 * @param {object}      [opts]
 * @param {Function}    [opts.onToggleSearch] - Called when Ctrl/Cmd+F is pressed.
 *   ViewerScreen passes `() => setShowSearch(v => !v)`. Stored in a ref internally
 *   so it does not need to be stable across renders.
 */
export function useViewerLayout(session, { onToggleSearch } = {}) {
  const _initPref = _loadLayoutPref();
  const [page, setPage] = useState(1);
  const [layoutMode, setLayoutMode] = useState(_initPref.mode);
  const [customZoom, setCustomZoom] = useState(_initPref.zoom);
  const [rotation, setRotation] = useState(0);
  const [twoPageMode, setTwoPageMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [pageInputStr, setPageInputStr] = useState('');

  const touchRef = useRef({ x: null, y: null, pinchDist: null });

  // Stable ref for the toggle-search callback so it is never in effect deps.
  const _onToggleSearchRef = useRef(onToggleSearch);
  useEffect(() => { _onToggleSearchRef.current = onToggleSearch; });

  const PAGE_COUNT = session?.page_count || 1;
  const pageStep = twoPageMode ? 2 : 1;

  const goNext = useCallback(() => setPage(p => Math.min(p + pageStep, PAGE_COUNT)), [PAGE_COUNT, pageStep]);
  const goPrev = useCallback(() => setPage(p => Math.max(p - pageStep, 1)), [pageStep]);

  // Layout helpers (stable identity — no setState in dep array needed)
  const _setLayout = useCallback((mode, zoom) => {
    setLayoutMode(mode);
    if (zoom !== undefined) setCustomZoom(zoom);
    _saveLayoutPref(mode, zoom !== undefined ? zoom : customZoom);
  }, [customZoom]);

  const _zoomBy = useCallback((delta) => {
    setCustomZoom(z => {
      const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z + delta));
      setLayoutMode(LAYOUT.CUSTOM);
      _saveLayoutPref(LAYOUT.CUSTOM, next);
      return next;
    });
  }, []);

  const _zoomTo = useCallback((pct) => {
    setCustomZoom(pct);
    setLayoutMode(LAYOUT.CUSTOM);
    _saveLayoutPref(LAYOUT.CUSTOM, pct);
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.();
    }
  }, []);

  // Keyboard navigation + browser search intercept + pinch-zoom block
  useEffect(() => {
    const h = e => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goNext();
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') goPrev();
      // Ctrl+F / Cmd+F opens in-viewer search
      if ((e.ctrlKey || e.metaKey) && e.key === 'f' && session) {
        e.preventDefault();
        _onToggleSearchRef.current?.();
      }
    };
    // Block browser native page-zoom from trackpad pinch (ctrlKey+wheel).
    // Zoom is controlled ONLY by the toolbar +/− buttons.
    const blockPinchZoom = e => { if (e.ctrlKey || e.metaKey) e.preventDefault(); };
    window.addEventListener('keydown', h);
    window.addEventListener('wheel', blockPinchZoom, { passive: false });
    return () => {
      window.removeEventListener('keydown', h);
      window.removeEventListener('wheel', blockPinchZoom);
    };
  }, [goNext, goPrev, session, _zoomBy, _setLayout]);

  // Phase 7: viewer state persistence — restore page/zoom from sessionStorage
  useEffect(() => {
    if (!session?.session_id) return;
    try {
      const saved = sessionStorage.getItem(`securedoc_vstate_${session.session_id}`);
      if (saved) {
        const { pg, zm } = JSON.parse(saved);
        if (pg && pg >= 1 && pg <= (session.page_count || 1)) setPage(pg);
        if (zm && zm >= ZOOM_MIN && zm <= ZOOM_MAX) {
          setCustomZoom(zm);
          setLayoutMode(LAYOUT.CUSTOM);
        }
      }
    } catch {}
  }, [session?.session_id]);

  // Phase 7: save viewer state on change
  useEffect(() => {
    if (!session?.session_id) return;
    try {
      sessionStorage.setItem(
        `securedoc_vstate_${session.session_id}`,
        JSON.stringify({ pg: page, zm: customZoom })
      );
    } catch {}
  }, [session?.session_id, page, customZoom]);

  // Sync fullscreen state with the browser's fullscreen element
  useEffect(() => {
    const h = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', h);
    return () => document.removeEventListener('fullscreenchange', h);
  }, []);

  return {
    page, setPage,
    pageInputStr, setPageInputStr,
    twoPageMode, setTwoPageMode,
    isFullscreen,
    layoutMode, setLayoutMode,
    customZoom, setCustomZoom,
    rotation, setRotation,
    goNext, goPrev,
    _setLayout, _zoomBy, _zoomTo,
    toggleFullscreen,
    touchRef,
  };
}
