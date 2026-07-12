export default function Nav({ onLogoClick, onSignIn, onGetStarted }) {
  return (
    <nav>
      <div className="nav-logo" onClick={onLogoClick}>
        <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        ConsentGuard
      </div>
      <div className="nav-links">
        <a href="#how">How it works</a>
        <a href="#coverage">Coverage</a>
        <a href="#pricing">Pricing</a>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.4rem' }}>
        <button
          onClick={onSignIn}
          style={{ background: 'none', border: 'none', color: 'var(--text2)', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 500, fontFamily: 'var(--sans)' }}
        >
          Sign in
        </button>
        <button className="btn-dark nav-cta" onClick={onGetStarted}>Get started</button>
      </div>
    </nav>
  )
}
