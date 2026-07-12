import { useState } from 'react'
import ScoreGauge from './ScoreGauge'
import { scoreFromResult } from '../lib/score'

export default function Results({ data, onReset }) {
  const [activeTab, setActiveTab] = useState('policy')
  const [copied, setCopied] = useState(false)
  const compliance = scoreFromResult(data)

  const scan = data.scan || {}
  const undeclared = data.undeclared || []
  const violations = data.violations || []
  const fixes = data.fixes || {}
  const exposure = data.exposure || {}

  const hasViolations = undeclared.length > 0

  const copyComplaint = () => {
    navigator.clipboard.writeText(data.complaint || '').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <section className="results-section">
      <div className="results-inner">

        {/* Verdict — gauge + headline + key facts, all in one */}
        <div className={`verdict-banner ${hasViolations ? 'fail' : 'pass'}`}>
          <div className="verdict-left">
            <h2>{hasViolations ? 'Cookie Consent Violated' : 'Cookie Consent Compliant'}</h2>
            <p>
              {hasViolations
                ? `${undeclared.length} undeclared tracker${undeclared.length > 1 ? 's' : ''} fired after “Reject All” on ${data.url}`
                : `No undeclared trackers detected after “Reject All” on ${data.url}`}
            </p>
            <div className="verdict-facts">
              <span><b>{scan.consent_platform || 'No CMP'}</b> platform</span>
              <span className={scan.clicked_reject ? 'ok' : 'bad'}><b>{scan.clicked_reject ? 'Yes' : 'No'}</b> reject clicked</span>
              <span><b>{scan.after_count ?? '—'}</b> requests after</span>
              <span className={undeclared.length ? 'bad' : 'ok'}><b>{undeclared.length}</b> undeclared</span>
            </div>
          </div>
          <ScoreGauge score={compliance.score} grade={compliance.grade} label={compliance.label} />
        </div>

        {/* Fine exposure — the impact number, compact */}
        <div className="fine-strip">
          <div className="fine-strip-lead">
            <span className="fine-strip-label">GDPR fine exposure</span>
            <span className="fine-strip-val">{exposure.estimated_range_medium || '—'}</span>
            <span className="fine-strip-sub">medium company · up to {exposure.max_fine_percent || '4% of turnover'} under Art. 83</span>
          </div>
          <div className="fine-strip-ranges">
            <div><i>Small</i>{exposure.estimated_range_small || '—'}</div>
            <div><i>Large</i>{exposure.estimated_range_large || '—'}</div>
          </div>
        </div>

        {/* Violations table — the evidence */}
        <div className="block">
          <div className="block-header">
            <h3>
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              Trackers firing after reject
            </h3>
            <span className={`chip ${violations.length ? 'red' : 'green'}`}>{violations.length} found</span>
          </div>
          <div style={{ padding: '0 1.5rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Company</th>
                  <th>Category</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {violations.length === 0 && (
                  <tr><td colSpan={4} style={{ color: 'var(--text3)', padding: '1rem 0' }}>No tracker violations detected.</td></tr>
                )}
                {violations.map((v, i) => (
                  <tr key={i}>
                    <td><span className="td-domain">{v.domain}</span></td>
                    <td style={{ color: 'var(--text2)', fontSize: '0.8rem' }}>{v.company || '—'}</td>
                    <td><span className="td-cat">{v.category}</span></td>
                    <td>
                      {v.needs_review
                        ? <span className="chip yellow">Review</span>
                        : v.declared
                          ? <span className="chip green">Declared</span>
                          : <span className="chip red">Undeclared</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Deliverables — collapsed by default so the page stays short */}
        <details className="block acc">
          <summary className="block-header">
            <h3>
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
              How to fix it
            </h3>
            <span className="acc-chev" aria-hidden>▾</span>
          </summary>
          <div className="tabs">
            <button className={`tab-btn ${activeTab === 'policy' ? 'active' : ''}`} onClick={() => setActiveTab('policy')}>Policy update</button>
            <button className={`tab-btn ${activeTab === 'banner' ? 'active' : ''}`} onClick={() => setActiveTab('banner')}>Banner config</button>
          </div>
          <div className={`tab-panel ${activeTab === 'policy' ? 'active' : ''}`}>
            <p className="acc-note">Add this to your cookie policy to disclose the undeclared trackers:</p>
            <div className="code-block" dangerouslySetInnerHTML={{ __html: fixes.policy_fix || '—' }} />
          </div>
          <div className={`tab-panel ${activeTab === 'banner' ? 'active' : ''}`}>
            <p className="acc-note">Steps to fix your consent platform configuration:</p>
            <div className="code-block">{fixes.banner_fix || '—'}</div>
          </div>
        </details>

        <details className="block acc">
          <summary className="block-header">
            <h3>
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
              </svg>
              DPA complaint letter
            </h3>
            <span className="acc-chev" aria-hidden>▾</span>
          </summary>
          <div className="block-body">
            <div className="acc-note-row">
              <p className="acc-note" style={{ margin: 0 }}>Ready-to-file complaint to your national Data Protection Authority.</p>
              <button className="copy-btn" onClick={copyComplaint}>{copied ? 'Copied ✓' : 'Copy letter'}</button>
            </div>
            <div className="complaint-box">{data.complaint || '—'}</div>
          </div>
        </details>

        <div style={{ textAlign: 'center', padding: '2.5rem 0 1rem' }}>
          <button className="reset-btn" onClick={onReset}>← Scan another site</button>
        </div>

      </div>
    </section>
  )
}
