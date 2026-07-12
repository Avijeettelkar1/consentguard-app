const VENDORS = [
  'Google Analytics', 'Meta Pixel', 'DoubleClick', 'TikTok Pixel', 'Microsoft UET',
  'Criteo', 'Hotjar', 'LinkedIn Insight', 'Amazon Ads', 'Segment',
  'Snap Pixel', 'MS Clarity', 'Quantcast', 'FingerprintJS',
]

export default function TrackerMarquee() {
  const doubled = [...VENDORS, ...VENDORS]
  return (
    <div className="tmarquee">
      <div className="tmarquee-label">Catching trackers from</div>
      <div className="tmarquee-outer">
        <div className="tmarquee-track">
          {doubled.map((v, i) => (
            <span className="tmarquee-item" key={i}>
              <span className="tmarquee-dot" />
              {v}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
