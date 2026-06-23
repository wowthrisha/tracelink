import { C, mono } from '../../constants/tokens.js';
import { StatusDot, Btn, Card } from '../atoms.jsx';

export function UploadProgressPanel({ uploading, uploadDone, progress, uploadedDoc, setUploadDone, onAccessDoc }) {
  return (
    <Card style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusDot status={uploading ? 'processing' : 'active'} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>
            {uploading ? 'Uploading & processing…' : '✓ Processing complete'}
          </span>
        </div>
        <span style={{ ...mono, fontSize: 11, color: C.textMuted }}>{Math.round(progress)}%</span>
      </div>
      <div style={{ height: 4, background: C.surface3, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${progress}%`,
          background: `linear-gradient(90deg, ${C.teal3}, ${C.teal1})`,
          borderRadius: 3, transition: 'width .2s ease'
        }} />
      </div>
      {uploadDone && (
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <Btn variant="primary" size="sm" onClick={() => { setUploadDone(false); if (uploadedDoc) onAccessDoc(uploadedDoc); }}>
            Share Document →
          </Btn>
          <Btn variant="ghost" size="sm" onClick={() => setUploadDone(false)}>Dismiss</Btn>
        </div>
      )}
    </Card>
  );
}
