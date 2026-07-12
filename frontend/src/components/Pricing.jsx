const check = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
)

const TIERS = [
  {
    name: 'Scanner', price: 'Free', sub: 'for individuals & journalists',
    features: ['1 scan / day', 'Full network log', 'Basic violation list', 'Public shareable URL'],
    cta: 'Run a scan', scan: true,
  },
  {
    name: 'Counsel', price: '€79', sub: 'per month · billed annually',
    features: ['Unlimited scans', 'AI-drafted cookie policy fixes', 'Fine exposure model', 'DPA complaint letters', 'History & re-scan diffs'],
    cta: 'Start 14-day trial', highlight: true,
  },
  {
    name: 'Firm', price: '€440', sub: 'per month · unlimited seats',
    features: ['Bulk domain scanning', 'Watchlist monitoring', 'Weekly regression alerts', 'White-label reports for clients', 'SSO + audit log'],
    cta: 'Talk to us',
  },
]

export default function Pricing({ onGetStarted }) {
  const handle = () => onGetStarted?.()
  return (
    <section className="section alt" id="pricing">
      <div className="shell">
        <div className="section-head">
          <span className="section-label">Pricing</span>
          <h2 className="h2">Priced like evidence, not software.</h2>
        </div>
      </div>
      <div className="pricing-grid">
        {TIERS.map((t) => (
          <div className={`tier${t.highlight ? ' highlight' : ''}`} key={t.name}>
            {t.highlight && <span className="tier-badge">Recommended</span>}
            <div className="tier-name">{t.name}</div>
            <div className="tier-price">{t.price}</div>
            <div className="tier-sub">{t.sub}</div>
            <ul className="tier-features">
              {t.features.slice(0, 3).map((f) => <li key={f}>{check}{f}</li>)}
              {t.features.length > 3 && (
                <li className="tier-more">+ {t.features.length - 3} more</li>
              )}
            </ul>
            <button className={t.highlight ? 'btn-dark' : 'btn-outline'} onClick={handle}>{t.cta}</button>
          </div>
        ))}
      </div>
    </section>
  )
}
