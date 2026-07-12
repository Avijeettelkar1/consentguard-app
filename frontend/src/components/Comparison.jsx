const X = (
  <svg className="x" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
)
const CHECK = (
  <svg className="c" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)

export default function Comparison() {
  return (
    <section className="compare-section">
      <div className="compare-header">
        <span className="eyebrow">The compliance gap</span>
        <h2 className="h2">Manual cookie audits can’t keep up with modern tracking.</h2>
        <p className="lead">
          Consultants audit once a quarter and hand you a static PDF. Trackers change every deploy.
          The gap between “audited” and “actually compliant” is where the fines live.
        </p>
      </div>

      <div className="compare-grid">
        <div className="compare-col">
          <div className="compare-col-head">
            <span className="compare-col-tag">The old way</span>
          </div>
          <h3>Manual audits</h3>
          <ul className="compare-list">
            <li>{X} €5,000+ and weeks of billable consultant hours</li>
            <li>{X} A snapshot that’s stale the day it’s delivered</li>
            <li>{X} No proof — just a spreadsheet of assumptions</li>
            <li>{X} Nothing to actually file or fix with</li>
          </ul>
        </div>

        <div className="compare-col highlight">
          <div className="compare-col-head">
            <span className="compare-col-tag">ConsentGuard</span>
          </div>
          <h3>Automated proof</h3>
          <ul className="compare-list">
            <li>{CHECK} A live scan of real network traffic in ~30 seconds</li>
            <li>{CHECK} Every tracker matched to a 6,324-domain database</li>
            <li>{CHECK} Re-run on every deploy, self-serve, for any site</li>
            <li>{CHECK} Fix, fine exposure, and complaint generated for you</li>
          </ul>
        </div>

        <div className="compare-col">
          <div className="compare-col-head">
            <span className="compare-col-tag">The result</span>
          </div>
          <h3>Defensible compliance</h3>
          <ul className="compare-list">
            <li>{CHECK} Evidence a regulator will accept</li>
            <li>{CHECK} Fines avoided before they’re ever issued</li>
            <li>{CHECK} Legal, engineering and marketing on the same page</li>
            <li>{CHECK} Continuous confidence, not annual anxiety</li>
          </ul>
        </div>
      </div>
    </section>
  )
}
