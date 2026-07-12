const GITHUB = 'https://github.com/Avijeettelkar1/consentguard'

export default function Footer() {
  const scrollTo = (id) => (e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }) }
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div>
          <div className="footer-logo">
            <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            ConsentGuard
          </div>
          <p className="footer-tag">
            Independent GDPR consent verification. We prove — with evidence — whether a website
            respects the choices its visitors make.
          </p>
          <p className="footer-mono">GDPR Art. 5, 7, 83 · ePrivacy Directive 2002/58/EC</p>
        </div>

        <div className="footer-col">
          <h4>Product</h4>
          <a href="#how" onClick={scrollTo('how')}>How it works</a>
          <a href="#coverage" onClick={scrollTo('coverage')}>Coverage</a>
          <a href="#pricing" onClick={scrollTo('pricing')}>Pricing</a>
          <a href={GITHUB} target="_blank" rel="noreferrer">Open source</a>
        </div>

        <div className="footer-col">
          <h4>Compliance</h4>
          <a href="https://gdpr-info.eu/art-7-gdpr/" target="_blank" rel="noreferrer">GDPR Art. 7</a>
          <a href="https://gdpr-info.eu/art-83-gdpr/" target="_blank" rel="noreferrer">GDPR Art. 83</a>
          <a href="https://disconnect.me" target="_blank" rel="noreferrer">Disconnect.me DB</a>
        </div>
      </div>

      <div className="footer-bottom">
        <span>Not affiliated with any Data Protection Authority. Reports are technical evidence, not legal advice.</span>
        <span>v0.9.0 · scanner uptime 99.98%</span>
      </div>
    </footer>
  )
}
