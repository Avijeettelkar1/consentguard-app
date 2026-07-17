export const API_URL =
  window.location.hostname === 'localhost' || window.location.protocol === 'file:'
    ? 'http://localhost:8000'
    : 'https://consentguard-backend-production.up.railway.app'

async function parseError(res) {
  try {
    const data = await res.json()
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg
  } catch {
    /* fall through */
  }
  return `Request failed (${res.status})`
}

export async function fetchScan(url, auth) {
  // auth (optional): { username, password } and/or { header_name, header_value }
  const res = await fetch(`${API_URL}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, ...(auth || {}) }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function fetchHealth() {
  const res = await fetch(`${API_URL}/health`)
  return res.json()
}

// ─────────────────────────── auth ───────────────────────────
export async function apiSignup({ email, password, name }) {
  const res = await fetch(`${API_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function apiLogin({ email, password }) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function apiMe(token) {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

// ─────────────────────── scan history ───────────────────────
const authHeaders = (token) => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${token}` })

export async function saveScan(token, body) {
  const res = await fetch(`${API_URL}/scans`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify(body) })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function listScans(token) {
  const res = await fetch(`${API_URL}/scans`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function getScan(token, id) {
  const res = await fetch(`${API_URL}/scans/${id}`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function deleteScan(token, id) {
  const res = await fetch(`${API_URL}/scans/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

// ─────────────────────── watchtower ───────────────────────
export async function listWatches(token) {
  const res = await fetch(`${API_URL}/watch`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function addWatch(token, url) {
  const res = await fetch(`${API_URL}/watch`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify({ url }) })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function scanWatch(token, id) {
  const res = await fetch(`${API_URL}/watch/${id}/scan`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function deleteWatch(token, id) {
  const res = await fetch(`${API_URL}/watch/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function listAlerts(token) {
  const res = await fetch(`${API_URL}/watch/alerts`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

// ─────────────────────── notifications ───────────────────────
export async function getWebhook(token) {
  const res = await fetch(`${API_URL}/settings/webhook`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function saveWebhook(token, url, enabled = true) {
  const res = await fetch(`${API_URL}/settings/webhook`, { method: 'PUT', headers: authHeaders(token), body: JSON.stringify({ url, enabled }) })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function testWebhook(token) {
  const res = await fetch(`${API_URL}/settings/webhook/test`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
