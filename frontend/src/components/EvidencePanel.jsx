import { useState, useEffect } from 'react'

const BEFORE = [
  'google-analytics.com', 'doubleclick.net', 'connect.facebook.net', 'static.assets.js',
]
const AFTER = [
  { d: 'google-analytics.com', leak: true },
  { d: 'doubleclick.net', leak: true },
  { d: 'connect.facebook.net', leak: true },
  { d: 'static.assets.js', blocked: true },
]

// Self-playing looped demo: baseline streams in → "Reject All" clicked →
// trackers keep firing (LEAK pops) → verdict. Loops forever.
const LOOP_MS = 9000

export default function EvidencePanel() {
  const [t, setT] = useState(0) // animation step counter
  const [cycle, setCycle] = useState(0)

  useEffect(() => {
    const timers = []
    // step schedule (ms → step value)
    const schedule = [
      [300, 1], [600, 2], [900, 3], [1200, 4],       // before rows 1-4
      [2000, 5],                                      // status: clicking reject
      [2900, 6], [3250, 7], [3600, 8], [3950, 9],     // after rows 1-4
      [4600, 10],                                     // verdict + stats
    ]
    schedule.forEach(([ms, step]) => timers.push(setTimeout(() => setT(step), ms)))
    timers.push(setTimeout(() => { setT(0); setCycle((c) => c + 1) }, LOOP_MS))
    return () => timers.forEach(clearTimeout)
  }, [cycle])

  const status =
    t < 5 ? 'capturing baseline…'
    : t < 6 ? 'clicking “Reject All”…'
    : t < 10 ? 'recording post-consent traffic…'
    : '3 trackers still firing after reject'

  return (
    <div className="evidence">
      <div className="evidence-bar">
        <span className="addr">consentguard://scan/live</span>
        <span className="rec"><span className="rdot" /> RECORDING</span>
      </div>

      <div className="evidence-cols">
        <div className="evidence-col">
          <div className="evidence-grp-label">Before consent</div>
          {BEFORE.map((d, i) => (
            <div className={`ev-row ev-anim${t >= i + 1 ? ' on' : ''}`} key={d}>
              <span className="method">GET</span>
              <span className="dom">{d}</span>
            </div>
          ))}
        </div>

        <div className="evidence-col">
          <div className="evidence-grp-label">After “Reject All”</div>
          {AFTER.map((r, i) => (
            <div
              className={`ev-row ev-anim${t >= i + 6 ? ' on' : ''}${r.leak ? ' violation' : ''}${r.blocked ? ' blocked' : ''}`}
              key={r.d}
            >
              <span className="method">GET</span>
              <span className="dom">{r.d}</span>
              {r.leak && t >= i + 6 && <span className="leak leak-pop">LEAK</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="evidence-foot">
        <span className="fmono">{status}</span>
        <span className={`badge-rose ev-anim${t >= 10 ? ' on' : ''}`}>Serious Violations</span>
      </div>

      <div className="evidence-stats">
        <div className="st">
          <div className="st-label">Fine exposure</div>
          <div className={`st-val rose ev-anim${t >= 10 ? ' on' : ''}`}>€180k – €950k</div>
        </div>
        <div className="st">
          <div className="st-label">Undeclared</div>
          <div className={`st-val ev-anim${t >= 10 ? ' on' : ''}`}>3 vendors</div>
        </div>
      </div>
    </div>
  )
}
