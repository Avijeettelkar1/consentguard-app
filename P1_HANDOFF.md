# P1 HANDOFF — Behavioral Tracker Detection (Identity Syncing)

> **You are the agent building Pillar 1.** This file is self-contained — you do not need any
> other file to do your job. Build the module, wire it in, test it, done.
> Cross-pillar view lives in `PILLARS.md` (optional reading).

---

## 0. Mission (one line)
Detect trackers **by behavior, not a blocklist**: find the *same user identifier* being shared
across *unrelated companies* after the user clicked "Reject All", and expose it as an identity graph.

**Why it matters:** this is the strongest *technical* pillar — a real algorithm over real data, no
LLM, no API key. It catches trackers that are on **no** list. Demo money-shot: *"the same ID for me
just got sent to Google, Facebook AND a data broker after I clicked Reject."*

---

## 1. Project context (30 seconds)
ConsentGuard / "Reject-All Radar" is a GDPR scanner. A headless browser (Playwright) opens a site,
clicks **Reject All**, and records every network request that fires **anyway**. Backend = FastAPI in
`backend/`. Your work is a new backend module + a one-line wire-in. No frontend required from you
(the frontend team consumes your JSON).

## 2. How to run & verify (do this first, confirm it works)
```bash
cd backend
python -m pip install -r requirements.txt          # first time
MOCK=true python -m uvicorn main:app --port 8000    # keyless, instant — for smoke testing wiring
# run the test suite:
MOCK=true python -m pytest -q
```
Your module is pure Python and testable **without** a browser or keys — you'll write unit tests that
feed synthetic request records. Do not rely on live scans for your unit tests.

---

## 3. GROUND TRUTH — the data you read (this is exact, verified against `scanner.py`)
`scanner.run_scan(url, auth)` returns a dict. **You read these fields:**

```python
scan_data["reject"]["post_consent_request_records"]   # ← PRIMARY. after-Reject traffic
scan_data["accept"]["post_consent_request_records"]   # for blocked-by-reject comparison
# each record:
{ "url": "https://host/path?a=b", "method": "GET|POST",
  "resource_type": "script|image|xhr|fetch|...", "post_data": "<= 2000 chars, may be ''" }

scan_data["reject"]["cookies"]     # [{name,domain,path,expires,httpOnly,secure,sameSite}]  ⚠️ NO value
scan_data["page_html_for_fallback"]  # first 8000 chars of HTML (use to filter site-wide constants)
scan_data["scanner"]  # "playwright" | "daytona" | "http"
```

**Hard facts that shape your design:**
- ✅ You HAVE full request URLs (with query strings) and POST bodies → extract identifiers from these.
- ❌ Cookie **values are stripped** → you CANNOT correlate cookie values. Correlate ID values found in
  request URLs/bodies instead. Do not try to read `cookie["value"]` — it doesn't exist.
- ⚠️ The **HTTP fallback** scanner (`scanner == "http"`) produces **no** `*_records` → your function
  must detect this and return `{"available": false, ...}` so callers keep the blocklist result.
- ℹ️ `tag_audit.py` already detects *known* payloads (GA4, Meta pixel, etc.). Do NOT duplicate that.
  You are **identifier-driven** — that's the whole novelty.

---

## 4. Build it — `backend/behavioral.py`

### Public API
```python
def detect_id_syncing(scan_data: dict, site_url: str) -> dict:
    """Detect cross-domain identity syncing after Reject. See return shape in §6."""
```

### Algorithm (implement in this order)

**Step 1 — `registrable_domain(host: str) -> str`.** Measure sharing at the *organization* level.
- Try `import tldextract` (add to requirements; see §8). `tldextract.extract(host).registered_domain`.
- Fallback if tldextract missing: lowercase, strip `www.`/port, handle a small multi-part suffix set
  `{co.uk, org.uk, ac.uk, com.au, co.jp, com.br, co.in, com.tr, co.za}` → keep 3 labels for those,
  else last 2 labels.

