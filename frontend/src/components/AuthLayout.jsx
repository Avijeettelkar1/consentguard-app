import { Link } from 'react-router-dom'

const CHECKS = [
  'Playwright browser sandbox',
  'Disconnect.me tracker DB',
  'Rule-based policy analysis',
  'Fine exposure model',
  'DPA complaint letter draft',
]

const Check = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
)

export default function AuthLayout({ children }) {
  return (
    <div className="auth-wrap">
      <div className="auth-brand">
        <Link to="/" className="auth-brand-logo" style={{ color: '#fff', textDecoration: 'none' }}>
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          ConsentGuard
        </Link>

        <div className="auth-radar-wrap">
          <div className="radar">
            <span className="radar-pulse" />
            <span className="radar-pulse d2" />
            <span className="radar-ring" />
            <span className="radar-ring r2" />
            <span className="radar-ring r3" />
            <span className="radar-cross v" />
            <span className="radar-cross h" />
            <span className="radar-sweep" />
            <span className="radar-blip b1" />
            <span className="radar-blip b2" />
            <span className="radar-blip b3" />
            <span className="radar-blip b4" />
            <span className="radar-center" />
          </div>
          <div className="radar-caption">
            <span className="radar-live" /> Scanning 6,326 tracker domains
          </div>
        </div>

        <div className="auth-brand-body">
          <h2>One scan. Six databases.<br />One report your legal team can <em>send.</em></h2>
          <ul className="auth-check">
            {CHECKS.map((c) => <li key={c}><Check />{c}</li>)}
          </ul>
          <div className="auth-brand-foot">Trusted by privacy counsel across the EU</div>
        </div>
      </div>

      <div className="auth-form-side">
        <div className="auth-card">{children}</div>
      </div>
    </div>
  )
}
