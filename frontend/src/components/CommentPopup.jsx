const { useState, useRef, useEffect } = React;

export function CommentPopup({ draft, onSave, onCancel, C }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);
  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 50); }, []);
  return (
    <div style={{ position: 'absolute', left: `${Math.min(draft.x * 100, 70)}%`, top: `${Math.min(draft.y * 100, 70)}%`, zIndex: 20, background: '#0E1416', border: '1px solid rgba(90,200,208,0.3)', borderRadius: 8, padding: '10px 12px', width: 220, boxShadow: '0 4px 24px rgba(0,0,0,0.6)' }}>
      <div style={{ fontSize: 10, color: 'rgba(148,160,176,0.7)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.5px' }}>{draft.type === 'sticky_note' ? 'ADD STICKY NOTE' : 'ADD COMMENT'}</div>
      <textarea ref={inputRef} value={text} onChange={e => setText(e.target.value)} placeholder="Type your comment…" maxLength={2000}
        style={{ width: '100%', minHeight: 64, fontSize: 11, resize: 'vertical', marginBottom: 8, background: 'rgba(90,200,208,0.05)', border: '1px solid rgba(90,200,208,0.2)', borderRadius: 5, color: '#F0F2F1', fontFamily: "'DM Sans',sans-serif", padding: '6px 8px', outline: 'none' }}
        onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) onSave(text); if (e.key === 'Escape') onCancel(); }}
      />
      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{ fontSize: 11, padding: '4px 10px', background: 'none', border: '1px solid rgba(148,160,176,0.2)', borderRadius: 5, color: 'rgba(148,160,176,0.7)', cursor: 'pointer' }}>Cancel</button>
        <button onClick={() => onSave(text)} style={{ fontSize: 11, padding: '4px 10px', background: 'rgba(90,200,208,0.15)', border: '1px solid rgba(90,200,208,0.3)', borderRadius: 5, color: '#5ac8d0', cursor: 'pointer', fontWeight: 600 }}>Save</button>
      </div>
    </div>
  );
}
