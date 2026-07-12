const ROWS = [
  { domain: 'connect.facebook.net', company: 'Meta', cat: 'advertising', bad: true },
  { domain: 'bat.bing.com', company: 'Microsoft', cat: 'advertising', bad: true },
  { domain: 'analytics.twitter.com', company: 'X / Twitter', cat: 'social', bad: true },
  { domain: 'cdn.segment.com', company: 'Twilio Segment', cat: 'analytics', bad: true },
  { domain: 'google-analytics.com', company: 'Google', cat: 'analytics', bad: false },
]

export default function ReportShot() {
  return (
    <div className="rshot">
      <div className="rshot-bar">
        <span className="rshot-dot r" /><span className="rshot-dot y" /><span className="rshot-dot g" />
        <span className="rshot-url">consentguard.io/scan/bbc.com</span>
        <span className="rshot-live"><span className="rshot-live-dot" /> Scan complete</span>
      </div>

      <div className="rshot-body">
        <div className="rshot-verdict">
          <div className="rshot-verdict-left">
            <span className="rshot-vdot" />
            <div>
              <div className="rshot-vtitle">GDPR violation detected on bbc.com</div>
              <div className="rshot-vsub">4 undeclared trackers fired after “Reject All”</div>
            </div>
          </div>
          <div className="rshot-badges">
            <span className="rshot-badge red">4 undeclared</span>
            <span className="rshot-badge gray">OneTrust</span>
            <span className="rshot-badge green">Reject clicked ✓</span>
          </div>
        </div>

        <table className="rshot-table">
          <thead>
            <tr><th>Domain</th><th>Company</th><th>Category</th><th>Status</th></tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.domain}>
                <td><span className="rshot-domain">{r.domain}</span></td>
                <td className="rshot-company">{r.company}</td>
                <td><span className="rshot-cat">{r.cat}</span></td>
                <td>
                  <span className={r.bad ? 'rshot-status bad' : 'rshot-status ok'}>
                    {r.bad ? 'UNDECLARED' : 'DECLARED'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="rshot-footer">
          <div className="rshot-stat">
            <div className="rshot-stat-val red">4</div>
            <div className="rshot-stat-label">Undeclared trackers</div>
          </div>
          <div className="rshot-stat">
            <div className="rshot-stat-val amber">€200k–€800k</div>
            <div className="rshot-stat-label">GDPR fine exposure</div>
          </div>
          <div className="rshot-stat">
            <div className="rshot-stat-val green">Ready</div>
            <div className="rshot-stat-label">DPA complaint letter</div>
          </div>
          <span className="rshot-badge green big">Full report generated ✓</span>
        </div>
      </div>
    </div>
  )
}
