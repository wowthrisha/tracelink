import { LAYOUT, ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, ZOOM_PRESETS, _saveLayoutPref } from '../constants/viewer.js';
import { _errMsg } from '../utils/viewer.js';
import { useTextLoader } from '../hooks/useTextLoader.js';
import { useLinksSidecar } from '../hooks/useLinksSidecar.js';
import { useSearchHighlights } from '../hooks/useSearchHighlights.js';
import { useAnnotations } from '../hooks/useAnnotations.js';
import { useViewerLayout } from '../hooks/useViewerLayout.js';
import { usePageLoader } from '../hooks/usePageLoader.js';
import { useViewerSession } from '../hooks/useViewerSession.js';
import { useReadingAnalytics } from '../hooks/useReadingAnalytics.js';
import { useToast } from '../contexts/toast.jsx';
import { ViewerToolbar } from '../components/ViewerToolbar.jsx';
import { C, mono } from '../constants/tokens.js';
import { LaserPointer } from '../components/LaserPointer.jsx';
import { RectMagnifier } from '../components/RectMagnifier.jsx';
import { SearchPanel } from '../components/SearchPanel.jsx';
import { InsightsModal } from '../components/InsightsModal.jsx';
import { ReadingStatusBar } from '../components/ReadingStatusBar.jsx';
import { LinksPanel } from '../components/LinksPanel.jsx';
import { TocSidebar } from '../components/TocSidebar.jsx';
import { PageThumb } from '../components/PageThumb.jsx';
import { Modal, Header } from '../components/atoms.jsx';
import { AccessGate } from '../components/AccessGate.jsx';
import { ViewerInfoPanel } from '../components/ViewerInfoPanel.jsx';
import { AnnotationLayer } from '../components/AnnotationLayer.jsx';
import { CommentPopup } from '../components/CommentPopup.jsx';
import { DocumentPicker } from '../components/DocumentPicker.jsx';

const { useState, useEffect, useRef } = React;

