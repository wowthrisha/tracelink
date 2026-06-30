import { C, mono } from '../../constants/tokens.js';

export function UploadDropZone({ dragging, setDragging, simulate, fileRef }) {
  return (
    <div onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); simulate(e.dataTransfer.files[0]).catch(() => {}); }}
      onClick={() => fileRef.current.click()}
      style={{
        border: `1.5px dashed ${dragging ? C.teal1 : C.borderMed}`,
        borderRadius: 10, padding: '24px', textAlign: 'center',
        background: dragging ? C.accentBg : 'transparent',
        cursor: 'pointer', transition: 'all .15s'
      }}>
      <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt,.md,.log" style={{ display: 'none' }} onChange={e => simulate(e.target.files[0]).catch(() => {})} />
      <div style={{
        width: 36, height: 36, borderRadius: 8, background: C.accentBg,
        border: `1px solid ${C.borderMed}`, display: 'flex', alignItems: 'center',
        justifyContent: 'center', margin: '0 auto 10px', fontSize: 16, color: C.teal2
      }}>⊕</div>
      <div style={{ fontSize: 13, color: C.textSecondary, fontWeight: 600, marginBottom: 4 }}>
        Drop document here or <span style={{ color: C.teal2 }}>click to browse</span>
      </div>
      <div style={{ ...mono, fontSize: 10, color: C.textMuted }}>PDF · DOCX · DOC · TXT · MD · LOG · Doc max 100 MB · Text max 10 MB</div>
    </div>
  );
}
