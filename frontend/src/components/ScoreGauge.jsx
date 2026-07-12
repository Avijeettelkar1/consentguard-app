import { useEffect, useState } from 'react'
import { gradeColor } from '../lib/score'

export default function ScoreGauge({ score = 0, grade = 'F', label = '', size = 128 }) {
  const stroke = 10
  const r = size / 2 - stroke
  const circ = 2 * Math.PI * r
  const [dash, setDash] = useState(0)
  const color = gradeColor(grade)

  useEffect(() => {
    const id = requestAnimationFrame(() => setDash(circ * (score / 100)))
    return () => cancelAnimationFrame(id)
  }, [score, circ])

  return (
    <div className="gauge">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--bg3)" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 1.1s cubic-bezier(0.16,1,0.3,1)' }}
        />
      </svg>
      <div className="gauge-center">
        <span className="gauge-grade" style={{ color }}>{grade}</span>
        <span className="gauge-score">{score}<i>/100</i></span>
      </div>
      {label && <div className="gauge-label" style={{ color }}>{label}</div>}
    </div>
  )
}
