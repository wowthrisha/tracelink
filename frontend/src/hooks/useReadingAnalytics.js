/**
 * Reading Intelligence Engine — viewer-side tracking hook.
 *
 * Tracks active reading time with sub-second precision using performance.now().
 * Pauses automatically on: tab hidden, window blur, idle >30s, document loading.
 * Resumes automatically on: tab visible, window focus, any user interaction.
 *
 * Per-page state accumulates in a ref (no re-render on every tick).
 * Display state updates once per second via setInterval.
 * Batches events to the backend every FLUSH_INTERVAL_MS (5 seconds).
 *
 * PRIVACY: No webcam, no keystrokes, no clipboard. Tracks only:
 *   - time spent per page (active vs idle)
 *   - page navigation (enter/exit timestamps)
 *   - visible browser events (tab switch, window blur)
 *   - user interactions that exist in session context (copy/print attempts)
 */

const { useState, useEffect, useRef, useCallback } = React;

const IDLE_THRESHOLD_MS = 30_000;   // 30s idle → pause timer
const FLUSH_INTERVAL_MS = 5_000;    // batch flush to backend every 5s
const DISPLAY_INTERVAL_MS = 1_000;  // display update every 1s
const MAX_ACTIVE_MS_PER_PAGE = 14_400_000; // 4h cap

// Words per minute baseline for initial estimate before any page data
const INITIAL_WPM = 200;

// EWMA alpha for reading speed smoothing
const EWMA_ALPHA = 0.35;

/**
 * Estimate remaining reading time from collected page data.
 * @param {Object[]} completedPages - page events with active_time_ms
 * @param {number}   currentPage    - current page number (1-based)
 * @param {number}   totalPages     - total page count
 * @param {number}   wordsPerPage   - estimated words per page
 * @param {number}   baselineWpm    - fallback wpm when no session data
 * @returns {number|null} remaining milliseconds, or null if unknown
 */
function _estimateRemaining(completedPages, currentPage, totalPages, wordsPerPage, baselineWpm) {
  const pagesRemaining = totalPages - currentPage;
  if (pagesRemaining <= 0) return 0;

  // Filter to pages with meaningful read time
  const qualifying = completedPages.filter(p =>
    p.active_time_ms > 1000 && ['reading', 'completed'].includes(p.completion_status)
  );

  let blendedWpm = baselineWpm;
  if (qualifying.length >= 2) {
    // EWMA of per-page wpm
    const readings = qualifying.map(p => {
      const minutes = p.active_time_ms / 60_000;
      return minutes > 0 ? wordsPerPage / minutes : 0;
    }).filter(r => r > 0);

    if (readings.length >= 2) {
      let ewma = readings[0];
      for (let i = 1; i < readings.length; i++) {
        ewma = EWMA_ALPHA * readings[i] + (1 - EWMA_ALPHA) * ewma;
      }
      // Clamp: 50–700 wpm
      const sessionWpm = Math.max(50, Math.min(700, ewma));
      // Blend: session weight grows with completed pages, caps at 1.0 after 5 pages
      const sessionWeight = Math.min(1.0, qualifying.length / 5);
      blendedWpm = sessionWeight * sessionWpm + (1 - sessionWeight) * baselineWpm;
    }
  }

  if (blendedWpm <= 0) return null;
  const wordsRemaining = pagesRemaining * wordsPerPage;
  return Math.round((wordsRemaining / blendedWpm) * 60_000);
}

/**
 * Determine page completion status from active_time_ms vs expected time.
 * @param {number} activeMs
 * @param {number} revisitCount
 * @param {number} expectedMs - expected ms per page at baseline wpm
 * @returns {string}
 */
function _pageStatus(activeMs, revisitCount, expectedMs) {
  if (revisitCount > 0) return 'revisited';
  if (activeMs <= 0) return 'unread';
  if (activeMs < 3_000) return 'started';
  if (activeMs < 15_000) return 'reading';
  if (activeMs >= expectedMs * 0.7) return 'completed';
  return 'reading';
}

