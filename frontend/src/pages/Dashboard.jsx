import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext'
import { fetchScan, saveScan, listScans, getScan, deleteScan } from '../api'
import { normalizeUrl } from '../lib/validateDomain'
import { scoreFromResult, gradeColor } from '../lib/score'
import Scanning from '../components/Scanning'
import Results from '../components/Results'
import Watchtower from '../components/Watchtower'

const fmtDate = (iso) => {
  try { return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) }
  catch { return '' }
}

export default function Dashboard() {
  const { token, user, logout } = useAuth()
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [view, setView] = useState('idle') // idle | scanning | results
  const [scanUrl, setScanUrl] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [inputError, setInputError] = useState(null)
  const [scans, setScans] = useState([])
  const [tab, setTab] = useState('scan')
  const [showAuth, setShowAuth] = useState(false)
  const [authUser, setAuthUser] = useState('')
  const [authPass, setAuthPass] = useState('')
  const [authNotice, setAuthNotice] = useState(null)

  const firstName = (user?.name || 'there').split(' ')[0]

  const refresh = useCallback(async () => {
    if (!token) return
    try { const d = await listScans(token); setScans(d.scans || []) } catch { /* ignore */ }
  }, [token])

  useEffect(() => { refresh() }, [refresh])

  const runScan = async (e) => {
    e.preventDefault()
    const check = normalizeUrl(url)
    if (!check.ok) { setInputError(check.error); return }
    setInputError(null)
    setAuthNotice(null)
    setScanUrl(check.url)
    setError(null)
    setResults(null)
    setView('scanning')
    const auth = showAuth && authUser.trim()
      ? { username: authUser.trim(), password: authPass }
      : undefined
    try {
      const data = await fetchScan(check.url, auth)
      if (data.auth_required) {
        // site is behind a login — prompt for credentials instead of a false report
        setAuthNotice(data.notice)
        setShowAuth(true)
        setView('idle')
        return
      }
      setResults(data)
      setView('results')
      const c = scoreFromResult(data)
      const s = data.scan || {}
      saveScan(token, {
        url: data.url || check.url,
        domain: (data.url || check.url).replace(/https?:\/\//, '').split('/')[0],
        score: c.score,
        grade: c.grade,
        consent_platform: s.consent_platform || null,
        tracker_count: (data.violations || []).length,
        undeclared_count: (data.undeclared || []).length,
        fine_range: (data.exposure || {}).estimated_range_medium || null,
        payload: data,
      }).then(refresh).catch(() => {})
    } catch (err) {
      setInputError(err.message)
      setView('idle')
    }
  }

  const openScan = async (id) => {
    try {
      const d = await getScan(token, id)
      setResults(d.payload)
      setScanUrl(d.url)
      setView('results')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch { /* ignore */ }
  }

  const removeScan = async (id, e) => {
    e.stopPropagation()
    try { await deleteScan(token, id); refresh() } catch { /* ignore */ }
  }

  const signOut = () => { logout(); navigate('/') }
  const backToIdle = () => { setView('idle'); refresh() }

  // KPIs
  const total = scans.length
  const failing = scans.filter((s) => s.undeclared_count > 0).length
  const avgScore = total ? Math.round(scans.reduce((a, s) => a + s.score, 0) / total) : 0
  const worst = scans.reduce((w, s) => (!w || s.undeclared_count > w.undeclared_count ? s : w), null)

  return (
    <div className="dash-page">
      <div className="dash-nav">
        <div className="nav-logo" onClick={() => setView('idle')} style={{ cursor: 'pointer' }}>
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          ConsentGuard
        </div>
        <div className="center">Dashboard</div>
        <div className="right">
          <span className="who">{user?.name || user?.email}</span>
          <button className="btn-outline" style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }} onClick={signOut}>Sign out</button>
        </div>
      </div>

      {view === 'scanning' && <Scanning url={scanUrl} error={error} />}
      {view === 'results' && results && (
        <>
          <div style={{ maxWidth: 940, margin: '0 auto', padding: '1.5rem 1.5rem 0' }}>
            <button className="reset-btn" onClick={backToIdle} style={{ padding: '0.5rem 1.1rem', fontSize: '0.82rem' }}>← Back to dashboard</button>
          </div>
          <Results data={results} onReset={backToIdle} />
        </>
      )}

      {view === 'idle' && (
        <div className="dash-wrap">
          <div className="dash-tabs">
            <button className={tab === 'scan' ? 'active' : ''} onClick={() => setTab('scan')}>Scan</button>
            <button className={tab === 'watch' ? 'active' : ''} onClick={() => setTab('watch')}>Watchtower</button>
          </div>

          {tab === 'watch' && <Watchtower token={token} />}

          {tab === 'scan' && (
          <>
          <div className="dash-head">
            <h1>Welcome, {firstName}.</h1>
            <p>Run a compliance scan on any domain.</p>
          </div>

          <form className={`dash-scan${inputError ? ' invalid' : ''}`} onSubmit={runScan}>
            <span className="prefix">https://</span>
            <input
              placeholder="bbc.com"
              value={url}
              onChange={(e) => { setUrl(e.target.value); if (inputError) setInputError(null); if (authNotice) setAuthNotice(null) }}
            />
            <button className="btn-dark" type="submit">▶ Run scan</button>
          </form>
          {inputError
            ? <div className="scan-error">{inputError}</div>
            : <div className="dash-scan-hint"><span className="live-dot" /> Live scanner · 6,326 tracker domains · ~30s per scan</div>}

          {authNotice && (
            <div className="auth-required-note">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <span>{authNotice}</span>
            </div>
          )}

          <button type="button" className="auth-toggle" onClick={() => setShowAuth((v) => !v)}>
            <span className="auth-caret">{showAuth ? '▾' : '▸'}</span> Behind a login? Scan a private or staging site
          </button>
          {showAuth && (
            <div className="auth-fields">
              <input placeholder="Username" autoComplete="off" value={authUser} onChange={(e) => setAuthUser(e.target.value)} />
              <input type="password" placeholder="Password" autoComplete="new-password" value={authPass} onChange={(e) => setAuthPass(e.target.value)} />
              <p className="auth-fields-note">HTTP Basic auth. Used for this scan only — never stored.</p>
            </div>
          )}

          {total > 0 && (
            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-val">{total}</div>
                <div className="kpi-label">Scans run</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-val" style={{ color: failing ? 'var(--rose)' : 'var(--emerald)' }}>{failing}</div>
                <div className="kpi-label">Sites failing</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-val" style={{ color: gradeColor(avgScore >= 90 ? 'A' : avgScore >= 80 ? 'B' : avgScore >= 65 ? 'C' : avgScore >= 50 ? 'D' : 'F') }}>{avgScore}</div>
                <div className="kpi-label">Avg. score</div>
              </div>
            </div>
          )}

          <h2 className="dash-h2">Scan history</h2>
          {total === 0 ? (
            <div className="dash-empty">No scans yet. Run your first one above.</div>
          ) : (
            <div className="history">
              <table>
                <thead>
                  <tr>
                    <th>Domain</th><th>Score</th><th>Undeclared</th>
                    <th>Fine exposure</th><th>Scanned</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((s) => (
                    <tr key={s.id} onClick={() => openScan(s.id)} style={{ cursor: 'pointer' }}>
                      <td className="td-domain">{s.domain}</td>
                      <td>
                        <span className="grade-badge" style={{ color: gradeColor(s.grade), borderColor: gradeColor(s.grade) }}>
                          {s.grade} · {s.score}
                        </span>
                      </td>
                      <td style={{ color: s.undeclared_count ? 'var(--rose)' : 'var(--emerald)', fontWeight: 600 }}>{s.undeclared_count}</td>
                      <td style={{ fontFamily: 'var(--mono)', fontSize: '0.78rem' }}>{s.fine_range || '—'}</td>
                      <td style={{ fontFamily: 'var(--mono)', fontSize: '0.76rem', color: 'var(--text3)' }}>{fmtDate(s.created_at)}</td>
                      <td>
                        <button className="del-btn" onClick={(e) => removeScan(s.id, e)} title="Delete scan" aria-label="Delete scan">
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" /></svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          </>
          )}
        </div>
      )}
    </div>
  )
}
