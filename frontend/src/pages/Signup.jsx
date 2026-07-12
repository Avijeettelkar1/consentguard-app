import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../lib/AuthContext'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return }
    setBusy(true)
    try {
      await signup(email.trim(), password, name.trim())
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <Link to="/" className="auth-back">← Back to site</Link>
      <h1 className="auth-title">Start scanning.</h1>
      <p className="auth-sub">Free forever for individual scans.</p>

      <form className="auth-form" onSubmit={submit}>
        {error && <div className="auth-error">{error}</div>}
        <div className="field">
          <label htmlFor="name">Name</label>
          <input id="name" type="text" autoComplete="name" placeholder="Avijeet Telkar" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="new-password" placeholder="At least 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn-dark auth-btn" type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="auth-fineprint">
        By creating an account you agree to our Terms of Service and acknowledge that ConsentGuard
        reports are technical evidence, not legal advice.
      </p>
      <p className="auth-switch">
        Already have an account?{' '}
        <button onClick={() => navigate('/login')}>Sign in</button>
      </p>
    </AuthLayout>
  )
}