export function useReadingAnalytics(session, page, pageCount, isDocumentReady) {
  // ── Shared ref (no re-renders on every tick) ──────────────────────────────
  const state = useRef({
    // Session-level
    sessionStartMs: null,       // performance.now() when session started
    sessionStartAt: null,       // ISO string (wall clock)
    totalActiveMs: 0,           // accumulated active time across all pages
    totalElapsedMs: 0,          // wall clock elapsed
    isActive: false,            // whether the timer is currently running
    isPaused: false,            // paused vs active
    pauseResumeTime: null,      // performance.now() when last resumed
    // Idle detection
    lastInteractionTime: null,  // performance.now() of last user interaction
    idleTimerId: null,
    // Per-page state
    pageData: {},               // { [pageNum]: PageState }
    currentPage: null,
    currentPageEnterPerfTime: null,  // performance.now() when current page entered
    // Batch
    lastFlushPerfTime: null,
    hasPendingFlush: false,
    // Prediction
    initialEstimateMs: null,
    wordsPerPage: 250,          // updated from session data
    baselineWpm: INITIAL_WPM,
  });

  // ── Display state (causes re-renders once/second) ─────────────────────────
  const [display, setDisplay] = useState({
    totalActiveMs: 0,
    estimatedRemainingMs: null,
    currentPageActiveMs: 0,
    completedPages: 0,
    avgMsPerPage: null,
    readingSpeedWpm: null,
    completionPct: 0,
  });

  // Refs for interaction tracking (shared with DRM system in useViewerSession)
  const copyCountRef = useRef({});   // { [page]: count }
  const printCountRef = useRef({});  // { [page]: count }
  const tabSwitchCountRef = useRef({});
  const visibilityChangesRef = useRef({});
  const idleEventsRef = useRef({});

  // ── Helpers ───────────────────────────────────────────────────────────────

  const _getOrCreatePageData = useCallback((pageNum) => {
    const s = state.current;
    if (!s.pageData[pageNum]) {
      s.pageData[pageNum] = {
        page_number: pageNum,
        active_time_ms: 0,
        pause_duration_ms: 0,
        revisit_count: 0,
        scroll_percentage: 0,
        zoom_level: 100,
        fullscreen_used: false,
        annotations_created: 0,
        copy_attempts: 0,
        print_attempts: 0,
        tab_switch_count: 0,
        visibility_changes: 0,
        idle_events: 0,
        completion_status: 'unread',
        enter_timestamp: null,
        exit_timestamp: null,
        _hasEntered: false,
        _visitCount: 0,
      };
    }
    return s.pageData[pageNum];
  }, []);

  const _accumulateCurrentPage = useCallback(() => {
    const s = state.current;
    if (!s.isActive || s.currentPage === null || s.currentPageEnterPerfTime === null) return;
    const now = performance.now();
    const delta = Math.max(0, now - s.currentPageEnterPerfTime);
    const pd = _getOrCreatePageData(s.currentPage);
    pd.active_time_ms = Math.min(MAX_ACTIVE_MS_PER_PAGE, pd.active_time_ms + delta);
    s.totalActiveMs += delta;
    s.currentPageEnterPerfTime = now;
  }, [_getOrCreatePageData]);

  const _pause = useCallback(() => {
    const s = state.current;
    if (!s.isActive) return;
    _accumulateCurrentPage();
    s.isActive = false;
    s.pauseResumeTime = null;
  }, [_accumulateCurrentPage]);

  const _resume = useCallback(() => {
    const s = state.current;
    if (s.isActive || !session || !isDocumentReady) return;
    s.isActive = true;
    s.currentPageEnterPerfTime = performance.now();
    s.lastInteractionTime = performance.now();
    // Reset idle timer
    if (s.idleTimerId) clearTimeout(s.idleTimerId);
    s.idleTimerId = setTimeout(() => {
      const pd = _getOrCreatePageData(s.currentPage);
      pd.idle_events = (pd.idle_events || 0) + 1;
      idleEventsRef.current[s.currentPage] = (idleEventsRef.current[s.currentPage] || 0) + 1;
      _pause();
    }, IDLE_THRESHOLD_MS);
  }, [session, isDocumentReady, _accumulateCurrentPage, _getOrCreatePageData, _pause]);

  const _resetIdleTimer = useCallback(() => {
    const s = state.current;
    s.lastInteractionTime = performance.now();
    if (s.idleTimerId) { clearTimeout(s.idleTimerId); s.idleTimerId = null; }
    if (!s.isActive) _resume();
    s.idleTimerId = setTimeout(() => {
      const pd = _getOrCreatePageData(s.currentPage);
      pd.idle_events = (pd.idle_events || 0) + 1;
      idleEventsRef.current[s.currentPage] = (idleEventsRef.current[s.currentPage] || 0) + 1;
      _pause();
    }, IDLE_THRESHOLD_MS);
  }, [_resume, _getOrCreatePageData, _pause]);

  // ── Page transition ───────────────────────────────────────────────────────

  const _onPageExit = useCallback((exitPage) => {
    const s = state.current;
    if (s.isActive) _accumulateCurrentPage();
    if (exitPage === null) return;
    const pd = _getOrCreatePageData(exitPage);
    pd.exit_timestamp = new Date().toISOString();

    // Update completion status
    const expectedMs = (s.wordsPerPage / s.baselineWpm) * 60_000;
    pd.completion_status = _pageStatus(pd.active_time_ms, pd.revisit_count, expectedMs);
  }, [_accumulateCurrentPage, _getOrCreatePageData]);

  const _onPageEnter = useCallback((enterPage) => {
    const s = state.current;
    const pd = _getOrCreatePageData(enterPage);
    const now = performance.now();
    const isoNow = new Date().toISOString();

    if (!pd._hasEntered) {
      pd.enter_timestamp = isoNow;
      pd._hasEntered = true;
    } else {
      // Revisit
      pd.revisit_count += 1;
      pd._visitCount += 1;
      pd.exit_timestamp = null; // reset exit on revisit
    }

    s.currentPage = enterPage;
    s.currentPageEnterPerfTime = now;
    if (s.isActive) {
      // Carry forward the active timer
    }
  }, [_getOrCreatePageData]);

  // ── Flush batch to backend ────────────────────────────────────────────────

  const _flush = useCallback(() => {
    const s = state.current;
    if (!session?.link_token || !session?.session_id) return;

    // Snapshot page data (copy current accumulated times)
    _accumulateCurrentPage();

    const now = performance.now();
    s.totalElapsedMs = s.sessionStartMs !== null
      ? Math.round(now - s.sessionStartMs)
      : s.totalActiveMs;

    const pageDataSnapshot = Object.values(s.pageData)
      .filter(pd => pd.active_time_ms > 0 || pd._hasEntered)
      .map(pd => ({
        page_number: pd.page_number,
        active_time_ms: Math.round(pd.active_time_ms),
        pause_duration_ms: Math.round(pd.pause_duration_ms || 0),
        revisit_count: pd.revisit_count,
        scroll_percentage: Math.round(pd.scroll_percentage * 10) / 10,
        zoom_level: pd.zoom_level,
        fullscreen_used: pd.fullscreen_used,
        annotations_created: pd.annotations_created,
        copy_attempts: copyCountRef.current[pd.page_number] || pd.copy_attempts,
        print_attempts: printCountRef.current[pd.page_number] || pd.print_attempts,
        tab_switch_count: tabSwitchCountRef.current[pd.page_number] || pd.tab_switch_count,
        visibility_changes: visibilityChangesRef.current[pd.page_number] || pd.visibility_changes,
        idle_events: idleEventsRef.current[pd.page_number] || pd.idle_events,
        completion_status: pd.completion_status,
        enter_timestamp: pd.enter_timestamp,
        exit_timestamp: pd.exit_timestamp,
      }));

    if (pageDataSnapshot.length === 0) return;

    const sessionMeta = {
      total_elapsed_ms: Math.round(s.totalElapsedMs),
      total_active_ms: Math.round(s.totalActiveMs),
      started_at: s.sessionStartAt,
      page_count: pageCount,
      current_page: s.currentPage,
      initial_estimate_ms: s.initialEstimateMs,
    };

    window.SecureDocAPI?.batchReadingEvents(
      session.link_token,
      session.session_id,
      pageDataSnapshot,
      sessionMeta,
    );

    s.lastFlushPerfTime = now;
  }, [session, pageCount, _accumulateCurrentPage]);

  // ── Initialize session when document is ready ─────────────────────────────

  useEffect(() => {
    if (!session || !isDocumentReady) return;
    const s = state.current;
    if (s.sessionStartMs !== null) return; // already started

    s.sessionStartMs = performance.now();
    s.sessionStartAt = new Date().toISOString();
    s.lastFlushPerfTime = s.sessionStartMs;

    // Estimate initial remaining from session data if available
    if (pageCount > 0 && session.page_count) {
      const pagesRemaining = session.page_count;
      const wordsRemaining = pagesRemaining * s.wordsPerPage;
      s.initialEstimateMs = Math.round((wordsRemaining / s.baselineWpm) * 60_000);
    }

    _resume();
  }, [session, isDocumentReady, pageCount, _resume]);

  // ── Page change effect ────────────────────────────────────────────────────

  useEffect(() => {
    if (!session || !isDocumentReady || !page) return;
    const s = state.current;
    const prevPage = s.currentPage;

    if (prevPage !== null && prevPage !== page) {
      _onPageExit(prevPage);
    }
    _onPageEnter(page);
  }, [page, session, isDocumentReady, _onPageExit, _onPageEnter]);

  // ── Visibility + focus event listeners ───────────────────────────────────

  useEffect(() => {
    if (!session || !isDocumentReady) return;

    const s = state.current;

    const onVisibilityChange = () => {
      if (document.hidden) {
        const pd = _getOrCreatePageData(s.currentPage);
        pd.tab_switch_count = (pd.tab_switch_count || 0) + 1;
        pd.visibility_changes = (pd.visibility_changes || 0) + 1;
        tabSwitchCountRef.current[s.currentPage] = (tabSwitchCountRef.current[s.currentPage] || 0) + 1;
        visibilityChangesRef.current[s.currentPage] = (visibilityChangesRef.current[s.currentPage] || 0) + 1;
        _pause();
      } else {
        _resume();
      }
    };

    const onBlur = () => _pause();
    const onFocus = () => _resume();

    const onInteraction = () => _resetIdleTimer();

    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    document.addEventListener('mousemove', onInteraction, { passive: true });
    document.addEventListener('keydown', onInteraction, { passive: true });
    document.addEventListener('scroll', onInteraction, { passive: true, capture: true });
    document.addEventListener('touchstart', onInteraction, { passive: true });

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('mousemove', onInteraction);
      document.removeEventListener('keydown', onInteraction);
      document.removeEventListener('scroll', onInteraction, true);
      document.removeEventListener('touchstart', onInteraction);
      if (s.idleTimerId) clearTimeout(s.idleTimerId);
    };
  }, [session, isDocumentReady, _pause, _resume, _resetIdleTimer, _getOrCreatePageData]);

  // ── Display update interval (once per second) ─────────────────────────────

  useEffect(() => {
    if (!session || !isDocumentReady) return;

    const timer = setInterval(() => {
      const s = state.current;

      // Compute live display values without mutating ref (accumulate to temp)
      let liveActiveMs = s.totalActiveMs;
      if (s.isActive && s.currentPageEnterPerfTime !== null) {
        liveActiveMs += performance.now() - s.currentPageEnterPerfTime;
      }

      const completedPages = Object.values(s.pageData).filter(
        p => ['completed', 'revisited'].includes(p.completion_status)
      );
      const validPages = Object.values(s.pageData).filter(p => p.active_time_ms > 1000);
      const avgMs = validPages.length > 0
        ? validPages.reduce((sum, p) => sum + p.active_time_ms, 0) / validPages.length
        : null;

      const currentPd = s.currentPage ? s.pageData[s.currentPage] : null;
      let currentPageMs = (currentPd?.active_time_ms || 0);
      if (s.isActive && s.currentPageEnterPerfTime !== null) {
        currentPageMs += performance.now() - s.currentPageEnterPerfTime;
      }

      // Reading speed from completed pages
      const qualifying = Object.values(s.pageData).filter(
        p => p.active_time_ms > 1000 && ['reading', 'completed'].includes(p.completion_status)
      );
      let speedWpm = null;
      if (qualifying.length >= 2) {
        const readings = qualifying.map(p => (s.wordsPerPage / (p.active_time_ms / 60_000)));
        let ewma = readings[0];
        for (let i = 1; i < readings.length; i++) {
          ewma = EWMA_ALPHA * readings[i] + (1 - EWMA_ALPHA) * ewma;
        }
        speedWpm = Math.round(Math.max(50, Math.min(700, ewma)));
      }

      const remaining = _estimateRemaining(
        Object.values(s.pageData),
        s.currentPage || page,
        pageCount,
        s.wordsPerPage,
        s.baselineWpm,
      );

      const completionPct = pageCount > 0
        ? Math.min(100, (Object.values(s.pageData).filter(p => p._hasEntered).length / pageCount) * 100)
        : 0;

      setDisplay({
        totalActiveMs: Math.round(liveActiveMs),
        estimatedRemainingMs: remaining,
        currentPageActiveMs: Math.round(currentPageMs),
        completedPages: completedPages.length,
        avgMsPerPage: avgMs ? Math.round(avgMs) : null,
        readingSpeedWpm: speedWpm,
        completionPct: Math.round(completionPct),
      });
    }, DISPLAY_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [session, isDocumentReady, page, pageCount, _estimateRemaining]);

  // ── Flush interval (every 5 seconds) ─────────────────────────────────────

  useEffect(() => {
    if (!session || !isDocumentReady) return;
    const timer = setInterval(_flush, FLUSH_INTERVAL_MS);
    // Final flush on unmount
    return () => {
      clearInterval(timer);
      _flush();
    };
  }, [session, isDocumentReady, _flush]);

  // ── Scroll tracking ───────────────────────────────────────────────────────

  const onScroll = useCallback((scrollPct) => {
    const s = state.current;
    if (s.currentPage === null) return;
    const pd = _getOrCreatePageData(s.currentPage);
    pd.scroll_percentage = Math.max(pd.scroll_percentage || 0, scrollPct);
  }, [_getOrCreatePageData]);

  // ── Zoom tracking ─────────────────────────────────────────────────────────

  const onZoomChange = useCallback((zoomLevel) => {
    const s = state.current;
    if (s.currentPage === null) return;
    const pd = _getOrCreatePageData(s.currentPage);
    pd.zoom_level = zoomLevel;
  }, [_getOrCreatePageData]);

  // ── Fullscreen tracking ───────────────────────────────────────────────────

  const onFullscreen = useCallback((isFullscreen) => {
    const s = state.current;
    if (s.currentPage === null || !isFullscreen) return;
    const pd = _getOrCreatePageData(s.currentPage);
    pd.fullscreen_used = true;
  }, [_getOrCreatePageData]);

  // ── Copy/print increment (called by DRM hooks) ────────────────────────────

  const onCopyAttempt = useCallback(() => {
    const s = state.current;
    if (s.currentPage === null) return;
    copyCountRef.current[s.currentPage] = (copyCountRef.current[s.currentPage] || 0) + 1;
  }, []);

  const onPrintAttempt = useCallback(() => {
    const s = state.current;
    if (s.currentPage === null) return;
    printCountRef.current[s.currentPage] = (printCountRef.current[s.currentPage] || 0) + 1;
  }, []);

  // ── Annotation increment ──────────────────────────────────────────────────

  const onAnnotationCreated = useCallback(() => {
    const s = state.current;
    if (s.currentPage === null) return;
    const pd = _getOrCreatePageData(s.currentPage);
    pd.annotations_created = (pd.annotations_created || 0) + 1;
  }, [_getOrCreatePageData]);

  return {
    display,         // { totalActiveMs, estimatedRemainingMs, currentPageActiveMs, ... }
    onScroll,        // call with scroll percentage 0–100
    onZoomChange,    // call with zoom level (integer, 100 = 100%)
    onFullscreen,    // call when entering fullscreen
    onCopyAttempt,   // call when viewer attempts a copy
    onPrintAttempt,  // call when viewer attempts a print
    onAnnotationCreated,  // call after annotation is saved
    _flush,          // call manually on unmount or page unload
  };
}
