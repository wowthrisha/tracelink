import { C } from '../../constants/tokens.js';
import { SectionLabel, Btn } from '../atoms.jsx';

export function UploadMetadataPanel({ selectedGroupId, setSelectedGroupId, groups, retentionPolicy, setRetentionPolicy, setGroupModal, setGroupForm }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <SectionLabel>Assign to group</SectionLabel>
      <select value={selectedGroupId} onChange={e => setSelectedGroupId(e.target.value)}
        style={{
          fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`,
          borderRadius: 6, padding: '4px 8px', color: C.textSecondary, maxWidth: 180
        }}>
        <option value="">— None —</option>
        {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
      </select>
      <Btn variant="ghost" size="sm" onClick={() => { setGroupForm({ name: '', color: '#6366f1', description: '' }); setGroupModal('new'); }}>+ New group</Btn>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
        <SectionLabel>Delete after</SectionLabel>
        <select value={retentionPolicy} onChange={e => setRetentionPolicy(e.target.value)}
          style={{
            fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`,
            borderRadius: 6, padding: '4px 8px', color: C.textSecondary
          }}>
          <option value="never">Never</option>
          <option value="30_days">30 days</option>
          <option value="60_days">60 days</option>
          <option value="90_days">90 days</option>
        </select>
      </div>
    </div>
  );
}
