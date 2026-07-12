import { useInView } from '../hooks/useInView'

export default function SpeedCompare() {
  const [ref, inView] = useInView(0.3)

  return (
    <section className="section speed-section">
      <div className="shell">
        <div className="section-head center" style={{ textAlign: 'center', margin: '0 auto' }}>
          <span className="section-label">From weeks to seconds</span>
          <h2 className="h2">The audit that used to take a law firm.</h2>
          <p className="lead" style={{ marginTop: '1.25rem' }}>
            Same evidence. Same defensibility. A fraction of the time and cost.
          </p>
        </div>

        <div className={`speed-bars${inView ? ' in-view' : ''}`} ref={ref}>
          <div className="speed-row">
            <div className="speed-meta">
              <span className="speed-name">Manual consultancy audit</span>
              <span className="speed-val">≈ 3 weeks · €5,000+</span>
            </div>
            <div className="speed-track">
              <div className="speed-fill old" />
            </div>
          </div>

          <div className="speed-row">
            <div className="speed-meta">
              <span className="speed-name brand">ConsentGuard scan</span>
              <span className="speed-val brand">≈ 30 seconds · free</span>
            </div>
            <div className="speed-track">
              <div className="speed-fill new" />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
