import EvidencePanel from './EvidencePanel'

export default function Hero({ onGetStarted }) {

  return (
    <section className="hero" id="top">
      <div className="hero-grid-bg bg-grid" />
      <div className="hero-inner">
        <div className="hero-left">
          <div className="hero-eyebrow"><span className="edot" />Independent · Evidence-based · GDPR Art. 5, 7, 83</div>
          <h1>
            Cookie banners are <em>theatre.</em><br />
            We publish the receipts.
          </h1>
          <p className="hero-sub">
            We run your site in a real browser, click “Reject All”, and record every tracker that
            keeps firing anyway — matched against 6,326 known ad &amp; analytics domains.
          </p>

          <div className="hero-actions">
            <button className="btn-dark" onClick={onGetStarted}>
              Get started free
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </button>
            <a className="btn-outline" href="#how">See how it works</a>
          </div>

          <div className="hero-caption">Free · No cookies stored · Report ready in ~30 seconds</div>
        </div>

        <div className="hero-right">
          <EvidencePanel />
        </div>
      </div>
    </section>
  )
}
