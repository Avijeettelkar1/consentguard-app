const SITES = ['bbc.com', 'cnn.com', 'nytimes.com', 'theguardian.com', 'forbes.com', 'reddit.com',
  'tripadvisor.com', 'businessinsider.com', 'dailymail.co.uk', 'vice.com', 'buzzfeed.com', 'huffpost.com']

export default function LogoStrip() {
  const doubled = [...SITES, ...SITES]
  return (
    <div className="logostrip">
      <div className="logostrip-label">GDPR violations detected on major sites</div>
      <div className="marquee-outer">
        <div className="marquee-track">
          {doubled.map((site, i) => (
            <span className="marquee-item" key={i}>
              <span className="marquee-dot" />
              {site}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
