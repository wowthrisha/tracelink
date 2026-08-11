import { isDocumentContentReady } from '../viewer.js';

// V24-001 regression: Reading Intelligence's isDocumentReady used to check
// imgReady alone, which is only ever set by the PDF/image <img> onLoad
// handler. The page-image-loading effect explicitly skips text documents
// entirely, so imgReady never becomes true for a .txt/.md/.log document —
// browser-confirmed live (public share link, real 8s wait + a real click):
// the reading-progress widget stayed on "Timer paused — not started"
// indefinitely, and zero batch-flush requests fired despite the 5s flush
// interval. isDocumentContentReady() is the extracted, testable version of
// the fix: text docs are "ready" once their current chunk has loaded.

describe('isDocumentContentReady (V24-001)', () => {
  test('PDF/image doc: ready once imgReady is true', () => {
    expect(isDocumentContentReady({ isTextDoc: false, imgReady: true, textLoading: false, textContent: '' })).toBe(true);
  });

  test('PDF/image doc: not ready while imgReady is false', () => {
    expect(isDocumentContentReady({ isTextDoc: false, imgReady: false, textLoading: false, textContent: '' })).toBe(false);
  });

  test('text doc: NOT ready even though imgReady will never be true for this doc type (the bug)', () => {
    expect(isDocumentContentReady({ isTextDoc: true, imgReady: false, textLoading: true, textContent: '' })).toBe(false);
  });

  test('text doc: ready once the chunk has finished loading and has content', () => {
    expect(isDocumentContentReady({ isTextDoc: true, imgReady: false, textLoading: false, textContent: '# Hello' })).toBe(true);
  });

  test('text doc: not ready while still loading, even if stale content is present', () => {
    expect(isDocumentContentReady({ isTextDoc: true, imgReady: false, textLoading: true, textContent: '# Hello' })).toBe(false);
  });

  test('text doc: not ready if load finished but content is empty', () => {
    expect(isDocumentContentReady({ isTextDoc: true, imgReady: false, textLoading: false, textContent: '' })).toBe(false);
  });

  test('text doc: imgReady being true (should never happen for text docs) does not matter — text readiness rules apply', () => {
    expect(isDocumentContentReady({ isTextDoc: true, imgReady: true, textLoading: true, textContent: '' })).toBe(false);
  });
});
