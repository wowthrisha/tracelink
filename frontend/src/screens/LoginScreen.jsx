import { C } from '../constants/tokens.js';
const { useState } = React;

export function LoginScreen({ onLogin }) {
  // mode: 'login' | 'signup' | 'forgot' | 'reset'
  const [mode, setMode] = useState(() => {
    // Detect Supabase password-reset callback: hash contains access_token + type=recovery
    if (typeof window !== 'undefined') {
      const hash = window.location.hash;
      if (hash.includes('type=recovery') && hash.includes('access_token=')) {
        return 'reset';
      }
    }
    return 'login';
  });
  const [resetToken] = useState(() => {
    if (typeof window === 'undefined') return '';
    const params = new URLSearchParams(window.location.hash.replace('#', ''));
    return params.get('access_token') || '';
  });
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e && e.preventDefault();
    setLoading(true);
    setError('');
    setInfo('');
    try {
      if (mode === 'forgot') {
        if (!email.trim()) { setError('Email is required.'); setLoading(false); return; }
        await window.SecureDocAPI.forgotPassword(email.trim());
        setInfo('Password reset email sent — check your inbox. The link expires in 1 hour.');
        setLoading(false);
        return;
      }
      if (mode === 'reset') {
        if (!newPassword || newPassword.length < 6) { setError('Password must be at least 6 characters.'); setLoading(false); return; }
        await window.SecureDocAPI.resetPassword(resetToken, newPassword);
        setInfo('Password updated successfully. You can now sign in.');
        setMode('login');
        setLoading(false);
        return;
      }
      if (!email.trim() || !password) { setError('Email and password are required.'); setLoading(false); return; }
      const token = await window.SecureDocAPI.auth(mode, email.trim(), password);
      localStorage.setItem('securedoc_token', token);
      onLogin(token);
    } catch (err) {
      const msg = err.message || 'Authentication failed.';
      const lc = msg.toLowerCase();
      if (lc.includes('confirm')) { setInfo(msg); }
      else if (mode === 'reset' && (lc.includes('expired') || lc.includes('invalid') || lc.includes('otp') || lc.includes('token'))) {
        setError('Your password reset link has expired or is invalid. Please request a new reset email.');
        setMode('forgot');
      }
      else if (lc.includes('failed to fetch') || lc.includes('network') || lc.includes('load failed')) {
        setError('Unable to reach the server. Check your connection and try again.');
      }
      else { setError(msg); }
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    background: 'rgba(90,200,208,0.04)', border: `1px solid ${C.borderMed}`,
    borderRadius: 8, color: C.textPrimary, fontFamily: "'DM Sans', sans-serif",
    fontSize: 13, padding: '10px 13px', outline: 'none', width: '100%',
    transition: 'border-color .15s',
  };

  return (
    <div style={{
      height: '100vh', width: '100vw', background: C.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      animation: 'fadeIn .25s ease'
    }}>
      <div className="fade-up" style={{
        width: 360, background: C.surface, border: `1px solid ${C.borderMed}`,
        borderRadius: 14, padding: '32px 28px',
        boxShadow: '0 24px 80px rgba(0,0,0,0.55)'
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, flexShrink: 0,
            background: `linear-gradient(135deg, ${C.teal1} 0%, ${C.teal3} 100%)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <svg width="15" height="15" viewBox="0 0 14 14" fill="none">
              <rect x="2" y="1" width="8" height="10" rx="1.5" stroke="#080B0C" strokeWidth="1.5" />
              <line x1="4" y1="4.5" x2="8" y2="4.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="4" y1="6.5" x2="8" y2="6.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="4" y1="8.5" x2="6.5" y2="8.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
              <circle cx="10" cy="10.5" r="2.5" fill="#080B0C" stroke="#080B0C" strokeWidth="0.5" />
              <path d="M9 10.5l.8.8 1.6-1.6" stroke={C.teal1} strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.4px', color: C.textPrimary, lineHeight: 1.2 }}>SecureDoc</div>
            <div style={{ fontSize: 9, color: C.teal3, letterSpacing: '0.5px', fontWeight: 500 }}>Document Security</div>
          </div>
        </div>

        {/* Mode toggle — hidden for forgot/reset flows */}
        {(mode === 'login' || mode === 'signup') && (
          <div style={{
            display: 'flex', background: C.surfaceAlt, borderRadius: 8,
            padding: 3, marginBottom: 24, gap: 2
          }}>
            {[['login', 'Sign In'], ['signup', 'Sign Up']].map(([m, lbl]) => (
              <button key={m} type="button" onClick={() => { setMode(m); setError(''); setInfo(''); }}
                style={{
                  flex: 1, padding: '7px 0', border: `1px solid ${mode === m ? C.borderMed : 'transparent'}`,
                  borderRadius: 6, cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
                  fontSize: 12, fontWeight: mode === m ? 600 : 400,
                  background: mode === m ? C.accentBg : 'transparent',
                  color: mode === m ? C.teal1 : C.textMuted,
                  transition: 'all .15s'
                }}>
                {lbl}
              </button>
            ))}
          </div>
        )}
        {(mode === 'forgot' || mode === 'reset') && (
          <div style={{ marginBottom: 20, fontSize: 13, color: C.textMuted }}>
            {mode === 'forgot' ? 'Reset your password' : 'Set a new password'}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Email field — shown for login, signup, forgot */}
          {mode !== 'reset' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <label style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: C.textMuted, fontWeight: 600 }}>
                Email
              </label>
              <input
                type="email" value={email} autoFocus={mode !== 'reset'} autoComplete="email"
                onChange={e => setEmail(e.target.value)}
                onFocus={e => e.target.style.borderColor = C.borderActive}
                onBlur={e => e.target.style.borderColor = C.borderMed}
                placeholder="you@example.com" style={inputStyle} />
            </div>
          )}

          {/* Password field — shown for login and signup only */}
          {(mode === 'login' || mode === 'signup') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: C.textMuted, fontWeight: 600 }}>
                  Password
                </label>
                {mode === 'login' && (
                  <button type="button"
                    onClick={() => { setMode('forgot'); setError(''); setInfo(''); }}
                    style={{ fontSize: 10, color: C.teal3, background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: "'DM Sans', sans-serif" }}>
                    Forgot password?
                  </button>
                )}
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'} value={password} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  onChange={e => setPassword(e.target.value)}
                  onFocus={e => e.target.style.borderColor = C.borderActive}
                  onBlur={e => e.target.style.borderColor = C.borderMed}
                  placeholder="••••••••" style={{ ...inputStyle, paddingRight: 40 }} />
                <button type="button"
                  onClick={() => setShowPassword(v => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  style={{
                    position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', padding: 6,
                    fontSize: 11, color: C.textMuted, fontFamily: "'DM Sans', sans-serif"
                  }}>
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              {mode === 'signup' && (
                <span style={{ fontSize: 10, color: C.textDim }}>At least 6 characters.</span>
              )}
            </div>
          )}

          {/* New password field — shown for reset flow only */}
          {mode === 'reset' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <label style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: C.textMuted, fontWeight: 600 }}>
                New Password
              </label>
              <input
                type="password" value={newPassword} autoFocus autoComplete="new-password"
                onChange={e => setNewPassword(e.target.value)}
                onFocus={e => e.target.style.borderColor = C.borderActive}
                onBlur={e => e.target.style.borderColor = C.borderMed}
                placeholder="At least 6 characters" style={inputStyle} />
            </div>
          )}

          {error && (
            <div style={{
              fontSize: 12, color: C.error, background: C.errorBg,
              border: `1px solid ${C.errorBdr}`, borderRadius: 7, padding: '9px 12px', lineHeight: 1.5
            }}>{error}</div>
          )}

          {info && (
            <div style={{
              fontSize: 12, color: C.teal1, background: C.infoBg,
              border: `1px solid ${C.infoBdr}`, borderRadius: 7, padding: '9px 12px', lineHeight: 1.5
            }}>
              {info}
              {mode === 'signup' && (
                <div style={{ marginTop: 6, color: C.teal3, fontSize: 11 }}>
                  Check your <strong>spam / junk folder</strong> if the email doesn't arrive within 2 minutes.
                </div>
              )}
            </div>
          )}

          <button type="submit" disabled={loading}
            style={{
              width: '100%', padding: '11px 0', border: 'none', borderRadius: 8,
              background: loading ? C.teal3 : C.teal2, color: '#080B0C',
              fontFamily: "'DM Sans', sans-serif", fontSize: 13, fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background .15s',
              boxShadow: loading ? 'none' : '0 0 20px rgba(90,200,208,0.25)'
            }}
            onMouseEnter={e => !loading && (e.target.style.background = C.teal1)}
            onMouseLeave={e => !loading && (e.target.style.background = C.teal2)}>
            {loading ? 'Please wait…'
              : mode === 'login' ? 'Sign In'
              : mode === 'signup' ? 'Create Account'
              : mode === 'forgot' ? 'Send Reset Email'
              : 'Set New Password'}
          </button>

          {(mode === 'forgot') && (
            <button type="button" onClick={() => { setMode('login'); setError(''); setInfo(''); }}
              style={{ fontSize: 11, color: C.textMuted, background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: "'DM Sans', sans-serif", textAlign: 'center' }}>
              ← Back to Sign In
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
