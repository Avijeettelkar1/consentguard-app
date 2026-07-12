import { useEffect, useRef, useState } from 'react'
import { useInView } from '../hooks/useInView'

function CountUp({ to, prefix = '', suffix = '', duration = 1400, start }) {
  const [val, setVal] = useState(0)
  const raf = useRef()

  useEffect(() => {
    if (!start) return
    const t0 = performance.now()
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / duration)
      const eased = 1 - Math.pow(1 - p, 3) // easeOutCubic
      setVal(Math.round(to * eased))
      if (p < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [start, to, duration])

  return <>{prefix}{val.toLocaleString('en-US')}{suffix}</>
}

const STATS = [
  { to: 73, suffix: '%', color: 'var(--rose)', label: 'of sites still fire trackers after “Reject All”' },
  { to: 6326, suffix: '', color: 'var(--ink)', label: 'tracker domains cross-referenced on every scan' },
  { to: 5, prefix: '€', suffix: 'B+', color: 'var(--brand)', label: 'in GDPR fines issued since 2018' },
]

export default function StatsCounter() {
  const [ref, inView] = useInView(0.35)
  return (
    <section className="counters" ref={ref}>
      <div className="counters-inner">
        {STATS.map((s) => (
          <div className="counter" key={s.label}>
            <div className="counter-val" style={{ color: s.color }}>
              <CountUp to={s.to} prefix={s.prefix} suffix={s.suffix} start={inView} />
            </div>
            <div className="counter-label">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
