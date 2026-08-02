import { C } from '../constants/tokens.js';
import { Btn } from './atoms.jsx';
import { GateMessage } from './GateMessage.jsx';

const { useState, useEffect } = React;

export function AccessGate({ gateInfo, onSubmit, error }) {
  const requiresPw = gateInfo?.requires_password;
  const requiresEmail = gateInfo?.requires_email;
  const status = gateInfo?.status;
  const [pw, setPw] = useState('');
  const [email, setEmail] = useState('');
  const [shaking, setShaking] = useState(false);
  useEffect(() => {
    if (error) { setShaking(true); setTimeout(() => setShaking(false), 500); }
  }, [error]);

  const gateInputStyle = {
    background: 'rgba(90,200,208,0.04)', border: `1px solid ${C.borderMed}`,
    borderRadius: 8, color: C.textPrimary, fontFamily: "'DM Sans', sans-serif",
    fontSize: 13, padding: '10px 13px', outline: 'none', width: '100%',
    boxSizing: 'border-box',
  };

  if (status === 'not_found') return <GateMessage icon="🔍" title="Link Not Found" msg="This share link does not exist or has been removed." />;
  if (status === 'revoked') return <GateMessage icon="🚫" title="Link Revoked" msg="This share link has been revoked by the document owner." />;
  if (status === 'expired') return <GateMessage icon="⏱" title="Link Expired" msg="This share link has expired and is no longer accessible." />;
  if (status === 'view_limit_reached') return <GateMessage icon="👁" title="View Limit Reached" msg="This share link has reached its maximum number of views and is no longer accessible. Contact the document owner for a new link." />;
  if (status === 'concurrent_limit') return <GateMessage icon="📋" title="Session Limit Reached" msg="The maximum number of simultaneous viewers for this link has been reached. Please try again later or contact the document owner." />;
  if (status === 'access_denied') return <GateMessage icon="🔒" title="Access Denied" msg={gateInfo?._detail || "You don't have permission to view this document. Contact the document owner if you believe this is an error."} />;

  const canSubmit = (!requiresEmail || email.trim()) && (!requiresPw || pw);
  const handleSubmit = () => { if (canSubmit) onSubmit(email.trim() || null, pw || null); };

  return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.bg }}>
      <div style={{
        background: C.surface, border: `1px solid ${C.borderMed}`, borderRadius: 14,
        padding: '36px 32px', width: 360, display: 'flex', flexDirection: 'column', gap: 16,
        boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
        animation: shaking ? 'shake .4s' : undefined,
      }}>
        <div style={{ textAlign: 'center', fontSize: 28 }}>
          {requiresPw && requiresEmail ? '🔐' : requiresPw ? '🔒' : '📧'}
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary, textAlign: 'center' }}>
          {requiresPw && requiresEmail ? 'Email & Password Required' : requiresPw ? 'Password Required' : 'Email Verification Required'}
        </div>
        <div style={{ fontSize: 12, color: C.textMuted, textAlign: 'center', lineHeight: 1.6 }}>
          {requiresPw && requiresEmail
            ? 'Enter your institutional email and the document password.'
            : requiresPw
              ? 'This document is password protected.'
              : 'Enter your email address to verify you have access to this document.'}
        </div>
        {requiresEmail && (
          <input type="email" placeholder="you@institution.edu" value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !requiresPw && handleSubmit()}
            autoFocus={true}
            style={gateInputStyle} />
        )}
        {requiresPw && (
          <input type="password" placeholder="Enter password" value={pw}
            onChange={e => setPw(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            autoFocus={!requiresEmail}
            style={gateInputStyle} />
        )}
        {error && <div style={{ fontSize: 11, color: C.error, textAlign: 'center' }}>{error}</div>}
        <Btn onClick={handleSubmit} disabled={!canSubmit} size="lg">Open Document</Btn>
      </div>
    </div>
  );
}