export function ViewerScreen({ doc, publicToken, onSelectDoc, onBack }) {
  const toast = useToast();
  const [showInfo, setShowInfo] = useState(false);
  // Phase 7: in-viewer search
  const [showSearch, setShowSearch] = useState(false);
  // Pages panel open by default on desktop; TOC closed by default
  const [showToc, setShowToc] = useState(false);
  // Premium: laser pointer, magnifier, fullscreen, page jump
  const [showLaser, setShowLaser] = useState(false);
  const [showMagnifier, setShowMagnifier] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const [insightsData, setInsightsData] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [readingData, setReadingData] = useState(null);
  const [readingLoading, setReadingLoading] = useState(false);
  const [showLinks, setShowLinks] = useState(false);
  const [showPageList, setShowPageList] = useState(typeof window !== 'undefined' ? window.innerWidth > 640 : true);

  // Inject point for setPage(1) — breaks session↔layout circular dep
  const _setPageRef = useRef(null);

  // Session lifecycle, gate management, auth, and DRM protections
  const {
    session, blurred, initializing,
    gateInfo, gateError, setGateError,
    pendingToken,
    reinitRef, doValidate,
  } = useViewerSession(doc, publicToken, { onValidated: () => _setPageRef.current?.() });


  const docName = doc?.filename || doc?.name || session?.document_filename || 'Document';
  const docId = doc?.id || '';
  const PAGE_COUNT = session?.page_count || 1;
  const isTextDoc = !!(session?.doc_type && ['txt', 'md', 'log'].includes(session.doc_type));

  // Navigation, layout, and keyboard/session-persistence effects
  const {
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
  } = useViewerLayout(session, { onToggleSearch: () => setShowSearch(v => !v) });

  // Inject setPage into the stable ref so useViewerSession.doValidate can reset to page 1
  _setPageRef.current = () => setPage(1);

  const { textContent, textLoading, textError } = useTextLoader(session, page, isTextDoc);

  // Page image loading, caching, prefetch, and crossfade
  const {
    imgSrc, imgLoading, pageError,
    prevImgSrc, imgReady, setImgReady,
    imgSrc2, imgLoading2, page2Error,
    pageAspectRatio, setPageAspectRatio,
    pageImgRef, pageContainerRef,
  } = usePageLoader({ session, page, twoPageMode, isTextDoc, onAuth401: () => reinitRef.current?.() });

  const isTwoPage = twoPageMode;

  // Feature 2: search highlights — state, refs, word-position load effect
  const {
    searchHighlightQuery, setSearchHighlightQuery,
    searchHighlights,
    searchResultPages, setSearchResultPages,
    activeHighlightIdx, setActiveHighlightIdx,
    wordPositionsRef, wordPositionsFetched,
  } = useSearchHighlights(session, page);

  // Feature 1: hyperlink sidecar — state, refs, and load/auto-extract effects
  const {
    pageLinksRef,
    linksLoaded, setLinksLoaded,
    visitedLinks, setVisitedLinks,
    setSidecarExtracted,
  } = useLinksSidecar(session, doc?.id, isTextDoc, {
    onAutoExtractReset: () => {
      wordPositionsRef.current = {};
      wordPositionsFetched.current = false;
    },
  });

  // Annotations, bookmarks, drawing, and comment-thread state + load effects
  const {
    annotTool, setAnnotTool,
    annotColor, setAnnotColor,
    annotThickness, setAnnotThickness,
    annotUndoStack, setAnnotUndoStack,
    pageAnnotations, setPageAnnotations,
    commentDraft, setCommentDraft,
    threadView, setThreadView,
    threadReplyText, setThreadReplyText,
    threadReplySending, setThreadReplySending,
    bookmarks, setBookmarks,
    annotCacheRef,
  } = useAnnotations(session, page, isTextDoc);

  // Reading Intelligence Engine — active-time tracking
  // isDocumentReady latches true once the first page loads and never resets to false.
  // This prevents the hook from re-initializing on every page navigation (imgReady toggles
  // false→true on each page load which would otherwise reset the session timer).
  const docReadyLatchRef = useRef(false);
  if (session && imgReady) docReadyLatchRef.current = true;
  const isDocumentReady = docReadyLatchRef.current;
  const { display: readingDisplay } = useReadingAnalytics(session, page, PAGE_COUNT, isDocumentReady);

  useEffect(() => {
    if (document.getElementById('sdoc-vx-styles')) return;
    const s = document.createElement('style');
    s.id = 'sdoc-vx-styles';
    s.textContent = '@keyframes sdoc-shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}';
    document.head.appendChild(s);
  }, []);

  // All hooks have run — safe to conditionally return now
  if (gateInfo && !session) {
    return (
      <AccessGate
        gateInfo={gateInfo}
        error={gateError}
        onSubmit={(email, pw) => { setGateError(null); doValidate(pendingToken, email, pw); }}
      />
    );
  }

  // No document selected (authenticated mode only — public token always has a doc).
  // Show an inline picker so the user can select without leaving the Viewer tab.
  if (!docId && !publicToken && !initializing) {
    return (
      <div data-testid="viewer-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Header screen="viewer" />
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          <DocumentPicker onSelect={(d) => { if (onSelectDoc) onSelectDoc(d); }} />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="viewer-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      {/* Chrome-style top toolbar — all viewer controls in one compact row */}
      <ViewerToolbar
        onBack={onBack}
        doc={doc}
        docName={docName}
        isTextDoc={isTextDoc}
        page={page} PAGE_COUNT={PAGE_COUNT}
        pageInputStr={pageInputStr} setPageInputStr={setPageInputStr} setPage={setPage}
        goPrev={goPrev} goNext={goNext}
        layoutMode={layoutMode} customZoom={customZoom}
        _zoomBy={_zoomBy} _zoomTo={_zoomTo} _setLayout={_setLayout}
        LAYOUT={LAYOUT} ZOOM_STEP={ZOOM_STEP} ZOOM_PRESETS={ZOOM_PRESETS}
        showLaser={showLaser} setShowLaser={setShowLaser}
        showMagnifier={showMagnifier} setShowMagnifier={setShowMagnifier}
        showInsights={showInsights} setShowInsights={v => {
          setShowInsights(v);
          const heatmapDocId = doc?.id || session?.document_id;
          if (v && heatmapDocId) {
            // Fetch legacy page heatmap
            if (!insightsData && !insightsLoading) {
              setInsightsLoading(true);
              window.SecureDocAPI.getPageHeatmap(heatmapDocId)
                .then(d => setInsightsData(d))
                .catch(() => setInsightsData(null))
                .finally(() => setInsightsLoading(false));
            }
            // Fetch reading analytics (summary, heatmap, insights, viewers)
            if (!readingData && !readingLoading) {
              setReadingLoading(true);
              Promise.all([
                window.SecureDocAPI.getDocumentReadingSummary(heatmapDocId).catch(() => null),
                window.SecureDocAPI.getDocumentReadingHeatmap(heatmapDocId).catch(() => null),
                window.SecureDocAPI.getDocumentReadingInsights(heatmapDocId).catch(() => null),
                window.SecureDocAPI.getDocumentReadingViewers(heatmapDocId).catch(() => null),
              ]).then(([summary, heatmap, insights, viewers]) => {
                setReadingData({ summary, heatmap, insights, viewers });
              }).finally(() => setReadingLoading(false));
            }
          }
        }}
        hasInsights={!!(doc?.id || session?.document_id)}
        showLinks={showLinks} setShowLinks={setShowLinks}
        linksCount={linksLoaded ? (pageLinksRef.current[page] || []).length : 0}
        isFullscreen={isFullscreen} toggleFullscreen={toggleFullscreen}
        showToc={showToc} setShowToc={setShowToc}
        showSearch={showSearch} setShowSearch={setShowSearch}
        showInfo={showInfo} setShowInfo={setShowInfo}
        showPageList={showPageList} setShowPageList={setShowPageList}
        canDownload={!!session?.permissions?.can_download}
        canPrint={!!session?.permissions?.can_print}
        canInfo={session ? !!session?.permissions?.enable_info : true}
        canAnnotate={!!session?.permissions?.can_annotate}
        annotTool={annotTool} setAnnotTool={setAnnotTool}
        annotColor={annotColor} setAnnotColor={setAnnotColor}
        annotThickness={annotThickness} setAnnotThickness={setAnnotThickness}
        annotUndoStack={annotUndoStack}
        onAnnotUndo={async () => {
          if (annotUndoStack.length === 0 || !session) return;
          const last = annotUndoStack[annotUndoStack.length - 1];
          try {
            await window.SecureDocAPI.deleteAnnotation(session.link_token, last.annotId, session.session_id);
            setAnnotUndoStack(s => s.slice(0, -1));
            if (last.page === page) {
              const updated = pageAnnotations.filter(a => a.id !== last.annotId);
              annotCacheRef.current.set(page, updated);
              setPageAnnotations(updated);
            } else {
              annotCacheRef.current.delete(last.page);
            }
          } catch (e) { toast(_errMsg(e, 'Undo failed'), 'error'); }
        }}
        bookmarked={bookmarks.has(page)}
        onToggleBookmark={async () => {
          if (!session) return;
          try {
            const res = await window.SecureDocAPI.toggleBookmark(session.link_token, page, session.session_id);
            setBookmarks(prev => {
              const next = new Set(prev);
              if (res.action === 'added') next.add(page); else next.delete(page);
              return next;
            });
          } catch (e) { toast(_errMsg(e, 'Bookmark failed'), 'error'); }
        }}
        onDownload={async () => {
          if (!session?.permissions?.can_download) return;
          toast('Preparing download…', 'info');
          try {
            await window.SecureDocAPI.downloadDocument(session.link_token, session.session_id, session.document_filename);
            toast('Download complete', 'success');
          } catch (e) { toast(_errMsg(e, 'Download failed'), 'error'); }
        }}
        onPrint={() => {
          if (session?.permissions?.can_print) {
            window.print();
            window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'printed');
          }
        }}
        rotation={rotation} onRotate={() => setRotation(r => (r + 90) % 360)}
        isTwoPage={isTwoPage} onToggleTwoPage={() => setTwoPageMode(v => !v)}
        C={C} mono={mono}
      />

      {/* Feature 3: Search panel — fixed viewport overlay, never pushes content */}
      {showSearch && session && (
        <SearchPanel
          session={session}
          onClose={() => { setShowSearch(false); setSearchHighlightQuery(''); setActiveHighlightIdx(0); setSearchResultPages(new Set()); }}
          onNavigate={p => setPage(p)}
          onQueryChange={q => { setSearchHighlightQuery(q); if (!q) setSearchResultPages(new Set()); }}
          onActiveChange={idx => setActiveHighlightIdx(idx)}
          onResultsChange={results => setSearchResultPages(new Set((results || []).map(r => r.page)))}
        />
      )}

      {/* Feature 7: Insights modal — fixed overlay, owner-only */}
      {showInsights && (doc?.id || session?.document_id) && (
        <InsightsModal
          docName={docName}
          loading={insightsLoading}
          data={insightsData}
          readingData={readingData}
          readingLoading={readingLoading}
          onClose={() => setShowInsights(false)}
          C={C} mono={mono}
        />
      )}

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Universal TOC sidebar — PDF (page nav) and text/docx/doc (chunk nav) */}
        {showToc && session && (
          <TocSidebar
            linkToken={session.link_token}
            sessionId={session.session_id}
            currentPage={page}
            pageCount={PAGE_COUNT}
            docType={session.doc_type || 'pdf'}
            onNavigate={p => setPage(p)}
            onClose={() => setShowToc(false)}
          />
        )}

        {/* Thumbnail strip — PDF only, toggleable via Pages button */}
        {!isTextDoc && showPageList && (
          <div className="sidebar-mobile-hidden" style={{
            width: 86, background: '#0d1117', borderRight: '1px solid rgba(255,255,255,0.06)',
            overflow: 'auto', padding: '10px 6px', display: 'flex', flexDirection: 'column', gap: 5, flexShrink: 0
          }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: 'rgba(130,142,158,0.6)', textTransform: 'uppercase', padding: '0 4px 6px', borderBottom: '1px solid rgba(255,255,255,0.05)', marginBottom: 4 }}>Pages</div>
            {Array.from({ length: PAGE_COUNT }, (_, i) => i + 1).map(p => (
              <PageThumb
                key={p} p={p} active={page === p} onClick={() => setPage(p)}
                token={session?.link_token} sessionId={session?.session_id}
                docReady={session?.doc_status === 'ready'}
              />
            ))}
          </div>
        )}

        {/* Main canvas */}
        <div style={{
          flex: 1, overflow: 'auto', background: '#060809',
          display: 'flex', flexDirection: 'column', alignItems: 'safe center', padding: '16px 0', gap: 10,
          position: 'relative'
        }}
          onTouchStart={e => { touchRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }; }}
          onTouchEnd={e => {
            if (!touchRef.current.x) return;
            const dx = e.changedTouches[0].clientX - touchRef.current.x;
            const dy = e.changedTouches[0].clientY - touchRef.current.y;
            if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 45) {
              if (dx < 0) goNext(); else goPrev();
            }
            touchRef.current = { x: null, y: null };
          }}
        >
          {/* Reading progress bar */}
          {session && PAGE_COUNT > 0 && (
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, zIndex: 10, pointerEvents: 'none' }}>
              <div style={{
                height: '100%',
                width: `${PAGE_COUNT > 1 ? Math.round(((page - 1) / (PAGE_COUNT - 1)) * 100) : 100}%`,
                background: 'linear-gradient(90deg, #5ac8d0, #3db8c0)',
                transition: 'width 0.4s ease',
                boxShadow: '0 0 4px #5ac8d0',
              }} />
            </div>
          )}

          {initializing && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: C.textMuted, marginTop: 40 }}>
              <span style={{ display: 'inline-block', width: 18, height: 18, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
              Opening secure viewer…
            </div>
          )}
          {!initializing && session && !isTextDoc && (() => {
            const rotated90 = rotation === 90 || rotation === 270;
            // Compute page dimensions based on layout mode.
            // In two-page mode: FIT_WIDTH → each page fills its flex slot (width:100%),
            // FIT_HEIGHT → each page fills viewport height, CUSTOM → fixed px.
            // The wrapping flex container splits available width for two-page layout.
            const _pgStyle = (() => {
              if (layoutMode === LAYOUT.AUTO) {
                // Auto: fit width on narrow viewports, fit height on wide landscape
                const isLandscapePage = pageAspectRatio && parseFloat(pageAspectRatio.split('/')[0]) > parseFloat(pageAspectRatio.split('/')[1]);
                if (isLandscapePage) {
                  return isTwoPage
                    ? { width: 'auto', height: 'calc(100vh - 74px)' }
                    : { width: 'auto', maxWidth: '100%', height: 'calc(100vh - 74px)' };
                }
                return { width: '100%', maxWidth: '100%', height: undefined };
              }
              if (layoutMode === LAYOUT.FIT_WIDTH) {
                return { width: '100%', maxWidth: '100%', height: undefined };
              }
              if (layoutMode === LAYOUT.FIT_HEIGHT) {
                // In 2-page mode don't clamp maxWidth — pages must size to their height
                // freely so both pages fill viewport height side-by-side. Canvas overflow:auto
                // handles horizontal scrolling when the spread is wider than the viewport.
                return isTwoPage
                  ? { width: 'auto', height: 'calc(100vh - 74px)' }
                  : { width: 'auto', maxWidth: '100%', height: 'calc(100vh - 74px)' };
              }
              if (layoutMode === LAYOUT.ACTUAL) {
                // 100% = natural page size (72dpi basis: letter = 612px wide)
                return { width: '612px', maxWidth: 'none', height: undefined };
              }
              // CUSTOM zoom: 100% = 590px (fits a letter-size PDF at typical DPI)
              return { width: `${customZoom * 5.9}px`, maxWidth: '100%', height: undefined };
            })();
            const _arBase = pageAspectRatio || '8.5/11';
            const _arRot = pageAspectRatio ? pageAspectRatio.split('/').reverse().join('/') : '11/8.5';
            const _rotStyle = rotation !== 0 ? { transform: `rotate(${rotation}deg)`, transformOrigin: 'center center' } : {};
            const _pageEl = (
            <div ref={pageContainerRef} className="viewer-page" style={{
              position: 'relative', ...(_pgStyle),
              aspectRatio: rotated90 ? _arRot : _arBase,
              flexShrink: 0, transition: 'width .25s ease, height .25s ease',
              borderRadius: 2, overflow: 'hidden',
              boxShadow: '0 2px 8px rgba(0,0,0,0.5), 0 8px 48px rgba(0,0,0,0.8), 0 20px 60px rgba(0,0,0,0.35)',
            }}
              onContextMenu={e => e.preventDefault()}
              onTouchStart={e => {
                if (e.touches.length === 2) {
                  const dx = e.touches[0].clientX - e.touches[1].clientX;
                  const dy = e.touches[0].clientY - e.touches[1].clientY;
                  touchRef.current.pinchDist = Math.sqrt(dx * dx + dy * dy);
                } else {
                  touchRef.current.pinchDist = null;
                }
              }}
              onTouchMove={e => {
                if (e.touches.length === 2 && touchRef.current.pinchDist != null) {
                  e.preventDefault();
                  const dx = e.touches[0].clientX - e.touches[1].clientX;
                  const dy = e.touches[0].clientY - e.touches[1].clientY;
                  const dist = Math.sqrt(dx * dx + dy * dy);
                  const ratio = dist / touchRef.current.pinchDist;
                  touchRef.current.pinchDist = dist;
                  // Each move event = scale the zoom by the delta ratio
                  setCustomZoom(z => {
                    const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(z * ratio)));
                    if (next !== z) {
                      setLayoutMode(LAYOUT.CUSTOM);
                      _saveLayoutPref(LAYOUT.CUSTOM, next);
                    }
                    return next;
                  });
                }
              }}>

              {/* Phase 7 crossfade: background layer holds previous page while next loads */}
              {prevImgSrc && prevImgSrc !== imgSrc && (
                <img
                  src={prevImgSrc}
                  draggable={false}
                  style={{
                    position: 'absolute', inset: 0,
                    width: '100%', height: '100%', objectFit: 'contain', display: 'block',
                    userSelect: 'none', pointerEvents: 'none',
                    filter: blurred ? 'blur(14px)' : 'none',
                    opacity: imgReady ? 0 : 1,
                    transition: 'opacity .22s ease, filter .3s',
                    ..._rotStyle,
                  }}
                  alt=""
                />
              )}

              {/* Current page — fades in when browser has decoded the new image */}
              {imgSrc && (
                <img ref={pageImgRef} src={imgSrc} draggable={false}
                  onLoad={e => {
                    setImgReady(true);
                    const { naturalWidth: nw, naturalHeight: nh } = e.target;
                    if (nw > 0 && nh > 0) setPageAspectRatio(`${nw}/${nh}`);
                  }}
                  onError={() => setImgReady(true)}
                  style={{
                    width: '100%', height: '100%', objectFit: 'contain', display: 'block',
                    userSelect: 'none', WebkitTouchCallout: 'none', WebkitUserSelect: 'none',
                    filter: blurred ? 'blur(14px)' : 'none',
                    opacity: imgReady ? 1 : 0,
                    transition: 'opacity .22s ease, filter .3s',
                    ..._rotStyle,
                  }}
                  alt={`Page ${page}`}
                />
              )}

              {/* Non-blocking loading badge — floats over image, doesn't obscure previous page */}
              {imgLoading && (
                <div style={{
                  position: 'absolute', bottom: 8, right: 8, zIndex: 2, pointerEvents: 'none',
                  display: 'flex', alignItems: 'center', gap: 5,
                  background: 'rgba(6,8,9,0.72)', borderRadius: 20, padding: '4px 10px'
                }}>
                  <span style={{ display: 'inline-block', width: 12, height: 12, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
                  <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>p.{page}</span>
                </div>
              )}

              {pageError && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.surface, flexDirection: 'column', gap: 10, padding: '20px 24px' }}>
                  <span style={{ fontSize: 22, color: 'rgba(224,154,69,0.7)' }}>⚠</span>
                  <span style={{ ...mono, fontSize: 11, color: C.textMuted, textAlign: 'center', lineHeight: 1.5 }}>{pageError}</span>
                </div>
              )}

              {blurred && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(6,8,9,0.4)' }}>
                  <div style={{ ...mono, fontSize: 11, color: C.teal2, padding: '8px 16px', background: 'rgba(6,8,9,0.85)', borderRadius: 6, border: `1px solid ${C.borderMed}` }}>Focus window to resume</div>
                </div>
              )}
              <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none',
                background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.025) 3px, rgba(0,0,0,0.025) 4px)'
              }} />
              {/* Premium: light-sweep shimmer — purely cosmetic, server-side watermark unaffected */}
              <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 2,
                background: 'linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.022) 50%, transparent 60%)',
                backgroundSize: '250% 100%',
                animation: 'sdoc-shimmer 5s ease-in-out infinite',
              }} />

              {/* Feature 2: Search highlight overlays — yellow (inactive) / orange (active) */}
              {searchHighlights.map((m, i) => {
                const isActive = i === activeHighlightIdx;
                return (
                  <div key={i} style={{
                    position: 'absolute',
                    left: `${m.x * 100}%`, top: `${m.y * 100}%`,
                    width: `${m.w * 100}%`, height: `${m.h * 100}%`,
                    background: isActive ? 'rgba(255,145,0,0.55)' : 'rgba(255,220,0,0.32)',
                    border: isActive ? '1.5px solid rgba(255,120,0,0.85)' : '1px solid rgba(255,200,0,0.45)',
                    borderRadius: 1, pointerEvents: 'none', zIndex: 6,
                    boxShadow: isActive ? '0 0 6px rgba(255,145,0,0.4)' : 'none',
                    transition: 'background .15s, border .15s, box-shadow .15s',
                  }} />
                );
              })}

              {/* Feature 2 fallback: visible match banner when word positions unavailable */}
              {searchHighlightQuery && searchResultPages.has(page) && searchHighlights.length === 0 && (
                <>
                  <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                    pointerEvents: 'none', zIndex: 5,
                    border: '3px solid rgba(255,210,0,0.75)',
                    borderRadius: 2, boxSizing: 'border-box',
                  }} />
                  <div style={{
                    position: 'absolute', top: 8, left: '50%', transform: 'translateX(-50%)',
                    zIndex: 8, pointerEvents: 'none',
                    background: 'rgba(255,218,0,0.93)',
                    borderRadius: 12, padding: '3px 14px',
                    fontFamily: "'DM Sans',sans-serif", fontSize: 10, fontWeight: 700,
                    color: '#4a2e00', whiteSpace: 'nowrap', letterSpacing: '0.02em',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                  }}>
                    ⌕ Match found on this page
                  </div>
                </>
              )}

              {/* Feature 1: Annotation-based hyperlink overlays (links with PDF coordinates) */}
              {linksLoaded && (pageLinksRef.current[page] || [])
                .filter(link => link.x != null && link.y != null)
                .map((link, i) => {
                  let safeHref = null;
                  try { const u = new URL(link.url); if (/^https?:$/i.test(u.protocol)) safeHref = link.url; } catch {}
                  return (
                    <a key={i} href={safeHref || '#'} target={safeHref ? '_blank' : undefined} rel="noopener noreferrer"
                      onClick={safeHref ? undefined : e => e.preventDefault()}
                      style={{
                        position: 'absolute',
                        left: `${link.x * 100}%`, top: `${link.y * 100}%`,
                        width: `${link.w * 100}%`, height: `${link.h * 100}%`,
                        cursor: safeHref ? 'pointer' : 'default', pointerEvents: 'auto', zIndex: 7,
                        display: 'block',
                      }}
                      title={link.url}
                    />
                  );
                })}

              {/* Annotation overlay layer — rendered above page image, never modifies it */}
              {session?.permissions?.can_annotate && (
                <AnnotationLayer
                  annotations={pageAnnotations}
                  activeTool={annotTool}
                  sessionPrefix={session?.session_id ? session.session_id.slice(0, 6) : ''}
                  commentDraft={commentDraft}
                  onDraw={async (coords, type) => {
                    if (type === 'comment' || type === 'sticky_note') {
                      setCommentDraft({ coords, type, x: coords.x, y: coords.y });
                      return;
                    }
                    try {
                      const colorFor = (t) => {
                        if (t === 'highlight') return annotColor || '#FFE066';
                        if (t === 'rectangle') return annotColor || 'rgba(90,200,208,0.25)';
                        if (t === 'draw') return annotColor || '#5ac8d0';
                        return annotColor || '#5ac8d0';
                      };
                      const annot = await window.SecureDocAPI.createAnnotation(
                        session.link_token,
                        { page_number: page, annotation_type: type, coords, color: colorFor(type), thickness: annotThickness },
                        session.session_id
                      );
                      const updated = [...pageAnnotations, annot];
                      annotCacheRef.current.set(page, updated);
                      setPageAnnotations(updated);
                      setAnnotUndoStack(s => [...s, { annotId: annot.id, page }]);
                    } catch (e) { toast(_errMsg(e, 'Failed to save annotation'), 'error'); }
                  }}
                  onDelete={async (annotId) => {
                    try {
                      await window.SecureDocAPI.deleteAnnotation(session.link_token, annotId, session.session_id);
                      const updated = pageAnnotations.filter(a => a.id !== annotId);
                      annotCacheRef.current.set(page, updated);
                      setPageAnnotations(updated);
                      setAnnotUndoStack(s => s.filter(u => u.annotId !== annotId));
                    } catch (e) { toast(_errMsg(e, 'Failed to delete annotation'), 'error'); }
                  }}
                  onOpenThread={async (a) => {
                    setThreadReplyText('');
                    setThreadView({ rootAnnot: a, root: null, replies: [], loading: true });
                    try {
                      const data = await window.SecureDocAPI.getAnnotationThread(session.link_token, a.id, session.session_id);
                      setThreadView({ rootAnnot: a, root: data.root || data, replies: data.replies || [], loading: false });
                    } catch (e) {
                      setThreadView(null);
                      toast(_errMsg(e, 'Failed to load thread'), 'error');
                    }
                  }}
                  C={C} mono={mono}
                />
              )}
              {/* Comment text input popup */}
              {commentDraft && (
                <CommentPopup
                  draft={commentDraft}
                  onSave={async (text) => {
                    const draft = commentDraft;
                    setCommentDraft(null);
                    if (!text.trim()) return;
                    try {
                      const annot = await window.SecureDocAPI.createAnnotation(
                        session.link_token,
                        { page_number: page, annotation_type: draft.type || 'comment', coords: draft.coords, comment_text: text.trim(), color: annotColor || '#5ac8d0' },
                        session.session_id
                      );
                      const updated = [...pageAnnotations, annot];
                      annotCacheRef.current.set(page, updated);
                      setPageAnnotations(updated);
                      setAnnotUndoStack(s => [...s, { annotId: annot.id, page }]);
                    } catch (e) { toast(_errMsg(e, 'Failed to save comment'), 'error'); }
                  }}
                  onCancel={() => setCommentDraft(null)}
                  C={C}
                />
              )}
            </div>
            );
            if (!isTwoPage) return _pageEl;
            // Two-page view: each page in a flex-1 slot so W/H/custom all work correctly.
            // W-fit → each slot is 50% wide, page fills its slot.
            // H-fit → each page fills viewport height, slots auto-size to content.
            // Custom → fixed px per page, slots shrink to content.
            const _fitWidth = layoutMode === LAYOUT.FIT_WIDTH || layoutMode === LAYOUT.AUTO;
            const _slotStyle = _fitWidth
              ? { flex: 1, minWidth: 0, display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }
              : { flexShrink: 0, display: 'flex', alignItems: 'flex-start', justifyContent: 'center' };
            // FIT_WIDTH/AUTO needs width:100% so flex-1 slots split the canvas evenly.
            // FIT_HEIGHT/CUSTOM/ACTUAL: no explicit width — each page sizes to its natural height,
            // canvas 'safe center' aligns left when spread overflows (enabling horizontal scroll).
            const _wrapStyle = _fitWidth
              ? { display: 'flex', flexDirection: 'row', gap: 2, alignItems: 'flex-start', justifyContent: 'center', width: '100%' }
              : { display: 'flex', flexDirection: 'row', gap: 2, alignItems: 'flex-start' };
            return (
              <div style={_wrapStyle}>
                <div style={_slotStyle}>{_pageEl}</div>
                {page + 1 <= PAGE_COUNT && (
                  <div style={_slotStyle}>
                    <div style={{ position: 'relative', ..._pgStyle, aspectRatio: rotated90 ? _arRot : _arBase, flexShrink: 0, borderRadius: 2, overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.5), 0 8px 48px rgba(0,0,0,0.8)' }} onContextMenu={e => e.preventDefault()}>
                      {imgSrc2 && <img src={imgSrc2} draggable={false} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', userSelect: 'none', WebkitUserSelect: 'none', ..._rotStyle }} alt={`Page ${page + 1}`} />}
                      {imgLoading2 && <div style={{ position: 'absolute', bottom: 8, right: 8, zIndex: 2, background: 'rgba(6,8,9,0.72)', borderRadius: 20, padding: '4px 10px' }}><span style={{ display: 'inline-block', width: 12, height: 12, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} /></div>}
                      {page2Error && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.surface, flexDirection: 'column', gap: 8 }}><span style={{ fontSize: 18, color: 'rgba(224,154,69,0.7)' }}>⚠</span><span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{page2Error}</span></div>}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}


          {!initializing && session && isTextDoc && (
            <div className="viewer-page" style={{
              position: 'relative', width: '100%', maxWidth: 800, flexShrink: 0,
              borderRadius: 2, overflow: 'hidden', boxShadow: '0 8px 48px rgba(0,0,0,0.7)',
              background: C.surface
            }}
              onContextMenu={e => e.preventDefault()}>
              {textLoading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', flexDirection: 'column', gap: 10 }}>
                  <span style={{ display: 'inline-block', width: 22, height: 22, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
                  <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>Loading chunk {page}…</span>
                </div>
              )}
              {!textLoading && textError && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', flexDirection: 'column', gap: 10 }}>
                  <span style={{ fontSize: 22, color: 'rgba(224,154,69,0.7)' }}>⚠</span>
                  <span style={{ ...mono, fontSize: 11, color: C.textMuted, textAlign: 'center', lineHeight: 1.5 }}>{textError}</span>
                </div>
              )}
              {!textLoading && !textError && (
                <pre style={{
                  margin: 0, padding: '20px 24px',
                  fontFamily: 'ui-monospace, "SFMono-Regular", Consolas, monospace',
                  fontSize: 13, lineHeight: 1.7, color: '#e2e8f0',
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowX: 'hidden',
                  userSelect: session?.permissions?.can_copy ? 'text' : 'none',
                  WebkitUserSelect: session?.permissions?.can_copy ? 'text' : 'none',
                  filter: blurred ? 'blur(14px)' : 'none', transition: 'filter .3s',
                  minHeight: 200
                }}>
                  {textContent}
                </pre>
              )}
              {/* watermark overlay — pointer-events:none so it doesn't block selection */}
              {session?.watermark_text && (
                <div style={{
                  position: 'absolute', inset: 0, pointerEvents: 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  overflow: 'hidden', userSelect: 'none'
                }}>
                  <div style={{
                    ...mono, fontSize: 16, fontWeight: 700,
                    color: 'rgba(90,200,208,0.18)',
                    transform: 'rotate(-30deg)', whiteSpace: 'nowrap', letterSpacing: '0.05em'
                  }}>
                    {session.watermark_text}
                  </div>
                </div>
              )}
              {blurred && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(6,8,9,0.4)' }}>
                  <div style={{ ...mono, fontSize: 11, color: C.teal2, padding: '8px 16px', background: 'rgba(6,8,9,0.85)', borderRadius: 6, border: `1px solid ${C.borderMed}` }}>Focus window to resume</div>
                </div>
              )}
            </div>
          )}
          {!initializing && !session && (
            <div style={{ textAlign: 'center', color: C.textMuted, marginTop: 40 }}>
              <div style={{ fontSize: 13, marginBottom: 8 }}>Document not ready for viewing</div>
              <div style={{ ...mono, fontSize: 10, color: C.textDim }}>Status: {doc?.status} — wait for processing to complete</div>
            </div>
          )}

        </div>

        {/* Info panel */}
        {showInfo && (
          <div style={{
            width: 230, background: C.surfaceAlt, borderLeft: `1px solid ${C.border}`,
            padding: 16, overflow: 'auto', flexShrink: 0
          }} className="slide-in">
            <ViewerInfoPanel doc={doc} docId={docId} page={page} session={session} pageCount={PAGE_COUNT}
              onSidecarExtract={() => {
                // Reset sidecar caches so next page load re-fetches
                pageLinksRef.current = {};
                setLinksLoaded(false);
                wordPositionsRef.current = {};
                wordPositionsFetched.current = false;
                setSidecarExtracted(true);
              }}
            />
          </div>
        )}
      </div>

      {/* Reading Intelligence Engine — viewer-side status bar */}
      {session && (
        <ReadingStatusBar
          display={readingDisplay}
          page={page}
          pageCount={PAGE_COUNT}
        />
      )}

      {/* Feature 5: Laser pointer — GPU-accelerated, ref-based (no setState on mousemove) */}
      <LaserPointer active={showLaser} />
      {/* Feature 4: Rectangular magnifier */}
      <RectMagnifier active={showMagnifier} imgSrc={imgSrc} pageContainerRef={pageContainerRef} />
      {/* Feature 1b: Links side panel — fixed right overlay, 30% width, per-page */}
      {showLinks && session && (
        <LinksPanel
          page={page}
          pageLinksRef={pageLinksRef}
          visitedLinks={visitedLinks}
          onVisit={setVisitedLinks}
          onClose={() => setShowLinks(false)}
          C={C} mono={mono}
        />
      )}

      {/* Part 5: comment-thread modal — viewer sees the original comment + all replies, no dashboard needed */}
      <Modal open={!!threadView} onClose={() => setThreadView(null)} title="Comment Thread" width={420}>
        {threadView?.loading && (
          <div style={{ ...mono, fontSize: 11, color: C.textMuted, textAlign: 'center', padding: '16px 0' }}>Loading thread…</div>
        )}
        {threadView && !threadView.loading && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{
                ...mono, fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                color: threadView.root?.resolved_at ? '#7CCB7C' : C.teal2,
                background: threadView.root?.resolved_at ? 'rgba(124,203,124,0.12)' : 'rgba(90,200,208,0.12)',
              }}>
                {threadView.root?.resolved_at ? 'RESOLVED' : 'OPEN'}
              </span>
              <span style={{ ...mono, fontSize: 10, color: C.textDim }}>Page {threadView.root?.page_number}</span>
            </div>

            {(() => {
              // Unified chronological timeline: root + replies, oldest first —
              // reads as one continuous conversation, not a "comment + nested replies" tree.
              const timeline = [
                ...(threadView.root ? [threadView.root] : []),
                ...(threadView.replies || []),
              ].slice().sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
              const timeOnly = (iso) => iso ? new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '';
              return (
                <div style={{ maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {timeline.map((m, i) => {
                    const isUploader = m.author_role === 'uploader';
                    return (
                      <div key={m.id || i} style={{
                        background: isUploader ? 'rgba(90,200,208,0.08)' : C.surfaceAlt,
                        border: `1px solid ${isUploader ? 'rgba(90,200,208,0.3)' : C.border}`,
                        borderRadius: 8, padding: '8px 10px',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4, gap: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: isUploader ? C.teal2 : C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {m.display_name || 'Anonymous Viewer'}
                            </span>
                            <span style={{
                              ...mono, fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 3, whiteSpace: 'nowrap',
                              color: isUploader ? C.teal2 : C.textMuted,
                              background: isUploader ? 'rgba(90,200,208,0.15)' : 'rgba(110,140,144,0.15)',
                            }}>
                              {isUploader ? 'Uploader' : 'Viewer'}
                            </span>
                          </div>
                          <span style={{ ...mono, fontSize: 9, color: C.textDim, whiteSpace: 'nowrap' }}>
                            {timeOnly(m.created_at)}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: C.textSecondary, lineHeight: 1.5, wordBreak: 'break-word' }}>
                          {m.comment_text}
                        </div>
                      </div>
                    );
                  })}
                  {timeline.length <= 1 && (
                    <div style={{ ...mono, fontSize: 10, color: C.textDim, textAlign: 'center', padding: '4px 0' }}>No replies yet</div>
                  )}
                </div>
              );
            })()}

            {/* Viewer reply composer */}
            {session?.permissions?.can_annotate && (
              <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                <input
                  type="text"
                  value={threadReplyText}
                  onChange={e => setThreadReplyText(e.target.value)}
                  placeholder="Reply to this comment…"
                  style={{
                    flex: 1, background: C.surfaceAlt, border: `1px solid ${C.borderMed}`, borderRadius: 6,
                    padding: '8px 10px', fontSize: 12, color: C.textPrimary, outline: 'none',
                  }}
                  onKeyDown={e => { if (e.key === 'Enter' && threadReplyText.trim() && !threadReplySending) e.currentTarget.nextSibling?.click(); }}
                />
                <button
                  disabled={!threadReplyText.trim() || threadReplySending}
                  onClick={async () => {
                    const text = threadReplyText.trim();
                    if (!text) return;
                    setThreadReplySending(true);
                    try {
                      const rootId = threadView.root?.id || threadView.rootAnnot?.id;
                      await window.SecureDocAPI.createAnnotation(
                        session.link_token,
                        { page_number: threadView.root?.page_number || page, annotation_type: 'comment', coords: { x: 0, y: 0 }, comment_text: text, parent_id: rootId },
                        session.session_id
                      );
                      const data = await window.SecureDocAPI.getAnnotationThread(session.link_token, rootId, session.session_id);
                      setThreadView({ rootAnnot: threadView.rootAnnot, root: data.root || data, replies: data.replies || [], loading: false });
                      setThreadReplyText('');
                    } catch (e) { toast(_errMsg(e, 'Failed to send reply'), 'error'); }
                    finally { setThreadReplySending(false); }
                  }}
                  style={{
                    background: C.teal2, color: '#06080A', border: 'none', borderRadius: 6,
                    padding: '8px 14px', fontSize: 12, fontWeight: 700, cursor: threadReplyText.trim() ? 'pointer' : 'default',
                    opacity: threadReplyText.trim() && !threadReplySending ? 1 : 0.5,
                  }}
                >Send</button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
