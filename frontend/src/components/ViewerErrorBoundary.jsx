import { C, mono } from '../constants/tokens.js';

function _correlationId() {
  return `err_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

export class ViewerErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null, correlationId: null }; }
  static getDerivedStateFromError(error) { return { error, correlationId: _correlationId() }; }
  componentDidCatch(error, info) {
    // The real error (message, stack, component stack) stays in the console for
    // debugging — never rendered to the user, who only sees a friendly message
    // plus a correlation ID they can quote in a support request.
    console.error(`ViewerErrorBoundary [${this.state.correlationId}]:`, error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, color: C.textMuted, padding: 32 }}>
          <div style={{ fontSize: 32 }}>⚠</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>Something went wrong opening this document</div>
          <div style={{ fontSize: 12, color: C.textMuted, maxWidth: 400, textAlign: 'center' }}>
            This wasn't your fault — try again, or contact support with the reference code below if it keeps happening.
          </div>
          <div style={{ ...mono, fontSize: 10, color: C.textDim }}>Reference: {this.state.correlationId}</div>
          <button onClick={() => this.setState({ error: null, correlationId: null })}
            style={{ marginTop: 8, padding: '7px 18px', borderRadius: 7, border: `1px solid ${C.borderMed}`, background: C.surface, color: C.textSecondary, cursor: 'pointer', fontSize: 12 }}>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
