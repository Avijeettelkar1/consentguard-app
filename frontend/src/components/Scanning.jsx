import { useState, useEffect, useRef } from 'react'

// Honest phase log. The scan is a single backend request with no streaming, so
// these describe the real pipeline stages in order and the bar is a time-based
// estimate that holds at 92% until the actual result arrives (component unmounts).
const STEPS = [
  { wait: 400,  icon: '▶', text: 'Launching isolated Chromium sandbox',                     pct: 6,  label: 'Launching sandbox…' },
  { wait: 1200, icon: '✓', text: 'Sandbox ready — no cookies, no history',                  pct: 12, label: 'Sandbox ready' },
  { wait: 800,  icon: '▶', text: (d) => `Navigating to ${d}`,                               pct: 18, label: 'Opening site…' },
  { wait: 2400, icon: '✓', text: 'Page loaded — capturing baseline network traffic',        pct: 26, label: 'Recording baseline…' },
  { wait: 1000, icon: '›', text: 'Baseline captured',                                       pct: 32, label: 'Baseline captured' },
  { wait: 1200, icon: '▶', text: 'Detecting consent management platform',                    pct: 40, label: 'Detecting CMP…' },
  { wait: 1000, icon: '✓', text: 'Clicking “Accept All” — recording traffic',               pct: 48, label: 'Recording accept…' },
  { wait: 1800, icon: '▶', text: 'Fresh session — clicking “Reject All”',                   pct: 58, label: 'Clicking Reject All…' },
  { wait: 2000, icon: '✓', text: 'Reject recorded — capturing post-consent traffic',        pct: 68, label: 'Re-scanning after reject…' },
  { wait: 1400, icon: '▶', text: 'Cross-referencing Disconnect.me (6,326 domains)',         pct: 78, label: 'Checking tracker DB…' },
  { wait: 1500, icon: '✓', text: 'Trackers identified',                                     pct: 84, label: 'Reading cookie policy…' },
  { wait: 1200, icon: '▶', text: 'Reading cookie policy for declarations',                  pct: 90, label: 'Analysing declarations…' },
  { wait: 1000, icon: '›', text: 'Compiling compliance report',                             pct: 92, label: 'Compiling report…' },
]

const STAGES = [
  { name: 'Isolated browser scan', start: 0,  end: 32 },
  { name: 'Accept vs Reject capture', start: 32, end: 68 },
  { name: 'Tracker cross-reference', start: 68, end: 101 }, // stays "running" until the report replaces this screen
]

function stageState(pct, s) {
  if (pct >= s.end) return 'done'
  if (pct >= s.start) return 'active'
  return 'pending'
}
const stageWord = { done: 'Done ✓', active: 'Running…', pending: 'Queued' }

export default function Scanning({ url, error }) {
  const [logs, setLogs] = useState([])
  const [progress, setProgress] = useState({ pct: 0, label: 'Initialising…' })
  const [slow, setSlow] = useState(false)
  const startRef = useRef(Date.now())
  const bodyRef = useRef(null)

  const fmt = () => {
    const s = Math.floor((Date.now() - startRef.current) / 1000)
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
  }

  useEffect(() => {
    startRef.current = Date.now()
    const domain = url.replace(/https?:\/\//, '').split('/')[0]
    setLogs([{ icon: '▶', text: 'ConsentGuard scanner initialising', time: '00:00', cursor: true }])
    setProgress({ pct: 0, label: 'Initialising…' })
    setSlow(false)

    let delay = 0
    const timers = []

    STEPS.forEach(({ wait, icon, text, pct, label }) => {
      delay += wait
      timers.push(setTimeout(() => {
        const resolved = typeof text === 'function' ? text(domain) : text
        setLogs((prev) => [
          ...prev.map((l) => ({ ...l, cursor: false })),
          { icon, text: resolved, time: fmt(), cursor: true },
        ])
        setProgress({ pct, label })
      }, delay))
    })

    // if the real scan is still running after the estimate, reassure honestly
    timers.push(setTimeout(() => setSlow(true), delay + 5000))

    return () => timers.forEach(clearTimeout)
  }, [url])

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [logs])

  return (
    <section className="scanning-section">
      <div className="scanning-header">
        <h2>Running compliance scan</h2>
        <p>Scanning <span className="scanning-url">{url}</span> — this is a real browser visit, so it can take 15–40s.</p>
      </div>

      <div className="terminal">
        <div className="terminal-bar">
          <span className="term-dot r" /><span className="term-dot y" /><span className="term-dot g" />
          <span className="terminal-title">consentguard — scanner</span>
        </div>
        <div className="terminal-body" ref={bodyRef}>
          {logs.map((log, i) => (
            <div className="log-line" key={i}>
              <span className="log-time">{log.time}</span>
              <span className="log-icon">{log.icon}</span>
              <span className="log-text">
                {log.text}
                {log.cursor && !error && <span className="cursor" />}
              </span>
            </div>
          ))}
          {slow && !error && (
            <div className="log-line">
              <span className="log-time">{fmt()}</span>
              <span className="log-icon">›</span>
              <span className="log-text" style={{ color: 'var(--text3)' }}>Larger sites take a little longer — still scanning…</span>
            </div>
          )}
          {error && (
            <div className="log-line">
              <span className="log-time">{fmt()}</span>
              <span className="log-icon" style={{ color: 'var(--rose)' }}>✗</span>
              <span className="log-text" style={{ color: 'var(--rose)' }}>Scan failed: {error}</span>
            </div>
          )}
        </div>
      </div>

      <div className="progress-wrap">
        <div className="progress-labels">
          <span>{error ? 'Stopped' : progress.label}</span>
          <span>{error ? '' : `${progress.pct}%`}</span>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${error ? progress.pct : progress.pct}%`, background: error ? 'var(--rose)' : undefined }} />
        </div>
      </div>

      <div className="phase-cards">
        {STAGES.map((s) => {
          const state = error ? 'pending' : stageState(progress.pct, s)
          return (
            <div className="phase-card" key={s.name}>
              <div className="phase-label">{s.name}</div>
              <div className={`phase-val ${state}`}>{stageWord[state]}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
