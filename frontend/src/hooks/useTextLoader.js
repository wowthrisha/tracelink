import { _errMsg } from '../utils/viewer.js';

// React hooks are available as globals via the UMD CDN bundle (window.React).
const { useState, useCallback, useEffect } = React;

/**
 * Loads text-document chunks (txt / md / log) for the current page.
 * Returns nothing for PDF/image documents (isTextDoc === false).
 */
export function useTextLoader(session, page, isTextDoc) {
  const [textContent, setTextContent] = useState('');
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState(null);

  const loadTextChunk = useCallback(async (token, chunkNum, sessionId) => {
    if (!token || !sessionId) return;
    setTextLoading(true);
    setTextError(null);
    try {
      const data = await window.SecureDocAPI.getTextChunk(token, chunkNum, sessionId);
      setTextContent(data.content);
    } catch (e) {
      setTextError(_errMsg(e, 'Unable to load content'));
    } finally {
      setTextLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!session || !isTextDoc) return;
    if (session.doc_status && session.doc_status !== 'ready') {
      const msgs = {
        uploaded:   'Document is queued for processing — please wait and refresh.',
        processing: 'Document is still processing — please wait a moment and refresh.',
        error:      'Document processing failed. Please contact the document owner.',
      };
      setTextError(msgs[session.doc_status] || `Document not available (${session.doc_status})`);
      return;
    }
    setTextError(null);
    loadTextChunk(session.link_token, page, session.session_id);
    if (page === session.page_count) {
      window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'completed');
    }
  }, [session?.link_token, session?.session_id, page, session?.doc_status, session?.doc_type, loadTextChunk]);

  return { textContent, textLoading, textError };
}
