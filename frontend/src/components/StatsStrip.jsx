import { useInView } from '../hooks/useInView'

const SITES = ['bbc.com', 'cnn.com', 'nytimes.com', 'theguardian.com', 'forbes.com', 'reddit.com',
  'tripadvisor.com', 'businessinsider.com', 'dailymail.co.uk', 'vice.com', 'buzzfeed.com', 'huffpost.com']

const STATS = [
  { value: '73%', label: 'of sites still fire trackers after a user clicks "Reject All"', color: 'var(--red)' },
  { value: '6,324', label: 'known tracker domains cross-referenced on every scan', color: 'var(--text)' },
  { value: '30s', label: 'from URL to a filed-ready compliance report', color: 'var(--accent)' },
  { value: '€20M', label: 'maximum fine per violation under GDPR Art. 83', color: 'var(--yellow)' },
]

export default function StatsStrip() {
  const doubled = [...SITES, ...SITES]
  const [ref, inView] = useInView(0.15)

  return (
    <>
      <div className="marquee-section">
        <div className="marquee-label">GDPR violations detected on</div>
        <div className="marquee-outer">
          <div className="marquee-track">
            {doubled.map((site, i) => (
              <span className="marquee-item" key={i}>
                <span className="marquee-dot" />
                {site}
              </span>
            ))}
          </div>
        </div>
      </div>

      <section className="stats-section">
        <div className="stats-header">
          <span className="eyebrow muted">The compliance gap</span>
          <h2>
            Your cookie banner says one thing.<br />
            <span className="grad-text">Your network traffic says another.</span>
          </h2>
          <p>
            "Reject All" is a legal promise. Most sites break it the moment the page reloads —
            ad and analytics trackers keep firing, undeclared, in plain violation of GDPR.
          </p>
        </div>

        <div ref={ref} className="stats-grid">
          {STATS.map(({ value, label, color }, i) => (
            <div
              className={`stat-item reveal${inView ? ' in-view' : ''}`}
              key={label}
              style={{ transitionDelay: `${i * 0.08}s` }}
            >
              <div className="stat-value" style={{ color }}>{value}</div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
