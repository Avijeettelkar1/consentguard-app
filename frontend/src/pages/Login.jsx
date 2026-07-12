import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../lib/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const dest = location.state?.from || '/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email.trim(), password)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <Link to="/" className="auth-back">← Back to site</Link>
      <h1 className="auth-title">Welcome back.</h1>
      <p className="auth-sub">Continue your compliance investigation.</p>

      <form className="auth-form" onSubmit={submit}>
        {error && <div className="auth-error">{error}</div>}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn-dark auth-btn" type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="auth-switch">
        No account yet?{' '}
        <button onClick={() => navigate('/signup')}>Create one</button>
      </p>
    </AuthLayout>
  )
}
