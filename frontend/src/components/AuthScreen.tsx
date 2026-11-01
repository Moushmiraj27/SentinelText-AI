import { FormEvent, useEffect, useMemo, useState } from 'react';
import { AudioLines, ChevronLeft, Eye, EyeOff, Heart, LoaderCircle, LockKeyhole, Moon, ShieldCheck, Sparkles, Sun } from 'lucide-react';
import '../auth.css';

export type AuthUser = { id: string; name: string; email: string; created_at: string };
type Props = { onAuthenticated: (user: AuthUser) => void; initialError?: string; theme: 'light' | 'dark'; onToggleTheme: () => void };
type Mode = 'login' | 'signup' | 'forgot' | 'reset';

async function authRequest(path: string, payload?: unknown) {
  const response = await fetch(`/api/auth/${path}`, {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'We could not complete that request. Please try again.');
  return data;
}

export default function AuthScreen({ onAuthenticated, initialError, theme, onToggleTheme }: Props) {
  const resetToken = useMemo(() => new URLSearchParams(window.location.search).get('reset_token') || new URLSearchParams(window.location.hash.slice(1)).get('reset_token') || '', []);
  const [mode, setMode] = useState<Mode>(resetToken ? 'reset' : 'login');
  const [name, setName] = useState(''); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [confirmPassword, setConfirmPassword] = useState('');
  const [remember, setRemember] = useState(false); const [accepted, setAccepted] = useState(false);
  const [showPassword, setShowPassword] = useState(false); const [showConfirm, setShowConfirm] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(initialError || ''); const [success, setSuccess] = useState('');

  useEffect(() => {
    if (resetToken) window.history.replaceState({}, document.title, window.location.pathname);
  }, [resetToken]);

  const switchMode = (next: Mode) => { setMode(next); setError(''); setSuccess(''); setPassword(''); setConfirmPassword(''); };
  const validPassword = password.length >= 10 && /[A-Za-z]/.test(password) && /\d/.test(password);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setSuccess('');
    if (mode === 'signup' && password !== confirmPassword) { setError('Your passwords do not match.'); return; }
    if ((mode === 'signup' || mode === 'reset') && !validPassword) { setError('Use at least 10 characters, including a letter and a number.'); return; }
    if (mode === 'signup' && !accepted) { setError('Please accept the terms and privacy notice to continue.'); return; }
    setBusy(true);
    try {
      if (mode === 'login') {
        const result = await authRequest('login', { email, password, remember }); onAuthenticated(result.user);
      } else if (mode === 'signup') {
        const result = await authRequest('register', { name, email, password, terms_accepted: accepted }); onAuthenticated(result.user);
      } else if (mode === 'forgot') {
        const result = await authRequest('forgot-password', { email }); setSuccess(result.message || 'If an account exists for that email, a reset link has been sent.');
      } else {
        await authRequest('reset-password', { token: resetToken, password }); setSuccess('Your password has been updated. Sign in with your new password.');
        window.history.replaceState({}, document.title, window.location.pathname); setMode('login');
      }
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const title = mode === 'login' ? 'Welcome back.' : mode === 'signup' ? 'Make space for yourself.' : mode === 'forgot' ? 'Let’s get you back in.' : 'Choose a new password.';
  const intro = mode === 'login' ? 'Sign in to return to your private reflection space.' : mode === 'signup' ? 'Create a private space for your voice, thoughts, and wellbeing.' : mode === 'forgot' ? 'Enter your account email and we’ll send a secure reset link if there is an account for it.' : 'Use a new password to secure your SentinelText account.';

  return <div className="auth-page">
    <button type="button" className="auth-theme-toggle" onClick={onToggleTheme} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>{theme === 'light' ? <Sun size={17}/> : <Moon size={17}/>}<span>{theme === 'light' ? 'Light' : 'Dark'} mode</span></button>
    <aside className="auth-story">
      <div className="auth-brand"><span className="brand-mark"><AudioLines size={22} /></span><span>sentinel<span>text</span></span></div>
      <div className="auth-story-copy"><div className="auth-kicker"><Sparkles size={14} /> A QUIETER PLACE TO CHECK IN</div><h1>Your thoughts<br />deserve <em>room.</em></h1><p>A private space to reflect in your own words, notice what matters, and find small ways to care for yourself.</p>
        <div className="auth-promise"><div><Heart size={17} /><span><b>Made for reflection</b><small>Your experience stays yours.</small></span></div><div><ShieldCheck size={17} /><span><b>Private by design</b><small>Only your signed-in account can access your entries.</small></span></div></div>
      </div>
      <div className="auth-story-foot">YOUR VOICE. YOUR EMOTIONS. YOUR WELL-BEING.</div>
      <span className="auth-orb auth-orb-one"/><span className="auth-orb auth-orb-two"/><span className="auth-orb auth-orb-three"/>
    </aside>
    <main className="auth-main"><div className="auth-mobile-brand"><AudioLines size={19}/> sentinel<span>text</span></div><section className="auth-card">
      {mode !== 'login' && <button className="auth-back" type="button" onClick={() => switchMode('login')}><ChevronLeft size={15} /> Back to sign in</button>}
      <div className="auth-card-heading"><div className="eyebrow">{mode === 'signup' ? 'CREATE YOUR PRIVATE SPACE' : mode === 'login' ? 'YOUR SPACE IS HERE' : mode === 'forgot' ? 'ACCOUNT RECOVERY' : 'SECURE PASSWORD RESET'}</div><h2>{title}</h2><p>{intro}</p></div>
      {error && <div className="auth-message auth-error" role="alert">{error}</div>}{success && <div className="auth-message auth-success" role="status">{success}</div>}
      <form onSubmit={submit} className="auth-form">
        {mode === 'signup' && <label>Full name<input autoComplete="name" value={name} onChange={e=>setName(e.target.value)} placeholder="Your name" required minLength={2} maxLength={120}/></label>}
        {(mode === 'login' || mode === 'signup' || mode === 'forgot') && <label>Email address<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" required maxLength={320}/></label>}
        {(mode === 'login' || mode === 'signup' || mode === 'reset') && <label>Password<span className="auth-password-wrap"><input type={showPassword?'text':'password'} autoComplete={mode==='login'?'current-password':'new-password'} value={password} onChange={e=>setPassword(e.target.value)} placeholder={mode==='login'?'Enter your password':'At least 10 characters'} required minLength={mode==='login'?1:10} maxLength={128}/><button type="button" aria-label={showPassword?'Hide password':'Show password'} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={16}/>:<Eye size={16}/>}</button></span>{(mode==='signup'||mode==='reset')&&<small className="auth-hint">Use at least 10 characters with a letter and a number.</small>}</label>}
        {mode === 'signup' && <label>Confirm password<span className="auth-password-wrap"><input type={showConfirm?'text':'password'} autoComplete="new-password" value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)} placeholder="Enter your password again" required minLength={10} maxLength={128}/><button type="button" aria-label={showConfirm?'Hide confirmation':'Show confirmation'} onClick={()=>setShowConfirm(!showConfirm)}>{showConfirm?<EyeOff size={16}/>:<Eye size={16}/>}</button></span></label>}
        {mode === 'login' && <div className="auth-options"><label className="auth-check"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)}/><span>Remember me</span></label><button type="button" className="auth-link" onClick={()=>switchMode('forgot')}>Forgot password?</button></div>}
        {mode === 'signup' && <label className="auth-check auth-terms"><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/><span>I agree to the terms and privacy notice. I understand this is a self-reflection tool, not medical care.</span></label>}
        <button className="primary auth-submit" disabled={busy||(mode==='reset'&&!resetToken)}>{busy?<LoaderCircle className="spin" size={17}/>:mode==='login'?'Sign in':mode==='signup'?'Create account':mode==='forgot'?'Send reset link':'Update password'}</button>
      </form>
      {mode==='login'&&<p className="auth-switch">New to SentinelText? <button className="auth-link" onClick={()=>switchMode('signup')}>Create an account</button></p>}
      {mode==='signup'&&<p className="auth-switch">Already have an account? <button className="auth-link" onClick={()=>switchMode('login')}>Sign in</button></p>}
      {mode==='forgot'&&<p className="auth-disclaimer"><LockKeyhole size={13}/> Reset links expire after 30 minutes and can only be used once.</p>}
      {mode==='reset'&&!resetToken&&<p className="auth-message auth-error">This reset link is missing its token. Request another link to continue.</p>}
    </section><p className="auth-footer">SentinelText is for self-reflection and wellbeing support. It does not provide diagnosis or emergency care.</p></main>
  </div>;
}
