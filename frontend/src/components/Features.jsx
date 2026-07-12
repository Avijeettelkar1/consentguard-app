import { useInView } from '../hooks/useInView'

function BrowserSVG() {
  return (
    <svg width="100%" height="100%" viewBox="0 0 320 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="320" height="200" rx="10" fill="#0D0F13"/>
      <rect width="320" height="36" rx="10" fill="#111520"/>
      <rect y="26" width="320" height="10" fill="#111520"/>
      <circle cx="20" cy="18" r="4.5" fill="#FF5F57"/>
      <circle cx="34" cy="18" r="4.5" fill="#FEBC2E"/>
      <circle cx="48" cy="18" r="4.5" fill="#28C840"/>
      <rect x="70" y="10" width="180" height="16" rx="5" fill="#0A0B0D" stroke="#1A2030" strokeWidth="1"/>
      <text x="82" y="22" fontSize="8" fill="#354050" fontFamily="monospace">bbc.com</text>
      {/* Page content */}
      <rect x="12" y="46" width="296" height="8" rx="3" fill="#171C29"/>
      <rect x="12" y="60" width="220" height="8" rx="3" fill="#171C29"/>
      {/* Cookie banner */}
      <rect x="12" y="108" width="296" height="78" rx="8" fill="#111520" stroke="#222B3A" strokeWidth="1.5"/>
      <text x="24" y="128" fontSize="9" fill="#7A8A9A" fontFamily="sans-serif">We use cookies to improve your experience.</text>
      <text x="24" y="143" fontSize="9" fill="#354050" fontFamily="sans-serif">See our cookie policy for more information.</text>
      {/* Reject btn */}
      <rect x="24" y="152" width="80" height="22" rx="5" fill="#171C29" stroke="#222B3A" strokeWidth="1.5"/>
      <text x="44" y="167" fontSize="8.5" fill="#7A8A9A" fontFamily="sans-serif">Reject All</text>
      {/* Accept btn */}
      <rect x="116" y="152" width="80" height="22" rx="5" fill="#6025C0"/>
      <text x="133" y="167" fontSize="8.5" fill="white" fontFamily="sans-serif">Accept All</text>
      {/* Red cursor over Reject */}
      <circle cx="64" cy="163" r="5" fill="none" stroke="#ef4444" strokeWidth="1.8"/>
      <circle cx="64" cy="163" r="2.5" fill="#ef4444"/>
      {/* VIOLATION badges firing */}
      <rect x="210" y="118" width="86" height="18" rx="4" fill="rgba(239,68,68,0.1)" stroke="rgba(239,68,68,0.35)" strokeWidth="1"/>
      <text x="218" y="131" fontSize="7" fill="#ef4444" fontFamily="monospace">facebook.net ✗</text>
      <rect x="210" y="140" width="86" height="18" rx="4" fill="rgba(239,68,68,0.1)" stroke="rgba(239,68,68,0.35)" strokeWidth="1"/>
      <text x="218" y="153" fontSize="7" fill="#ef4444" fontFamily="monospace">bat.bing.com ✗</text>
      <rect x="210" y="162" width="86" height="18" rx="4" fill="rgba(239,68,68,0.1)" stroke="rgba(239,68,68,0.35)" strokeWidth="1"/>
      <text x="218" y="175" fontSize="7" fill="#ef4444" fontFamily="monospace">segment.com ✗</text>
    </svg>
  )
}

function ViolationsSVG() {
  const rows = [
    { d: 'facebook.net',    c: 'advertising', bad: true },
    { d: 'bat.bing.com',    c: 'advertising', bad: true },
    { d: 'ads-twitter.com', c: 'social',       bad: true },
    { d: 'segment.com',     c: 'analytics',   bad: true },
    { d: 'google-analytics', c: 'analytics',  bad: false },
  ]
  return (
    <svg width="100%" height="100%" viewBox="0 0 320 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="320" height="200" rx="10" fill="#0D0F13"/>
      <rect width="320" height="36" rx="10" fill="#111520"/>
      <rect y="26" width="320" height="10" fill="#111520"/>
      <circle cx="20" cy="18" r="4.5" fill="#FF5F57"/>
      <circle cx="34" cy="18" r="4.5" fill="#FEBC2E"/>
      <circle cx="48" cy="18" r="4.5" fill="#28C840"/>
      <text x="110" y="22" fontSize="7" fill="#354050" fontFamily="monospace">ConsentGuard — Tracker Analysis</text>
      {/* Column headers */}
      <text x="16" y="52" fontSize="6.5" fill="#354050" fontFamily="monospace" fontWeight="bold">DOMAIN</text>
      <text x="160" y="52" fontSize="6.5" fill="#354050" fontFamily="monospace" fontWeight="bold">CATEGORY</text>
      <text x="258" y="52" fontSize="6.5" fill="#354050" fontFamily="monospace" fontWeight="bold">STATUS</text>
      <line x1="12" y1="56" x2="308" y2="56" stroke="#1A2030" strokeWidth="1"/>
      {rows.map((r, i) => (
        <g key={i}>
          <text x="16" y={72 + i * 26} fontSize="8" fill="#E8EDF2" fontFamily="monospace">{r.d}</text>
          <rect x="158" y={60 + i * 26} width="62" height="14" rx="3" fill="#111520" stroke="#1A2030" strokeWidth="0.8"/>
          <text x="163" y={71 + i * 26} fontSize="6.5" fill="#7A8A9A" fontFamily="monospace">{r.c}</text>
          <rect x="252" y={60 + i * 26} width="56" height="14" rx="3" fill={r.bad ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)'} stroke={r.bad ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)'} strokeWidth="0.8"/>
          <text x="257" y={71 + i * 26} fontSize="6" fill={r.bad ? '#ef4444' : '#22c55e'} fontFamily="monospace" fontWeight="bold">{r.bad ? 'UNDECLARED' : 'DECLARED'}</text>
        </g>
      ))}
    </svg>
  )
}

