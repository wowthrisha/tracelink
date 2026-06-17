// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useEffect } = React;

/**
 * Manages annotation, bookmark, drawing, and comment-thread state for the viewer.
 *
 * Owns the per-page annotation cache, lazy-loads annotations for the current
 * page when the viewer has annotation permission, and loads bookmarks once
 * per session.
 *
 * @param {object|null} session   - Validated viewer session object.
 * @param {number}      page      - Current page number.
 * @param {boolean}     isTextDoc - True for txt/md/log; skips annotation loading.
 */
export function useAnnotations(session, page, isTextDoc) {
  const [annotTool, setAnnotTool] = useState(null);
  const [annotColor, setAnnotColor] = useState('#FFE066');
  const [annotThickness, setAnnotThickness] = useState(2);
  const [annotUndoStack, setAnnotUndoStack] = useState([]);
  const [pageAnnotations, setPageAnnotations] = useState([]);
  const [commentDraft, setCommentDraft] = useState(null);
  const [threadView, setThreadView] = useState(null);
  const [threadReplyText, setThreadReplyText] = useState('');
  const [threadReplySending, setThreadReplySending] = useState(false);
  const annotCacheRef = useRef(new Map());
  const [bookmarks, setBookmarks] = useState(new Set());
  const [drawingState, setDrawingState] = useState(null);

  // Lazy-load annotations for the current page when annotations are enabled
  useEffect(() => {
    if (!session || !session.permissions?.can_annotate || isTextDoc) return;
    if (annotCacheRef.current.has(page)) {
      setPageAnnotations(annotCacheRef.current.get(page));
      return;
    }
    window.SecureDocAPI.getAnnotations(session.link_token, page, session.session_id)
      .then(data => {
        const annots = data.annotations || [];
        annotCacheRef.current.set(page, annots);
        setPageAnnotations(annots);
      })
      .catch(() => {});
  }, [session?.link_token, session?.session_id, page, session?.permissions?.can_annotate, isTextDoc]);

  // Load bookmarks once on session start
  useEffect(() => {
    if (!session || !session.permissions?.can_annotate) return;
    window.SecureDocAPI.getBookmarks(session.link_token, session.session_id)
      .then(data => setBookmarks(new Set((data.bookmarks || []).map(b => b.page_number))))
      .catch(() => {});
  }, [session?.link_token, session?.session_id, session?.permissions?.can_annotate]);

  return {
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
    drawingState, setDrawingState,
    annotCacheRef,
  };
}
