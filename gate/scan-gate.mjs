#!/usr/bin/env node
/*
 * ConsentGuard compliance gate.
 * Scans a URL and exits non-zero if undeclared trackers fire after "Reject All",
 * so a CI pipeline can block a release before the violation reaches production.
 *
 * Config via env vars:
 *   URL            (required)  page to scan, e.g. your staging deploy
 *   API_URL        (optional)  ConsentGuard API base   [default http://localhost:8000]
 *   USERNAME/PASSWORD          HTTP Basic auth for a protected/staging site
 *   HEADER_NAME/HEADER_VALUE   custom header (e.g. a staging bypass token)
 *   MAX_UNDECLARED (optional)  allowed undeclared trackers before failing [default 0]
 *
 * Exit codes: 0 = compliant · 1 = violations found · 2 = could not run the check
 */
const API = (process.env.API_URL || 'http://localhost:8000').replace(/\/+$/, '')
const url = (process.env.URL || '').trim()
const maxUndeclared = parseInt(process.env.MAX_UNDECLARED || '0', 10)

const err = (m) => console.error(`::error::${m}`)
const notice = (m) => console.log(`::notice::${m}`)

if (!url) { err('URL is required.'); process.exit(2) }

const body = { url }
if (process.env.USERNAME) { body.username = process.env.USERNAME; body.password = process.env.PASSWORD || '' }
if (process.env.HEADER_NAME && process.env.HEADER_VALUE) { body.header_name = process.env.HEADER_NAME; body.header_value = process.env.HEADER_VALUE }

console.log(`\n🛡️  ConsentGuard compliance gate`)
console.log(`   scanning: ${url}`)
console.log(`   via:      ${API}\n`)

let res, data
try {
  res = await fetch(`${API}/scan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  data = await res.json()
} catch (e) {
  err(`Could not reach the ConsentGuard API at ${API} — ${e.message}`)
  process.exit(2)
}

if (data && data.auth_required) { err(data.notice || 'The site is behind a login — provide credentials.'); process.exit(2) }
if (!res.ok) { err(`Scan failed: ${(data && data.detail) || res.status}`); process.exit(2) }

const undeclared = data.undeclared || []
const n = undeclared.length

if (n > maxUndeclared) {
  err(`Compliance gate FAILED — ${n} undeclared tracker${n === 1 ? '' : 's'} fired after "Reject All":`)
  for (const t of undeclared) console.error(`     • ${t.domain}${t.company ? '  (' + t.company + ')' : ''}`)
  console.error(`\n   These are GDPR violations. Fix them before shipping to production.`)
  const fine = (data.exposure || {}).estimated_range_medium
  if (fine) console.error(`   Estimated exposure: ${fine}\n`)
  process.exit(1)
}

notice(`Compliance gate PASSED — no undeclared trackers on ${data.url || url}. Safe to ship. ✅`)
process.exit(0)