function ReportSVG() {
  return (
    <svg width="100%" height="100%" viewBox="0 0 320 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="320" height="200" rx="10" fill="#0D0F13"/>
      <rect width="320" height="36" rx="10" fill="#111520"/>
      <rect y="26" width="320" height="10" fill="#111520"/>
      <circle cx="20" cy="18" r="4.5" fill="#FF5F57"/>
      <circle cx="34" cy="18" r="4.5" fill="#FEBC2E"/>
      <circle cx="48" cy="18" r="4.5" fill="#28C840"/>
      <text x="105" y="22" fontSize="7" fill="#354050" fontFamily="monospace">ConsentGuard — GDPR Report</text>
      {/* Fine section */}
      <rect x="12" y="44" width="140" height="70" rx="6" fill="#111520" stroke="#222B3A" strokeWidth="1"/>
      <text x="20" y="59" fontSize="7.5" fill="#7A8A9A" fontFamily="sans-serif">GDPR Fine Exposure</text>
      <text x="20" y="76" fontSize="8" fill="#7A8A9A" fontFamily="sans-serif">Small company</text>
      <text x="20" y="88" fontSize="8.5" fill="#ef4444" fontFamily="monospace" fontWeight="bold">€50k–€200k</text>
      <text x="20" y="101" fontSize="8" fill="#7A8A9A" fontFamily="sans-serif">Medium company</text>
      <text x="20" y="109" fontSize="8.5" fill="#ef4444" fontFamily="monospace" fontWeight="bold">€200k–€800k</text>
      {/* Complaint section */}
      <rect x="164" y="44" width="144" height="70" rx="6" fill="#111520" stroke="#222B3A" strokeWidth="1"/>
      <text x="172" y="59" fontSize="7.5" fill="#7A8A9A" fontFamily="sans-serif">DPA Complaint Letter</text>
      <text x="172" y="73" fontSize="6.5" fill="#354050" fontFamily="monospace">Dear Data Protection</text>
      <text x="172" y="83" fontSize="6.5" fill="#354050" fontFamily="monospace">Authority, I submit</text>
      <text x="172" y="93" fontSize="6.5" fill="#354050" fontFamily="monospace">this formal complaint</text>
      <text x="172" y="103" fontSize="6.5" fill="#354050" fontFamily="monospace">regarding...</text>
      <rect x="172" y="108" width="60" height="0.8" fill="#222B3A"/>
      {/* Policy fix */}
      <rect x="12" y="124" width="296" height="58" rx="6" fill="#111520" stroke="#222B3A" strokeWidth="1"/>
      <text x="20" y="139" fontSize="7.5" fill="#7A8A9A" fontFamily="sans-serif">Cookie Policy Fix</text>
      <rect x="20" y="146" width="280" height="7" rx="2" fill="#1A2030"/>
      <rect x="20" y="157" width="230" height="7" rx="2" fill="#1A2030"/>
      <rect x="20" y="168" width="200" height="7" rx="2" fill="#1A2030"/>
      {/* Ready badge */}
      <rect x="230" y="128" width="70" height="16" rx="4" fill="rgba(34,197,94,0.12)" stroke="rgba(34,197,94,0.3)" strokeWidth="0.8"/>
      <text x="237" y="139" fontSize="6.5" fill="#22c55e" fontFamily="monospace">Ready to send ✓</text>
    </svg>
  )
}

const STEPS = [
  {
    num: '01',
    tag: 'Scan & Detect',
    title: 'We click Reject All. Then watch what fires anyway.',
    body: 'A fresh Chromium sandbox with no cookies, no history. We click Accept All and Reject All in separate sessions, intercepting every network request to compare what fires between the two.',
    svg: <BrowserSVG />,
    accent: '#7c3aed',
  },
  {
    num: '02',
    tag: 'Analyze',
    title: '6,324 tracker domains. Cross-referenced instantly.',
    body: 'Every request after rejection is matched against the Disconnect.me tracker database. Trackers not declared in the site\'s cookie policy are flagged as GDPR Art. 7 violations.',
    svg: <ViolationsSVG />,
    accent: '#ef4444',
  },
  {
    num: '03',
    tag: 'Report & Act',
    title: 'A ready-to-file complaint. And an exact fix.',
    body: 'We calculate GDPR fine exposure by company size, generate the exact text needed to fix your cookie policy and banner config, and draft a formal DPA complaint letter — ready to file.',
    svg: <ReportSVG />,
    accent: '#22c55e',
  },
]

function Step({ step, index }) {
  const [ref, inView] = useInView(0.12)
  const isReverse = index % 2 === 1

  return (
    <div ref={ref} className={`feat-step${isReverse ? ' reverse' : ''}${inView ? ' in-view' : ''}`}>
      <div className="feat-text">
        <span className="feat-num" style={{ color: step.accent }}>{step.num}</span>
        <span className="feat-tag">{step.tag}</span>
        <h3 className="feat-title">{step.title}</h3>
        <p className="feat-body">{step.body}</p>
      </div>
      <div className="feat-img">
        {step.svg}
      </div>
    </div>
  )
}

export default function Features() {
  return (
    <section className="features-section" id="howItWorks">
      <div className="features-inner">
        <div className="features-header">
          <span className="section-tag">How it works</span>
          <h2 className="features-h2">From scan to compliance report<br />in 30 seconds</h2>
        </div>
        <div className="features-steps">
          {STEPS.map((step, i) => (
            <Step key={step.num} step={step} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
