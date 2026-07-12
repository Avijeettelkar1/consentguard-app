const STACK = [
  {
    name: 'Playwright',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9" /><path d="M12 3v18M3 12h18" />
      </svg>
    ),
  },
  {
    name: 'Claude',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" /><path d="M8 12h8M12 8v8" />
      </svg>
    ),
  },
  {
    name: 'Disconnect.me',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 6 6 18M8 6a4 4 0 0 0-4 4M16 18a4 4 0 0 0 4-4" />
      </svg>
    ),
  },
  {
    name: 'Daytona',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18" />
      </svg>
    ),
  },
]

export default function TrustBar() {
  return (
    <div className="trust-bar">
      <div className="trust-bar-inner">
        <span className="trust-bar-label">Built on a serious stack</span>
        <div className="trust-logos">
          {STACK.map((s) => (
            <span className="trust-logo" key={s.name}>
              {s.icon}
              {s.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
