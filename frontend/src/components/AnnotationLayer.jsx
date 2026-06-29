const { useState, useRef } = React;

// commentDraft and mono are declared in the prop signature for caller compatibility
// but are not used inside this component (commentDraft is used by sibling CommentPopup).
// drawPoints is read directly in _onMouseUp — pre-existing stale-closure risk, not introduced by extraction.
export function AnnotationLayer({ annotations, activeTool, sessionPrefix, commentDraft, onDraw, onDelete, onOpenThread, C, mono }) {
  const svgRef = useRef(null);
  const [preview, setPreview] = useState(null); // shape being drawn
  const [drawPoints, setDrawPoints] = useState([]); // freehand path points
  const dragRef = useRef(null);

  const _toNorm = (e) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return { x: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)), y: Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height)) };
  };

  // SVG path `d` cannot use "%" units (invalid path syntax — browsers drop the path).
  // Convert normalized 0-1 points to real pixel coords using the live SVG box.
  const _pathD = (pts) => {
    const rect = svgRef.current?.getBoundingClientRect();
    const w = rect?.width || 1;
    const h = rect?.height || 1;
    return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${(p.x * w).toFixed(2)} ${(p.y * h).toFixed(2)}`).join(' ');
  };

  const _onMouseDown = (e) => {
    if (!activeTool || e.button !== 0) return;
    e.preventDefault();
    const { x, y } = _toNorm(e);
    dragRef.current = { x, y };
    if (activeTool === 'draw') {
      setDrawPoints([{ x, y }]);
      setPreview(true);
    } else {
      setPreview({ x, y, w: 0, h: 0, x2: x, y2: y });
    }
  };
  const _onMouseMove = (e) => {
    if (!dragRef.current) return;
    const { x, y } = _toNorm(e);
    const s = dragRef.current;
    if (activeTool === 'draw') {
      setDrawPoints(pts => [...pts, { x, y }]);
    } else {
      setPreview({ x: Math.min(s.x, x), y: Math.min(s.y, y), w: Math.abs(x - s.x), h: Math.abs(y - s.y), x1: s.x, y1: s.y, x2: x, y2: y });
    }
  };
  const _onMouseUp = (e) => {
    if (!dragRef.current || !preview) { dragRef.current = null; return; }
    const s = dragRef.current;
    const { x, y } = _toNorm(e);
    dragRef.current = null;
    setPreview(null);
    const minDrag = 0.01;
    if (activeTool === 'comment' || activeTool === 'sticky_note') {
      onDraw({ x: s.x, y: s.y }, activeTool);
      return;
    }
    if (activeTool === 'draw') {
      const pts = drawPoints;
      setDrawPoints([]);
      if (pts.length >= 2) onDraw({ points: pts }, 'draw');
      return;
    }
    if (Math.abs(x - s.x) < minDrag && Math.abs(y - s.y) < minDrag) return;
    const coords = activeTool === 'arrow'
      ? { x1: s.x, y1: s.y, x2: x, y2: y }
      : { x: Math.min(s.x, x), y: Math.min(s.y, y), w: Math.abs(x - s.x), h: Math.abs(y - s.y) };
    onDraw(coords, activeTool);
  };

  const isInteractive = !!activeTool;
  return (
    <svg
      ref={svgRef}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 8, pointerEvents: isInteractive ? 'all' : 'none', cursor: isInteractive ? (activeTool === 'comment' ? 'crosshair' : 'crosshair') : 'default', overflow: 'visible' }}
      onMouseDown={_onMouseDown} onMouseMove={_onMouseMove} onMouseUp={_onMouseUp}
    >
      {annotations.filter(a => !a.parent_id).map(a => {
        const isOwn = a.session_id === sessionPrefix + '…' || a.session_id?.startsWith(sessionPrefix);
        const coords = typeof a.coords === 'string' ? JSON.parse(a.coords) : a.coords;
        const col = a.color || '#FFE066';
        if (a.annotation_type === 'highlight') return (
          <rect key={a.id} x={`${coords.x * 100}%`} y={`${coords.y * 100}%`} width={`${coords.w * 100}%`} height={`${coords.h * 100}%`}
            fill={col} opacity="0.35" rx="2"
            style={{ pointerEvents: isOwn && !activeTool ? 'all' : 'none', cursor: 'pointer' }}
            onClick={() => !activeTool && isOwn && onDelete(a.id)} />
        );
        if (a.annotation_type === 'rectangle') return (
          <rect key={a.id} x={`${coords.x * 100}%`} y={`${coords.y * 100}%`} width={`${coords.w * 100}%`} height={`${coords.h * 100}%`}
            fill="none" stroke={col} strokeWidth="1.5" rx="2" opacity="0.8"
            style={{ pointerEvents: isOwn && !activeTool ? 'all' : 'none', cursor: 'pointer' }}
            onClick={() => !activeTool && isOwn && onDelete(a.id)} />
        );
        if (a.annotation_type === 'arrow') return (
          <g key={a.id} style={{ pointerEvents: isOwn && !activeTool ? 'all' : 'none', cursor: 'pointer' }} onClick={() => !activeTool && isOwn && onDelete(a.id)}>
            <defs><marker id={`ah-${a.id}`} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill={col}/></marker></defs>
            <line x1={`${coords.x1 * 100}%`} y1={`${coords.y1 * 100}%`} x2={`${coords.x2 * 100}%`} y2={`${coords.y2 * 100}%`} stroke={col} strokeWidth="1.8" opacity="0.9" markerEnd={`url(#ah-${a.id})`}/>
          </g>
        );
        if (a.annotation_type === 'bookmark') return (
          <g key={a.id} style={{ pointerEvents: isOwn && !activeTool ? 'all' : 'none', cursor: 'pointer' }} onClick={() => !activeTool && isOwn && onDelete(a.id)}>
            <circle cx={`${(coords.x || 0) * 100}%`} cy={`${(coords.y || 0) * 100}%`} r="8" fill={col} opacity="0.85"/>
            <text x={`${(coords.x || 0) * 100}%`} y={`${(coords.y || 0) * 100}%`} textAnchor="middle" dominantBaseline="central" fontSize="9" fill="#060809" fontWeight="700">🔖</text>
          </g>
        );
        if (a.annotation_type === 'comment') return (
          <g key={a.id} style={{ pointerEvents: !activeTool ? 'all' : 'none', cursor: 'pointer' }} onClick={() => !activeTool && onOpenThread && onOpenThread(a)}>
            <circle cx={`${(coords.x || 0) * 100}%`} cy={`${(coords.y || 0) * 100}%`} r="8" fill={col} opacity="0.85"/>
            <text x={`${(coords.x || 0) * 100}%`} y={`${(coords.y || 0) * 100}%`} textAnchor="middle" dominantBaseline="central" fontSize="9" fill="#060809" fontWeight="700">💬</text>
            {a.comment_text && (
              <foreignObject x={`${Math.min((coords.x || 0) * 100 + 2, 60)}%`} y={`${(coords.y || 0) * 100}%`} width="160" height="60" style={{ pointerEvents: 'none' }}>
                <div style={{ background: 'rgba(6,8,9,0.88)', border: `1px solid ${col}`, borderRadius: 5, padding: '4px 8px', fontSize: 10, color: '#F0F2F1', fontFamily: "'DM Sans',sans-serif", lineHeight: 1.4, maxWidth: 160, wordBreak: 'break-word' }}>
                  {a.comment_text}
                </div>
              </foreignObject>
            )}
          </g>
        );
        if (a.annotation_type === 'sticky_note') return (
          <g key={a.id} style={{ pointerEvents: !activeTool ? 'all' : 'none', cursor: 'pointer' }} onClick={() => !activeTool && onOpenThread && onOpenThread(a)}>
            <rect x={`${(coords.x || 0) * 100 - 1}%`} y={`${(coords.y || 0) * 100 - 1}%`} width="22" height="22" rx="3" fill="#FFE066" opacity="0.92"/>
            <text x={`${(coords.x || 0) * 100}%`} y={`${(coords.y || 0) * 100}%`} textAnchor="middle" dominantBaseline="central" fontSize="11" style={{ transform: `translate(10px, 10px)` }}>📝</text>
            {a.comment_text && (
              <foreignObject x={`${Math.min((coords.x || 0) * 100 + 2, 60)}%`} y={`${(coords.y || 0) * 100}%`} width="160" height="80" style={{ pointerEvents: 'none' }}>
                <div style={{ background: '#FFFDE7', border: '1px solid #FFE066', borderRadius: 5, padding: '4px 8px', fontSize: 10, color: '#333', fontFamily: "'DM Sans',sans-serif", lineHeight: 1.4, maxWidth: 160, wordBreak: 'break-word', boxShadow: '0 2px 8px rgba(0,0,0,0.25)' }}>
                  {a.comment_text}
                </div>
              </foreignObject>
            )}
          </g>
        );
        if (a.annotation_type === 'draw') {
          const pts = Array.isArray(coords.points) ? coords.points : [];
          if (pts.length < 2) return null;
          const d = _pathD(pts);
          return (
            <path key={a.id} d={d} stroke={col} strokeWidth={a.thickness || 2} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.9"
              style={{ pointerEvents: isOwn && !activeTool ? 'all' : 'none', cursor: 'pointer' }}
              onClick={() => !activeTool && isOwn && onDelete(a.id)} />
          );
        }
        return null;
      })}
      {/* Drawing preview */}
      {preview && activeTool === 'highlight' && <rect x={`${preview.x * 100}%`} y={`${preview.y * 100}%`} width={`${preview.w * 100}%`} height={`${preview.h * 100}%`} fill="#FFE066" opacity="0.3" rx="2" style={{ pointerEvents: 'none' }}/>}
      {preview && activeTool === 'rectangle' && <rect x={`${preview.x * 100}%`} y={`${preview.y * 100}%`} width={`${preview.w * 100}%`} height={`${preview.h * 100}%`} fill="none" stroke="#5ac8d0" strokeWidth="1.5" rx="2" opacity="0.7" style={{ pointerEvents: 'none' }}/>}
      {preview && activeTool === 'arrow' && <line x1={`${preview.x1 * 100}%`} y1={`${preview.y1 * 100}%`} x2={`${preview.x2 * 100}%`} y2={`${preview.y2 * 100}%`} stroke="#5ac8d0" strokeWidth="1.8" opacity="0.7" style={{ pointerEvents: 'none' }}/>}
      {preview && activeTool === 'draw' && drawPoints.length >= 2 && (
        <path d={_pathD(drawPoints)} stroke="#5ac8d0" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" style={{ pointerEvents: 'none' }}/>
      )}
    </svg>
  );
}
