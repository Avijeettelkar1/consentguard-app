// Accepts a user-typed website and returns { ok, url } or { ok:false, error }.
// Rejects non-domains like "sssss", "hello world", "http://", bare words, etc.
const HOST_RE = /^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/i

// Obvious non-real TLDs people fat-finger; keep light, not a full allowlist.
const BAD_HOSTS = new Set(['localhost', 'example.com', 'test.com'])

export function normalizeUrl(input) {
  const raw = (input || '').trim()
  if (!raw) return { ok: false, error: 'Enter a website to scan.' }
  if (/\s/.test(raw)) return { ok: false, error: 'A domain can’t contain spaces. Try e.g. bbc.com.' }

  // strip protocol + path/query/fragment to isolate the host
  let rest = raw.replace(/^https?:\/\//i, '')
  const host = rest.split('/')[0].split('?')[0].split('#')[0].toLowerCase()

  if (!host.includes('.')) {
    return { ok: false, error: `“${raw}” isn’t a valid website. Include a domain ending, e.g. ${raw}.com` }
  }
  if (!HOST_RE.test(host)) {
    return { ok: false, error: `“${raw}” doesn’t look like a valid website. Try a domain like bbc.com.` }
  }
  if (host.length > 253) return { ok: false, error: 'That domain is too long to be valid.' }
  if (BAD_HOSTS.has(host)) {
    return { ok: false, error: 'Enter a real, public website (not localhost/example.com).' }
  }

  return { ok: true, url: 'https://' + rest }
}
