import { useState } from 'react'

const QA = [
  {
    q: 'What exactly does ConsentGuard detect?',
    a: 'Trackers that fire after a visitor clicks “Reject All” but aren’t declared in your cookie policy. Under GDPR, refused consent means those requests shouldn’t happen — we prove, with real network traffic, that they do.',
  },
  {
    q: 'How is this different from a manual cookie audit?',
    a: 'A consultancy audit is a one-time snapshot that costs thousands and is stale the moment your site changes. ConsentGuard runs a live scan in ~30 seconds, self-serve, and can be re-run on every deploy — with evidence attached, not assumptions.',
  },
  {
    q: 'Do I need to install anything on my site?',
    a: 'No. We scan from the outside in an isolated Chromium sandbox, exactly like a real visitor. There’s no tag, SDK, or code change required on your end.',
  },
  {
    q: 'How accurate is the tracker detection?',
    a: 'Every request is matched against the open-source Disconnect.me database of 6,324+ known tracking domains, then cross-checked against your declared cookie policy. Ambiguous cases are surfaced for review rather than silently passed.',
  },
  {
    q: 'What do I actually get at the end of a scan?',
    a: 'A compliance verdict, the full list of undeclared trackers and who owns them, your estimated GDPR fine exposure, the exact policy and banner-config fix, and a formal complaint letter ready to file with a Data Protection Authority.',
  },
  {
    q: 'Is my data or the scanned site’s data stored?',
    a: 'Scans run in ephemeral, isolated sandboxes that are torn down after each run. We keep the report, not the raw browsing session — and nothing is installed on the target site.',
  },
  {
    q: 'Which regulations does this cover?',
    a: 'The core focus is GDPR (Articles 7 and 83) and the ePrivacy Directive that governs cookies in the EU/UK. The same tracker-level evidence maps cleanly onto emerging US state privacy laws.',
  },
  {
    q: 'Who is ConsentGuard for?',
    a: 'Privacy and legal teams who need defensible proof, engineering teams who need to know what to fix, and agencies who audit consent for clients at scale.',
  },
]

function Item({ item, open, onToggle }) {
  return (
    <div className={`faq-item${open ? ' open' : ''}`}>
      <button className="faq-q" onClick={onToggle}>
        {item.q}
        <span className="faq-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </span>
      </button>
      <div className="faq-a">
        <div className="faq-a-inner">{item.a}</div>
      </div>
    </div>
  )
}

export default function FAQ() {
  const [open, setOpen] = useState(0)
  return (
    <section className="faq-section">
      <div className="faq-inner">
        <div className="faq-header">
          <span className="eyebrow">FAQ</span>
          <h2 className="h2">Questions, answered.</h2>
        </div>
        <div className="faq-list">
          {QA.map((item, i) => (
            <Item key={i} item={item} open={open === i} onToggle={() => setOpen(open === i ? -1 : i)} />
          ))}
        </div>
      </div>
    </section>
  )
}
