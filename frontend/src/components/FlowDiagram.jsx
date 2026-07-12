const STEPS = [
  {
    num: 'Step 1',
    title: 'Scan',
    body: 'A fresh, isolated Chromium sandbox opens your site — no cookies, no history, no extensions.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
      </svg>
    ),
  },
  {
    num: 'Step 2',
    title: 'Detect',
    body: 'We click “Reject All,” then watch every network request and match it against 6,324 known trackers.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  {
    num: 'Step 3',
    title: 'Prove',
    body: 'Claude reads the cookie policy and flags trackers that fired but were never declared — a GDPR violation.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
        <path d="m9 15 2 2 4-4" />
      </svg>
    ),
  },
  {
    num: 'Step 4',
    title: 'Fix',
    body: 'You get the exact policy text, the banner config fix, your fine exposure, and a ready-to-file complaint.',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </svg>
    ),
    done: true,
  },
]

export default function FlowDiagram() {
  return (
    <section className="flow-section" id="howItWorks">
      <div className="flow-header">
        <span className="eyebrow">How it works</span>
        <h2 className="h2">From URL to filed complaint, automatically.</h2>
        <p className="lead">One pipeline runs the whole audit inside a sandbox — no plugins, no cached state, no manual review.</p>
      </div>

      <div className="flow-track">
        {STEPS.map((s) => (
          <div className={`flow-step${s.done ? ' done' : ''}`} key={s.title}>
            <div className="flow-icon">{s.icon}</div>
            <div className="flow-num">{s.num}</div>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
