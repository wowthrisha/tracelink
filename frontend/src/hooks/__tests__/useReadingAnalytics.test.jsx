import { render, act } from '@testing-library/react';
import { useReadingAnalytics } from '../useReadingAnalytics.js';

// ENG-048 regression coverage.
//
// Root cause: the "handle page changes" effect used to depend on only
// [page, _exitPage, _enterPage] and guard on a ref read (state.current
// .sessionStarted) instead of a reactive value. `page` is already 1 on
// mount (useViewerLayout's initial state) but the session becomes ready
// (isDocumentReady flipping true) on a *later* render — a state change
// this effect had no dependency on, so it never re-ran and `_enterPage`
// was never called. With `currentPage` stuck at null, `_accumulate()`'s
// guard clause made it a permanent no-op, so accumulated active time
// never left zero and no page was ever marked entered — meaning nothing
// was ever flushed to the backend either, not just a display illusion.
//
// This harness reproduces exactly that timing: isDocumentReady starts
// false and flips true on a subsequent render, matching ViewerScreen's
// real docReadyLatchRef behavior.

function Harness({ session, page, pageCount, isDocumentReady, captureRef }) {
  const { _flush } = useReadingAnalytics(session, page, pageCount, isDocumentReady);
  captureRef.current = { _flush };
  return null;
}

const session = { link_token: 'tok-eng048', session_id: 'sess-eng048' };

function totalActiveMsFromLastCall(mockFn) {
  const calls = mockFn.mock.calls;
  if (calls.length === 0) return undefined;
  const lastCall = calls[calls.length - 1];
  return lastCall[3].total_active_ms; // (token, sessionId, pages, meta)
}

describe('useReadingAnalytics — ENG-048: active time must survive a blur/focus cycle', () => {
  let batchReadingEvents;

  beforeEach(() => {
    batchReadingEvents = vi.fn();
    window.SecureDocAPI = {
      ...window.SecureDocAPI,
      batchReadingEvents,
      getViewerReadingSummary: vi.fn().mockResolvedValue(null),
    };
  });

  test('accumulates active time once the session becomes ready, even though page was already set before isDocumentReady flipped true', async () => {
    const captureRef = { current: null };
    const { rerender } = render(
      <Harness session={session} page={1} pageCount={5} isDocumentReady={false} captureRef={captureRef} />
    );

    // isDocumentReady flips true on a later render — this is the exact
    // sequence that broke the old dependency array.
    rerender(<Harness session={session} page={1} pageCount={5} isDocumentReady captureRef={captureRef} />);

    await act(async () => { await new Promise(r => setTimeout(r, 250)); });

    act(() => { captureRef.current._flush(); });

    // Old code: pageData stays {} forever (currentPage never set to a
    // real page), so _flush's pageDataSnapshot is always empty and it
    // returns before ever calling batchReadingEvents.
    expect(batchReadingEvents).toHaveBeenCalled();
    const afterReading = totalActiveMsFromLastCall(batchReadingEvents);
    expect(afterReading).toBeGreaterThan(0);
  });

  test('pausing on window blur freezes accumulated time instead of losing it, and resuming continues from the preserved value', async () => {
    const captureRef = { current: null };
    const { rerender } = render(
      <Harness session={session} page={1} pageCount={5} isDocumentReady={false} captureRef={captureRef} />
    );
    rerender(<Harness session={session} page={1} pageCount={5} isDocumentReady captureRef={captureRef} />);

    // Segment 1: read for ~250ms.
    await act(async () => { await new Promise(r => setTimeout(r, 250)); });
    act(() => { captureRef.current._flush(); });
    const afterSegment1 = totalActiveMsFromLastCall(batchReadingEvents);
    expect(afterSegment1).toBeGreaterThan(0);

    // Blur — must pause immediately and preserve the accumulated value.
    act(() => { window.dispatchEvent(new Event('blur')); });

    // "Away" for ~250ms — none of this should count.
    await act(async () => { await new Promise(r => setTimeout(r, 250)); });
    act(() => { captureRef.current._flush(); });
    const whilePaused = totalActiveMsFromLastCall(batchReadingEvents);

    // The old bug reset to 0 on pause; the fix must freeze at ~afterSegment1
    // (a few ms of real-clock jitter between the flush and the blur event
    // is expected and fine — it must NOT grow by anywhere near the 250ms
    // "away" wait that follows, and must NOT drop toward 0).
    expect(whilePaused).toBeGreaterThanOrEqual(afterSegment1);
    expect(whilePaused).toBeLessThan(afterSegment1 + 20);

    // Focus — resume from the preserved value, not from zero.
    act(() => { window.dispatchEvent(new Event('focus')); });
    await act(async () => { await new Promise(r => setTimeout(r, 250)); });
    act(() => { captureRef.current._flush(); });
    const afterResume = totalActiveMsFromLastCall(batchReadingEvents);

    // Must have grown from the preserved base by roughly segment 2's
    // duration — not restarted near zero (the old bug's exact symptom).
    expect(afterResume).toBeGreaterThan(whilePaused);
    expect(afterResume - whilePaused).toBeGreaterThan(50); // segment 2 contributed real time
    expect(afterResume).toBeGreaterThan(afterSegment1 * 1.3); // genuinely additive, not a near-zero restart
  });
});
