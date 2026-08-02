/**
 * Reading Intelligence Engine — viewer-side active-time tracker.
 *
 * KEY DESIGN PRINCIPLES:
 *   - Uses a mutable ref (state.current) for all timing state to avoid re-renders on every tick
 *   - Display state updates once per second via setInterval
 *   - Batch flush to backend every 5s (fire-and-forget, never blocks rendering)
 *   - isDocumentReady fluctuations (caused by page navigation resetting imgReady) are absorbed:
 *     once the session starts, the timer never re-initializes mid-session
 *   - Event listeners are attached once per session, not per page navigation
 *   - _resume/_pause are stable across renders (only depend on state.current, never on React props)
 *
 * TIMER PAUSE CONDITIONS:
 *   Tab hidden, window blur, idle >30s (no mouse/key/scroll/touch), document loading
 *
 * PRIVACY: No webcam, keylogger, or clipboard access. Tracks only:
 *   - active time per page, page navigation sequence
 *   - visible browser events (tab switch, window blur)
 *   - scroll depth, zoom level, fullscreen
 */

const { useState, useEffect, useRef, useCallback } = React;

const IDLE_THRESHOLD_MS = 30_000;
const FLUSH_INTERVAL_MS = 5_000;
const DISPLAY_INTERVAL_MS = 1_000;
const MAX_ACTIVE_MS_PER_PAGE = 14_400_000; // 4 hours cap per page
const INITIAL_WPM = 200;
const EWMA_ALPHA = 0.35;

// Rank for upgrade-only completion status changes
const STATUS_RANK = { unread: 0, skipped: 1, started: 2, reading: 3, revisited: 4, completed: 5 };

function _pageStatus(activeMs, revisitCount, expectedMs) {
  if (revisitCount > 0) return 'revisited';
  if (activeMs <= 0) return 'unread';
  if (activeMs < 3_000) return 'started';
  if (activeMs < 15_000) return 'reading';
  if (activeMs >= expectedMs * 0.7) return 'completed';
  return 'reading';
}

function _upgradeStatus(current, next) {
  return (STATUS_RANK[next] || 0) > (STATUS_RANK[current] || 0) ? next : current;
}

function _estimateRemainingMs(pageDataMap, currentPage, totalPages, wordsPerPage, baselineWpm) {
  const pagesRemaining = Math.max(0, totalPages - (currentPage || 0));
  if (pagesRemaining === 0) return 0;

  // Use all pages with real time data (not just "completed" — include current page being read)
  const qualifying = Object.values(pageDataMap).filter(p => p.active_time_ms > 1000);

  let blendedWpm = baselineWpm;
  if (qualifying.length >= 1) {
    const readings = qualifying
      .map(p => wordsPerPage / (p.active_time_ms / 60_000))
      .filter(r => r > 0 && r < 2000);
    if (readings.length >= 1) {
      let ewma = readings[0];
      for (let i = 1; i < readings.length; i++) {
        ewma = EWMA_ALPHA * readings[i] + (1 - EWMA_ALPHA) * ewma;
      }
      const sessionWpm = Math.max(50, Math.min(700, ewma));
      // Blend: full session weight after 3 pages (not 5 — gets useful estimates faster)
      const sessionWeight = Math.min(1.0, qualifying.length / 3);
      blendedWpm = sessionWeight * sessionWpm + (1 - sessionWeight) * baselineWpm;
    }
  }

  return Math.round((pagesRemaining * wordsPerPage) / blendedWpm * 60_000);
}

