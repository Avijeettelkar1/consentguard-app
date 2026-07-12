import { useInView } from '../hooks/useInView'

const CARDS = [
  {
    num: '€5B+',
    label: 'GDPR fines issued since 2018',
    body: 'Regulators moved from warnings to penalties. Enforcement compounds every year — and cookie consent is the most-cited violation.',
    color: 'var(--red)',
  },
  {
    num: 'Millions',
    label: 'of sites serve EU users',
    body: 'Every one is legally on the hook the moment a regulator, competitor, or user files. Almost none can prove they comply.',
    color: 'var(--text)',
  },
  {
    num: '€5k+',
    label: 'per manual audit today',
    body: 'A single consultancy audit is weeks of billable hours for a snapshot that is already stale the day it lands.',
    color: 'var(--yellow)',
  },
  {
    num: '30s',
    label: 'with ConsentGuard',
    body: 'Self-serve, continuous, and priced for every site — not just the enterprises that can afford a law firm.',
    color: 'var(--accent)',
  },
]

export default function Market() {
  const [ref, inView] = useInView(0.12)

  return (
    <section className="market-section">
      <div className="market-inner">
        <div className="market-header">
          <span className="eyebrow">Why now</span>
          <h2>The enforcement wave has arrived.</h2>
          <p>
            GDPR stopped being a formality. The fines are real and automated proof of compliance
            barely exists — yet. ConsentGuard turns a €5,000 consultant engagement into a
            30-second, self-serve scan.
          </p>
        </div>

        <div ref={ref} className="market-grid">
          {CARDS.map((c, i) => (
            <div
              className={`market-card reveal${inView ? ' in-view' : ''}`}
              key={c.label}
              style={{ transitionDelay: `${i * 0.09}s` }}
            >
              <div className="market-num" style={{ color: c.color }}>{c.num}</div>
              <div className="market-card-label">{c.label}</div>
              <div className="market-card-body">{c.body}</div>
            </div>
          ))}
        </div>

        <p className="market-closer">
          A multi-billion-dollar compliance market, <span>still audited by hand.</span><br />
          We automate the proof.
        </p>
      </div>
    </section>
  )
}
