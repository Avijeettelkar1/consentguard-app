import { useState, useEffect, useCallback, useRef } from 'react'
import { listWatches, addWatch, scanWatch, deleteWatch, listAlerts, getWebhook, saveWebhook, testWebhook } from '../api'
import { gradeColor } from '../lib/score'
import { normalizeUrl } from '../lib/validateDomain'

function relTime(iso) {
  if (!iso) return 'never'
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function Sparkline({ trend = [], color }) {
  if (!trend.length) return <div className="spark empty">—</div>
  const w = 132, h = 34, pad = 3
  const max = 100, min = 0
  const pts = trend.length === 1 ? [trend[0], trend[0]] : trend
  const step = (w - pad * 2) / (pts.length - 1)
  const y = (v) => h - pad - ((v - min) / (max - min)) * (h - pad * 2)
  const d = pts.map((v, i) => `${i === 0 ? 'M' : 'L'} ${pad + i * step} ${y(v)}`).join(' ')
  const area = `${d} L ${pad + (pts.length - 1) * step} ${h} L ${pad} ${h} Z`
  return (
    <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <path d={area} fill={color} opacity="0.1" />
      <path d={d} fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pad + (pts.length - 1) * step} cy={y(pts[pts.length - 1])} r="2.5" fill={color} />
    </svg>
  )
}

const STATUS = {
  ok: { dot: 'var(--emerald)', text: 'Compliant' },
  alert: { dot: 'var(--rose)', text: 'Violations' },
  error: { dot: 'var(--yellow)', text: 'Scan error' },
  pending: { dot: 'var(--text4)', text: 'First scan running…' },
}