export function useReadingAnalytics(session, page, pageCount, isDocumentReady) {
  // All timing state lives in a ref — no re-renders on every tick
  const state = useRef({
    sessionStarted: false,        // true once _startSession() has been called
    sessionStartMs: null,         // performance.now() at session start
    sessionStartAt: null,         // ISO string wall clock
    totalActiveMs: 0,             // accumulated active time across all pages
    isActive: false,              // is the timer currently running?
    currentPage: null,
    currentPageEnterPerfTime: null,
    idleTimerId: null,
    pageData: {},                 // { [pageNum]: PageState }
    wordsPerPage: 250,
    baselineWpm: INITIAL_WPM,
    listenersAttached: false,
  });

  // Separate refs for side-channel counters
  const copyCountRef = useRef({});
  const printCountRef = useRef({});
  const tabSwitchCountRef = useRef({});
  const visibilityChangesRef = useRef({});
  const idleEventsRef = useRef({});

  // Display state — updated every second
  const [display, setDisplay] = useState({
    isActive: false,
    totalActiveMs: 0,
    estimatedRemainingMs: null,
    currentPageActiveMs: 0,
    completedPages: 0,
    pagesVisited: 0,
    avgMsPerPage: null,
    readingSpeedWpm: null,
    completionPct: 0,
  });

  // ── Stable helpers (no React state deps — read from state.current only) ──

  const _getOrCreate = useCallback((pageNum) => {
    if (pageNum == null) return null;
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
      };
    }
    return s.pageData[pageNum];
  }, []);

  // Accumulate elapsed time for the current page into active_time_ms
  const _accumulate = useCallback(() => {
    const s = state.current;
    if (!s.isActive || s.currentPage == null || s.currentPageEnterPerfTime == null) return;
    const now = performance.now();
    const delta = Math.max(0, now - s.currentPageEnterPerfTime);
    if (delta === 0) return;
    const pd = _getOrCreate(s.currentPage);
    if (pd) pd.active_time_ms = Math.min(MAX_ACTIVE_MS_PER_PAGE, pd.active_time_ms + delta);
    s.totalActiveMs += delta;
    s.currentPageEnterPerfTime = now;
  }, [_getOrCreate]);

  // Pause the timer immediately — no React deps
  const _pause = useCallback(() => {
    const s = state.current;
    if (!s.isActive) return;
    _accumulate();
    s.isActive = false;
  }, [_accumulate]);

  // Resume the timer — no React deps (reads session from a ref)
  const sessionRef = useRef(session);
  useEffect(() => { sessionRef.current = session; }, [session]);

  const _resume = useCallback(() => {
    const s = state.current;
    if (s.isActive || !sessionRef.current || !s.sessionStarted) return;
    s.isActive = true;
    s.currentPageEnterPerfTime = performance.now();
    // Reset idle countdown
    if (s.idleTimerId) clearTimeout(s.idleTimerId);
    s.idleTimerId = setTimeout(() => {
      const pd = _getOrCreate(s.currentPage);
      if (pd) pd.idle_events += 1;
      if (s.currentPage != null) {
        idleEventsRef.current[s.currentPage] = (idleEventsRef.current[s.currentPage] || 0) + 1;
      }
      _pause();
    }, IDLE_THRESHOLD_MS);
  }, [_accumulate, _pause, _getOrCreate]);

  const _resetIdle = useCallback(() => {
    const s = state.current;
    if (s.idleTimerId) { clearTimeout(s.idleTimerId); s.idleTimerId = null; }
    if (!s.isActive) _resume();
    else {
      s.idleTimerId = setTimeout(() => {
        const pd = _getOrCreate(s.currentPage);
        if (pd) pd.idle_events += 1;
        if (s.currentPage != null) {
          idleEventsRef.current[s.currentPage] = (idleEventsRef.current[s.currentPage] || 0) + 1;
        }
        _pause();
      }, IDLE_THRESHOLD_MS);
    }
  }, [_resume, _pause, _getOrCreate]);

  // ── Session start (runs only once) ─────────────────────────────────────────

  const _startSession = useCallback(() => {
    const s = state.current;
    if (s.sessionStarted) return;
    s.sessionStarted = true;
    s.sessionStartMs = performance.now();
    s.sessionStartAt = new Date().toISOString();
    _resume();
  }, [_resume]);

  // ── Page transitions ───────────────────────────────────────────────────────

  const _exitPage = useCallback((exitPage) => {
    if (exitPage == null) return;
    _accumulate();
    const s = state.current;
    const pd = _getOrCreate(exitPage);
    if (!pd) return;
    pd.exit_timestamp = new Date().toISOString();
    const expectedMs = (s.wordsPerPage / s.baselineWpm) * 60_000;
    const newStatus = _pageStatus(pd.active_time_ms, pd.revisit_count, expectedMs);
    pd.completion_status = _upgradeStatus(pd.completion_status, newStatus);
  }, [_accumulate, _getOrCreate]);

  const _enterPage = useCallback((enterPage) => {
    if (enterPage == null) return;
    const s = state.current;
    const pd = _getOrCreate(enterPage);
    if (!pd) return;
    const now = performance.now();
    if (!pd._hasEntered) {
      pd.enter_timestamp = new Date().toISOString();
      pd._hasEntered = true;
    } else {
      pd.revisit_count += 1;
      pd.exit_timestamp = null;
    }
    s.currentPage = enterPage;
    s.currentPageEnterPerfTime = now;
  }, [_getOrCreate]);

  // ── Flush batch to backend ─────────────────────────────────────────────────

  const pageCountRef = useRef(pageCount);
  useEffect(() => { pageCountRef.current = pageCount; }, [pageCount]);

  const _flush = useCallback(() => {
    const s = state.current;
    const sess = sessionRef.current;
    if (!sess?.link_token || !sess?.session_id || !s.sessionStarted) return;

    _accumulate(); // snapshot current page time without resetting

    const now = performance.now();
    const totalElapsedMs = s.sessionStartMs != null ? Math.round(now - s.sessionStartMs) : 0;

    const pageDataSnapshot = Object.values(s.pageData)
      .filter(pd => pd.active_time_ms > 0 || pd._hasEntered)
      .map(pd => {
        // Update completion status for pages currently being read
        const expectedMs = (s.wordsPerPage / s.baselineWpm) * 60_000;
        const liveStatus = _pageStatus(pd.active_time_ms, pd.revisit_count, expectedMs);
        const finalStatus = _upgradeStatus(pd.completion_status, liveStatus);
        return {
          page_number: pd.page_number,
          active_time_ms: Math.round(pd.active_time_ms),
          pause_duration_ms: Math.round(pd.pause_duration_ms || 0),
          revisit_count: pd.revisit_count,
          scroll_percentage: Math.round(pd.scroll_percentage * 10) / 10,
          zoom_level: pd.zoom_level,
          fullscreen_used: pd.fullscreen_used,
          annotations_created: pd.annotations_created,
          copy_attempts: copyCountRef.current[pd.page_number] || 0,
          print_attempts: printCountRef.current[pd.page_number] || 0,
          tab_switch_count: tabSwitchCountRef.current[pd.page_number] || 0,
          visibility_changes: visibilityChangesRef.current[pd.page_number] || 0,
          idle_events: idleEventsRef.current[pd.page_number] || 0,
          completion_status: finalStatus,
          enter_timestamp: pd.enter_timestamp,
          exit_timestamp: pd.exit_timestamp,
        };
      });

    if (pageDataSnapshot.length === 0) return;

    window.SecureDocAPI?.batchReadingEvents(
      sess.link_token,
      sess.session_id,
      pageDataSnapshot,
      {
        total_elapsed_ms: totalElapsedMs,
        total_active_ms: Math.round(s.totalActiveMs),
        started_at: s.sessionStartAt,
        page_count: pageCountRef.current,
        current_page: s.currentPage,
        initial_estimate_ms: null,
      },
    );
  }, [_accumulate]);

  // ── Start session once document is ready ───────────────────────────────────

  useEffect(() => {
    if (session && isDocumentReady) {
      _startSession();
    }
  }, [session, isDocumentReady, _startSession]);

  // ── Handle page changes ────────────────────────────────────────────────────

  const prevPageRef = useRef(null);
  useEffect(() => {
    if (!page || !state.current.sessionStarted) return;
    const prev = prevPageRef.current;
    if (prev !== null && prev !== page) {
      _exitPage(prev);
    }
    _enterPage(page);
    prevPageRef.current = page;
  }, [page, _exitPage, _enterPage]);

  // ── Attach event listeners once (when session is available) ───────────────

  useEffect(() => {
    if (!session) return;
    const s = state.current;

    const onHide = () => {
      if (s.currentPage != null) {
        const pd = _getOrCreate(s.currentPage);
        if (pd) {
          pd.tab_switch_count += 1;
          pd.visibility_changes += 1;
        }
        tabSwitchCountRef.current[s.currentPage] = (tabSwitchCountRef.current[s.currentPage] || 0) + 1;
        visibilityChangesRef.current[s.currentPage] = (visibilityChangesRef.current[s.currentPage] || 0) + 1;
      }
      _pause();
    };
    const onShow = () => _resume();
    const onBlur = () => _pause();
    const onFocus = () => _resume();
    const onInteract = () => _resetIdle();

    const onVisibility = () => { document.hidden ? onHide() : onShow(); };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    document.addEventListener('mousemove', onInteract, { passive: true });
    document.addEventListener('keydown', onInteract, { passive: true });
    document.addEventListener('scroll', onInteract, { passive: true, capture: true });
    document.addEventListener('touchstart', onInteract, { passive: true });

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('mousemove', onInteract);
      document.removeEventListener('keydown', onInteract);
      document.removeEventListener('scroll', onInteract, true);
      document.removeEventListener('touchstart', onInteract);
      if (s.idleTimerId) { clearTimeout(s.idleTimerId); s.idleTimerId = null; }
    };
  }, [session, _pause, _resume, _resetIdle, _getOrCreate]);

  // ── Display update — once per second ──────────────────────────────────────

  useEffect(() => {
    if (!session) return;
    const timer = setInterval(() => {
      const s = state.current;
      const now = performance.now();

      // Live active time = accumulated + current page in-flight
      let liveActive = s.totalActiveMs;
      if (s.isActive && s.currentPageEnterPerfTime != null) {
        liveActive += now - s.currentPageEnterPerfTime;
      }

      // Current page time
      const curPd = s.currentPage != null ? s.pageData[s.currentPage] : null;
      let curPageMs = curPd?.active_time_ms || 0;
      if (s.isActive && s.currentPageEnterPerfTime != null) {
        curPageMs += now - s.currentPageEnterPerfTime;
      }

      const allPages = Object.values(s.pageData);
      const visitedPages = allPages.filter(p => p._hasEntered);
      const completedPages = allPages.filter(p => ['completed', 'revisited'].includes(p.completion_status));
      const validPages = allPages.filter(p => p.active_time_ms > 1000);
      const avgMs = validPages.length > 0
        ? validPages.reduce((sum, p) => sum + p.active_time_ms, 0) / validPages.length
        : null;

      // EWMA reading speed (any page with real time data, not just "completed")
      let speedWpm = null;
      if (validPages.length >= 2) {
        const readings = validPages.map(p => s.wordsPerPage / (p.active_time_ms / 60_000)).filter(r => r > 0 && r < 2000);
        if (readings.length >= 2) {
          let ewma = readings[0];
          for (let i = 1; i < readings.length; i++) ewma = EWMA_ALPHA * readings[i] + (1 - EWMA_ALPHA) * ewma;
          speedWpm = Math.round(Math.max(50, Math.min(700, ewma)));
        }
      }

      const pc = pageCountRef.current;
      const remaining = _estimateRemainingMs(s.pageData, s.currentPage, pc, s.wordsPerPage, s.baselineWpm);
      const completionPct = pc > 0 ? Math.min(100, Math.round((visitedPages.length / pc) * 100)) : 0;

      setDisplay({
        isActive: s.isActive,
        totalActiveMs: Math.round(liveActive),
        estimatedRemainingMs: remaining,
        currentPageActiveMs: Math.round(curPageMs),
        completedPages: completedPages.length,
        pagesVisited: visitedPages.length,
        avgMsPerPage: avgMs != null ? Math.round(avgMs) : null,
        readingSpeedWpm: speedWpm,
        completionPct,
      });
    }, DISPLAY_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [session]);

  // ── Flush interval — every 5 seconds ──────────────────────────────────────

  useEffect(() => {
    if (!session) return;
    const timer = setInterval(_flush, FLUSH_INTERVAL_MS);
    return () => {
      clearInterval(timer);
      _flush(); // final flush on unmount
    };
  }, [session, _flush]);

  // ── Comparative insights (difficulty, this-page average, pace vs. other
  // viewers) — this data is a cross-session server aggregate, unlike
  // everything else in `display` above (which is computed entirely
  // client-side from this viewer's own local timers). Fetched periodically
  // rather than every second since it changes slowly. The backend returns
  // nulls for all three fields unless the link owner has enabled
  // `show_reading_insights`, so `insights` naturally stays null-shaped (and
  // the panel hides itself) when the uploader hasn't opted in — no
  // permission flag needs to be threaded through the frontend to know this.
  const [insights, setInsights] = useState(null);

  useEffect(() => {
    if (!session?.link_token || !session?.session_id || !window.SecureDocAPI?.getViewerReadingSummary) return;
    let cancelled = false;
    const fetchInsights = () => {
      window.SecureDocAPI.getViewerReadingSummary(session.link_token, session.session_id)
        .then(data => {
          if (cancelled || !data) return;
          setInsights({
            difficulty: data.difficulty ?? null,
            currentPageAvgMs: data.current_page_avg_ms ?? null,
            paceVsAverage: data.pace_vs_average ?? null,
          });
        })
        .catch(() => {});
    };
    fetchInsights();
    const timer = setInterval(fetchInsights, 20_000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [session, page]);

  // ── Public surface ─────────────────────────────────────────────────────────

  const onScroll = useCallback((pct) => {
    const pd = _getOrCreate(state.current.currentPage);
    if (pd) pd.scroll_percentage = Math.max(pd.scroll_percentage, pct);
  }, [_getOrCreate]);

  const onZoomChange = useCallback((zoom) => {
    const pd = _getOrCreate(state.current.currentPage);
    if (pd) pd.zoom_level = zoom;
  }, [_getOrCreate]);

  const onFullscreen = useCallback((active) => {
    if (!active) return;
    const pd = _getOrCreate(state.current.currentPage);
    if (pd) pd.fullscreen_used = true;
  }, [_getOrCreate]);

  const onCopyAttempt = useCallback(() => {
    const p = state.current.currentPage;
    if (p != null) copyCountRef.current[p] = (copyCountRef.current[p] || 0) + 1;
  }, []);

  const onPrintAttempt = useCallback(() => {
    const p = state.current.currentPage;
    if (p != null) printCountRef.current[p] = (printCountRef.current[p] || 0) + 1;
  }, []);

  const onAnnotationCreated = useCallback(() => {
    const pd = _getOrCreate(state.current.currentPage);
    if (pd) pd.annotations_created += 1;
  }, [_getOrCreate]);

  return {
    display,
    insights,
    onScroll,
    onZoomChange,
    onFullscreen,
    onCopyAttempt,
    onPrintAttempt,
    onAnnotationCreated,
    _flush,
  };
}
