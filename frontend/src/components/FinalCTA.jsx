export default function FinalCTA({ onGetStarted }) {
  return (
    <section className="final">
      <div className="final-quote">
        <span className="quote-label">Trusted by privacy counsel across the EU</span>
        <p>“The first tool that actually holds cookie banners accountable — with technical evidence a DPA can act on.”</p>
        <cite>— privacy counsel, EU e-commerce group</cite>
      </div>

      <h2>Prove it, or fix it. <em>Preferably both.</em></h2>
      <p>
        Every scan you run makes the web a little less full of consent theatre. Create a free
        account and run your first scan in under a minute.
      </p>
      <div className="hero-actions" style={{ justifyContent: 'center' }}>
        <button className="btn-dark" onClick={onGetStarted}>
          Get started free
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
        </button>
      </div>
    </section>
  )
}