export default function Watchtower({ token }) {
  const [watches, setWatches] = useState([])
  const [alerts, setAlerts] = useState([])
  const [url, setUrl] = useState('')
  const [err, setErr] = useState(null)
  const [adding, setAdding] = useState(false)
  const [busy, setBusy] = useState({})
  const [loaded, setLoaded] = useState(false)
  const timer = useRef()

  // notifications
  const [hook, setHook] = useState('')
  const [hookSaved, setHookSaved] = useState('')
  const [hookMsg, setHookMsg] = useState(null)
  const [hookBusy, setHookBusy] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    try {
      const [w, a] = await Promise.all([listWatches(token), listAlerts(token)])
      setWatches(w.watches || [])
      setAlerts(a.alerts || [])
    } catch { /* ignore */ }
    finally { setLoaded(true) }
  }, [token])

  useEffect(() => {
    load()
    timer.current = setInterval(load, 9000) // live board
    return () => clearInterval(timer.current)
  }, [load])

  useEffect(() => {
    if (!token) return
    getWebhook(token).then((d) => { setHook(d.url || ''); setHookSaved(d.url || '') }).catch(() => {})
  }, [token])

  const saveHook = async () => {
    setHookBusy(true); setHookMsg(null)
    try {
      await saveWebhook(token, hook.trim(), true)
      setHookSaved(hook.trim())
      setHookMsg({ ok: true, text: 'Saved. Regressions will now post here.' })
    } catch (e) { setHookMsg({ ok: false, text: e.message }) }
    finally { setHookBusy(false) }
  }

  const testHook = async () => {
    setHookBusy(true); setHookMsg(null)
    try {
      if (hook.trim() !== hookSaved) await saveWebhook(token, hook.trim(), true)
      await testWebhook(token)
      setHookSaved(hook.trim())
      setHookMsg({ ok: true, text: 'Test alert sent — check your Slack/channel.' })
    } catch (e) { setHookMsg({ ok: false, text: e.message }) }
    finally { setHookBusy(false) }
  }

  const add = async (e) => {
    e.preventDefault()
    const check = normalizeUrl(url)
    if (!check.ok) { setErr(check.error); return }
    setErr(null); setAdding(true)
    try { await addWatch(token, check.url); setUrl(''); await load() }
    catch (e2) { setErr(e2.message) }
    finally { setAdding(false) }
  }

  const doScan = async (id) => {
    setBusy((b) => ({ ...b, [id]: true }))
    try { await scanWatch(token, id) } catch { /* ignore */ }
    setTimeout(async () => { await load(); setBusy((b) => ({ ...b, [id]: false })) }, 2500)
  }

  const remove = async (id) => {
    try { await deleteWatch(token, id); await load() } catch { /* ignore */ }
  }

  const pendingAlerts = alerts.filter((a) => !a.read)

  return (
    <div className="watch">
      <div className="watch-head">
        <div>
          <h1>Watchtower</h1>
          <p>Compliance drifts every deploy. We re-scan your domains on a schedule and alert you the moment one slips.</p>
        </div>
      </div>

      <form className={`dash-scan${err ? ' invalid' : ''}`} onSubmit={add}>
        <span className="prefix">https://</span>
        <input placeholder="add a domain to monitor…" value={url} onChange={(e) => { setUrl(e.target.value); if (err) setErr(null) }} />
        <button className="btn-dark" type="submit" disabled={adding}>{adding ? 'Adding…' : '+ Monitor'}</button>
      </form>
      {err && <div className="scan-error">{err}</div>}

      <details className="notify" open={!hookSaved && false}>
        <summary>
          <span className="notify-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" /></svg>
            Alert notifications
            {hookSaved && <span className="notify-on">● on</span>}
          </span>
          <span className="acc-chev" aria-hidden>▾</span>
        </summary>
        <div className="notify-body">
          <p className="notify-note">Send Watchtower regressions to Slack, Teams, or any webhook — the moment a site slips.</p>
          <div className="notify-row">
            <input
              className="notify-input"
              placeholder="https://hooks.slack.com/services/…"
              value={hook}
              onChange={(e) => { setHook(e.target.value); if (hookMsg) setHookMsg(null) }}
            />
            <button className="btn-dark" onClick={saveHook} disabled={hookBusy}>Save</button>
            <button className="btn-outline" onClick={testHook} disabled={hookBusy || !hook.trim()}>Send test</button>
          </div>
          {hookMsg && <div className={`notify-msg ${hookMsg.ok ? 'ok' : 'bad'}`}>{hookMsg.text}</div>}
        </div>
      </details>

      {pendingAlerts.length > 0 && (
        <div className="alert-feed">
          {pendingAlerts.slice(0, 5).map((a) => (
            <div className={`alert-row ${a.type}`} key={a.id}>
              <span className="alert-ic">{a.type === 'regression' ? '▼' : a.type === 'improved' ? '▲' : '⚠'}</span>
              <span className="alert-domain">{a.domain}</span>
              <span className="alert-msg">{a.message}</span>
              <span className="alert-time">{relTime(a.created_at)}</span>
            </div>
          ))}
        </div>
      )}

      {loaded && watches.length === 0 && (
        <div className="dash-empty" style={{ marginTop: '1.75rem' }}>
          No domains monitored yet. Add one above — we’ll baseline it, then watch it around the clock.
        </div>
      )}

      {watches.length > 0 && (
        <div className="watch-grid">
          {watches.map((w) => {
            const st = STATUS[w.status] || STATUS.pending
            const color = w.last_grade ? gradeColor(w.last_grade) : 'var(--text4)'
            const delta = w.trend.length > 1 ? w.trend[w.trend.length - 1] - w.trend[w.trend.length - 2] : 0
            const isBusy = busy[w.id] || w.status === 'pending'
            return (
              <div className="watch-card" key={w.id}>
                <div className="watch-card-top">
                  <div className="watch-dom">
                    <span className="watch-dot" style={{ background: st.dot }} />
                    {w.domain}
                  </div>
                  <button className="del-btn" onClick={() => remove(w.id)} aria-label="Stop monitoring" title="Stop monitoring">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" /></svg>
                  </button>
                </div>

                <div className="watch-mid">
                  {w.last_grade ? (
                    <div className="watch-score">
                      <span className="watch-grade" style={{ color }}>{w.last_grade}</span>
                      <span className="watch-scoreval">{w.last_score}<i>/100</i></span>
                      {delta !== 0 && (
                        <span className="watch-delta" style={{ color: delta > 0 ? 'var(--emerald)' : 'var(--rose)' }}>
                          {delta > 0 ? '▲' : '▼'}{Math.abs(delta)}
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="watch-score pending">{isBusy ? 'Scanning…' : 'Queued…'}</div>
                  )}
                  <Sparkline trend={w.trend} color={color} />
                </div>

                <div className="watch-status" style={{ color: st.dot }}>
                  {w.status === 'ok' ? '✓ Compliant'
                    : w.status === 'alert' ? `${w.undeclared_count} undeclared tracker${w.undeclared_count === 1 ? '' : 's'}`
                    : w.status === 'error' ? 'Scan error'
                    : isBusy ? 'Running first scan…' : 'Queued'}
                </div>

                <div className="watch-foot">
                  <span>Checked {relTime(w.last_checked_at)}</span>
                  <button className="watch-rescan" onClick={() => doScan(w.id)} disabled={isBusy}>
                    {isBusy ? 'Scanning…' : '↻ Scan now'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