**Step 2 — token extraction per record.** For each request record collect candidate `(value,
source_domain, location, param_name)`:
- `source_domain = registrable_domain(urlparse(url).hostname)`.
- Query params: `parse_qs(urlparse(url).query)` → every value (location="query", param=key).
- Path segments: split path on `/ ; ,` → segments (location="path", param=None).
- POST body: try `parse_qs(body)`; then `json.loads(body)` and recurse over string leaves; else regex
  long tokens `[A-Za-z0-9_\-]{8,}` (location="body").
- Decode each value up to **2 levels** of `urllib.parse.unquote`. Also attempt base64url decode; if it
  yields printable JSON/keyvals, recurse into those too (pixels pack params in base64).

**Step 3 — identifier filter** (precision-critical — see helpers below). Keep a token only if
`looks_like_identifier(value)` AND `not is_noise(value, site_domain, page_html)`.

```python
def shannon_entropy(s: str) -> float: ...  # bits/char over the string's own alphabet

def looks_like_identifier(v: str) -> tuple[bool, str]:
    # returns (is_id, kind). kind ∈ {"uuid","hex32","base64","opaque","hashed_pii"}
    if not (8 <= len(v) <= 128): return (False, "")
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", v):
        return (True, "uuid")
    if re.fullmatch(r"[0-9a-fA-F]+", v) and len(v) in (16,24,32,40,48,64):
        return (True, "hashed_pii" if len(v) in (32,40,64) else "hex32")
    if re.fullmatch(r"[A-Za-z0-9_\-]{16,}", v) and shannon_entropy(v) >= 3.0:
        return (True, "base64" if re.search(r"[_\-]", v) or not v.isalnum() else "opaque")
    if shannon_entropy(v) >= 3.5 and len(v) >= 10:
        return (True, "opaque")
    return (False, "")

def is_noise(v, site_domain, page_html) -> bool:
    if re.fullmatch(r"\d{10}", v) or re.fullmatch(r"\d{13}", v): return True   # epoch / ms timestamp
    if re.fullmatch(r"\d{3,4}[xX]\d{3,4}", v): return True                      # screen size
    if re.fullmatch(r"v?\d+(\.\d+)+", v): return True                           # version string
    if v.lower() in {"true","false","null","undefined","none","en","de","en-us","de-de","0","1"}: return True
    if v.lower() == site_domain or "." in v and v.lower().endswith((".com",".net",".de",".org")): return True
    if v.startswith(("http://","https://")): return True
    if page_html and v in page_html: return True   # site-wide constant (GTM id, publisher id, asset hash)
    return False
```
**MANDATORY exclusion — consent strings.** If `param_name` (lowercased) ∈
`{gdpr, gdpr_consent, euconsent, euconsent-v2, us_privacy, gpp, gpp_sid, consent, cmpid}` → **drop the
token**. Consent strings are shared across vendors *by design*; not excluding them is the #1
false-positive source. (Pillar 3's agent uses these separately — leave them alone.)

**Step 4 — sharing map.** `token -> {source_domain, ...}` plus `token -> [evidence dicts]`.

**Step 5 — select sync identifiers.** A token qualifies when:
- it reached **≥ 2 distinct registrable domains**, AND
- **≥ 2 of those are third-party** (≠ `registrable_domain(site_url)`).
- First-party-only (only the site's own subdomains) → drop.
- Severity: `third_party_domain_count >= 3` OR `kind == "hashed_pii"` → `"high"`; `== 2` → `"medium"`.

**Step 6 — after-reject weighting.** Compute the same on the **accept** branch. `after_reject=True`
if the identifier appears in the reject branch (the headline — sharing that survives "no").
`blocked_by_reject` = present under accept, absent under reject.

**Step 7 — identity graph.** Nodes = registrable domains, tag `first_party|third_party`, enrich with
`company`/`category` via `from tracker_db import is_tracker` (`is_tracker(domain)` → dict or None).
Edge `(a,b)` weight = number of shared identifiers. `worst_cluster_size` = max third-party fan-out of
any single identifier.

---

## 5. Privacy rule (non-negotiable)
**Never emit a raw identifier value.** In output, mask to `first4…last4` and include a
`sha256` hex of the value as a stable non-reversible id. Same for `url_preview` — truncate and mask
the token inside it.

## 6. Return shape (exact — the frontend depends on this)
```python
{
  "available": true,                     # false when records missing (HTTP fallback)
  "sync_identifiers": [
    {
      "token_preview": "3f9a…c1d7",
      "token_hash": "sha256:9b74c9…",
      "kind": "uuid|hex32|base64|opaque|hashed_pii",
      "entropy": 3.94,
      "domains": ["doubleclick.net","facebook.com","criteo.com"],
      "third_party_domain_count": 3,
      "after_reject": true,
      "severity": "high",
      "evidence": [
        {"domain":"doubleclick.net","param":"uid","location":"query","url_preview":"https://…/px?uid=3f9a…"}
      ]
    }
  ],
  "identity_graph": {
    "nodes": [{"id":"doubleclick.net","type":"third_party","company":"Google","category":"advertising"}],
    "edges": [{"source":"doubleclick.net","target":"facebook.com","shared_ids":2}]
  },
  "worst_cluster_size": 3,
  "hashed_pii_suspected": true,
  "summary": "1 identifier was shared with 3 unrelated ad companies after Reject All."
}
```

## 7. Edge cases — handle every one
| Case | Required handling |
|---|---|
| `scanner == "http"` or records missing/empty | return `{"available": false}` + empty lists; never throw |
| request with empty query and empty body | skip |
| shared timestamp / cache-buster | dropped by epoch test |
| TCF consent string on many vendors | dropped by consent-param exclusion (Step 3) |
| screen size / locale / version shared | dropped by noise patterns |
| public API key / font hash / publisher id | dropped by "value appears in page HTML" |
| hashed email (md5/sha1/sha256, 32/40/64 hex) | **keep + flag** `hashed_pii` (strongest signal) |
| double-/base64-encoded params | decode ≤2 levels + base64 attempt before filtering |
| non-ASCII / malformed value | wrap decode/entropy in try/except; skip on error |
| id shorter than 8 chars | skip (collision-prone) |
| huge page (thousands of requests) | cap: 50 tokens/request, 5000 tokens total, 1500 records; dedupe |
| our own output leaking PII | mask + hash only; never raw values |

## 8. Requirements
Add to `backend/requirements.txt` (append; your two teammates also append here — keep to one line):
```
tldextract
```
(Your fallback works without it, but include it — cleaner registrable-domain logic.)

## 9. Integration (exact — one line)
In `backend/agent.py`, function `scan_one(url, auth=None)`, after `scan_data = run_scan(...)` and
after the card dict is built, add:
```python
from behavioral import detect_id_syncing        # top-of-file import is fine too
card["identity_sync"] = detect_id_syncing(scan_data, url)
card["behavioral_flag"] = card["identity_sync"].get("worst_cluster_size", 0) >= 2
```
Also mirror it in `backend/main.py` `scan_endpoint` (the single-scan response dict): add
`"identity_sync": detect_id_syncing(scan_data, url)` to the returned JSON.
**Do not** change the scanner or any other pillar's code.

## 10. Coordination (three agents, shared files)
- **Shared touch-point:** `agent.scan_one()` — all three of you add ONE `card[...] = ...` line. Add
  yours; leave the others' lines alone. If they aren't there yet, just add yours.
- **`requirements.txt`** — all three append. Add only `tldextract`.
- You do **not** touch `scanner.py`, `analyzer.py`, or `tcf.py`. Pillar 1 is self-contained.

## 11. Definition of done (acceptance criteria)
1. `backend/behavioral.py` exists; `python -m py_compile backend/behavioral.py` passes.
2. Unit tests in `backend/test_behavioral.py` pass:
   - synthetic: token `T` on 3 domains after reject → one `high` sync identifier w/ those 3 domains;
   - shared 10-digit epoch on 3 domains → **zero** identifiers;
   - `gdpr_consent=<value>` on 3 domains → **zero** identifiers (excluded);
   - first-party-only sharing → zero;
   - `scanner:"http"` / empty records → `{"available": false}`.
3. Wired into `agent.scan_one` and `main.scan_endpoint`; `MOCK=true pytest -q` still green.
4. No raw identifier value appears anywhere in the output.

## 12. What the demo shows
A live force-graph where one identifier node connects Google → Meta → a data broker after Reject, with
the caption *"caught by behavior — no blocklist told us this."* Output feeds the frontend's graph via
`identity_graph.nodes/edges`.
