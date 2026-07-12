const box = <><rect x="3" y="3" width="18" height="18" rx="1" /><path d="M3 9h18M9 21V9" /></>
const ban = <><circle cx="12" cy="12" r="9" /><line x1="5.6" y1="5.6" x2="18.4" y2="18.4" /></>
const db = <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></>
const file = <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M9 15l2 2 4-4" /></>
const scale = <><path d="M12 3v18M7 8l-4 7h8zM17 8l-4 7h8zM5 21h14" /></>
const wrench = <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />

const STEPS = [
  { n: '01', icon: box, title: 'Isolated sandbox scan', body: 'A fresh browser — no cookies, no history. We record every request on load.' },
  { n: '02', icon: ban, title: 'Auto-click Reject All', body: 'We detect OneTrust, Cookiebot, Didomi and 40+ banners, then click the real “Reject All”.' },
  { n: '03', icon: db, title: 'Cross-reference trackers', body: 'Every request after reject is matched against 6,326 known ad & analytics domains.' },
  { n: '04', icon: file, title: 'Check the cookie policy', body: 'We flag trackers that fired but were never declared in your policy.' },
  { n: '05', icon: scale, title: 'Fine exposure model', body: 'We model your GDPR fine range by violation count and company size.' },
  { n: '06', icon: wrench, title: 'Fixes + DPA complaint', body: 'The exact policy fix, banner config, and a ready-to-file complaint.' },
]

export default function HowItWorks() {
  return (
    <section className="section alt" id="how">
      <div className="shell">
        <div className="section-head">
          <span className="section-label">How it works</span>
          <h2 className="h2">Six steps. One irrefutable report.</h2>
        </div>
      </div>
      <div className="steps">
        {STEPS.map((s) => (
          <div className="step" key={s.n}>
            <div className="step-top">
              <span className="step-n">{s.n}</span>
              <span className="step-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">{s.icon}</svg>
              </span>
            </div>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
