import { useState } from 'react'
import { supabase } from './data'

/** Magic link (or the 6-digit code, if the email template includes {{ .Token }}). */
export function Login() {
  const [email, setEmail] = useState(() => localStorage.getItem('admin.email') ?? '')
  const [sent, setSent] = useState(false)
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function send(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    try { localStorage.setItem('admin.email', email) } catch { /* private window */ }
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin, shouldCreateUser: false },
    })
    setBusy(false)
    if (error) setError(error.message)
    else setSent(true)
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    const { error } = await supabase.auth.verifyOtp({ email, token: code.trim(), type: 'email' })
    setBusy(false)
    if (error) setError(error.message)
  }

  return (
    <div className="login">
      <div className="login-card">
        <h1>Catalog admin</h1>
        <p className="muted">Sign in with an admin email. You'll get a link; open it in this browser.</p>
        {!sent ? (
          <form onSubmit={send}>
            <input type="email" required autoFocus placeholder="you@example.com" value={email}
              onChange={(e) => setEmail(e.target.value)} />
            <button className="primary" disabled={busy}>{busy ? 'Sending…' : 'Send magic link'}</button>
          </form>
        ) : (
          <form onSubmit={verify}>
            <p>Link sent to <b>{email}</b>. Click it, or paste the code if the email has one.</p>
            <input inputMode="numeric" placeholder="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} />
            <div className="row">
              <button className="primary" disabled={busy || code.trim().length < 6}>Verify code</button>
              <button type="button" onClick={() => setSent(false)}>Use another email</button>
            </div>
          </form>
        )}
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  )
}
