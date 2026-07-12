function MockAuditor() {
  return (
    <div className="mock">
      <div className="mock-bar"><span className="mock-dot r" /><span className="mock-dot y" /><span className="mock-dot g" /><span className="mock-title">reject-all · session</span></div>
      <div className="mock-body">
        <div className="mock-row"><span className="mock-domain">connect.facebook.net</span><span className="mock-tag-red">FIRED</span></div>
        <div className="mock-row"><span className="mock-domain">bat.bing.com</span><span className="mock-tag-red">FIRED</span></div>
        <div className="mock-row"><span className="mock-domain">cdn.segment.com</span><span className="mock-tag-red">FIRED</span></div>
      </div>
    </div>
  )
}
function MockTrackers() {
  return (
    <div className="mock">
      <div className="mock-bar"><span className="mock-dot r" /><span className="mock-dot y" /><span className="mock-dot g" /><span className="mock-title">tracker analysis</span></div>
      <div className="mock-body">
        <div className="mock-row"><span className="mock-domain">facebook.net · Meta</span><span className="mock-tag-red">UNDECLARED</span></div>
        <div className="mock-row"><span className="mock-domain">bing.com · Microsoft</span><span className="mock-tag-red">UNDECLARED</span></div>
        <div className="mock-row"><span className="mock-domain">g-analytics · Google</span><span className="mock-tag-green">DECLARED</span></div>
      </div>
    </div>
  )
}
function MockFine() {
  return (
    <div className="mock">
      <div className="mock-bar"><span className="mock-dot r" /><span className="mock-dot y" /><span className="mock-dot g" /><span className="mock-title">gdpr exposure</span></div>
      <div className="mock-body">
        <div className="mock-row"><span className="mock-domain">Small company</span><span className="mock-tag-red">€50k–€200k</span></div>
        <div className="mock-row"><span className="mock-domain">Medium company</span><span className="mock-tag-red">€200k–€800k</span></div>
        <div className="mock-row"><span className="mock-domain">Max · Art. 83</span><span className="mock-tag-red">4% revenue</span></div>
      </div>
    </div>
  )
}
function MockComplaint() {
  return (
    <div className="mock">
      <div className="mock-bar"><span className="mock-dot r" /><span className="mock-dot y" /><span className="mock-dot g" /><span className="mock-title">dpa-complaint.txt</span></div>
      <div className="mock-body" style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--text2)', lineHeight: 1.7 }}>
        <div style={{ color: 'var(--text)' }}>Dear Data Protection Authority,</div>
        <div>I submit this formal complaint</div>
        <div>regarding bbc.com. After selecting</div>
        <div>“Reject All,” the following trackers…</div>
        <div style={{ marginTop: '0.4rem' }}><span className="mock-tag-green">Ready to file ✓</span></div>
      </div>
    </div>
  )
}

const CARDS = [
  { tag: 'Web Auditor', title: 'Watch what fires after “Reject All.”', body: 'A real browser session records every network request the moment consent is refused — the evidence a regulator actually cares about.', shot: <MockAuditor /> },
  { tag: 'Tracker Analysis', title: '6,324 trackers, cross-referenced instantly.', body: 'Each request is matched to its owner and category, then checked against your cookie policy. Undeclared trackers are flagged as violations.', shot: <MockTrackers /> },
  { tag: 'Fine Exposure', title: 'Know exactly what it could cost.', body: 'We translate the violations into a GDPR fine range by company size under Art. 83 — the number that makes leadership pay attention.', shot: <MockFine /> },
  { tag: 'DPA Complaint', title: 'A complaint, drafted and ready to file.', body: 'Claude drafts a formal, submission-ready complaint to your national Data Protection Authority — plus the exact policy and banner fix.', shot: <MockComplaint /> },
]

export default function ProductGrid() {
  return (
    <section className="product-section">
      <div className="product-header">
        <span className="eyebrow">The product</span>
        <h2 className="h2">Everything you need to prove — and fix — compliance.</h2>
        <p className="lead">One scan produces four deliverables, laid out like a legal exhibit and ready to act on.</p>
      </div>

      <div className="product-grid">
        {CARDS.map((c) => (
          <article className="prod-card" key={c.tag}>
            <div className="prod-card-shot">{c.shot}</div>
            <div className="prod-card-body">
              <span className="prod-card-tag">{c.tag}</span>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
