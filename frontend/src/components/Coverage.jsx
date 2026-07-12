const CMPS = ['OneTrust', 'Cookiebot', 'TrustArc', 'Didomi', 'Quantcast', 'Usercentrics']
const BADGES = ['GDPR Art. 5, 7, 83', 'ePrivacy Directive', 'Disconnect.me DB · 5,412 domains', '+40 custom patterns']

export default function Coverage() {
  return (
    <section className="section" id="coverage">
      <div className="coverage-inner">
        <div>
          <span className="section-label">Coverage</span>
          <h2 className="h2">Every major consent platform.</h2>
          <p className="lead" style={{ marginTop: '1.25rem' }}>
            Built by engineers who’ve reverse-engineered the DOM of every mainstream CMP. When they
            update their button IDs, we update our detectors.
          </p>
          <div className="cov-badges">
            {BADGES.map((b) => <span className="cov-badge" key={b}>{b}</span>)}
          </div>
        </div>

        <div className="cmp-grid">
          {CMPS.map((c) => (
            <div className="cmp" key={c}><span className="dot" />{c}</div>
          ))}
        </div>
      </div>
    </section>
  )
}
