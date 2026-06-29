import { C, mono } from '../constants/tokens.js';

export class ViewerErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error('ViewerErrorBoundary caught:', error, info); }
  render() {
    if (this.state.error) {
      return (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, color: C.textMuted, padding: 32 }}>
          <div style={{ fontSize: 32 }}>⚠</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>Viewer encountered an error</div>
          <div style={{ ...mono, fontSize: 11, color: C.textDim, maxWidth: 400, textAlign: 'center' }}>{String(this.state.error)}</div>
          <button onClick={() => this.setState({ error: null })}
            style={{ marginTop: 8, padding: '7px 18px', borderRadius: 7, border: `1px solid ${C.borderMed}`, background: C.surface, color: C.textSecondary, cursor: 'pointer', fontSize: 12 }}>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
