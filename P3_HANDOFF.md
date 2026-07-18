# P3 HANDOFF — TCF Consent-String Decoding + Protocol Mismatch

> **You are the agent building Pillar 3.** This file is self-contained — you do not need any
> other file. Cross-pillar view is in `PILLARS.md` (optional).
> ⚠️ This is the **highest-risk, highest-reward** pillar. Build the **fallback path first** (§4a):
> it needs no scanner change and proves value on its own. The authoritative path (§4b) is a bonus.

---

## 0. Mission (one line)
On sites using the IAB **TCF** consent protocol, decode the site's **own consent string** and prove it
**byte-for-byte contradicts** what actually fired: the string says "vendor X = no consent", yet a
request to vendor X loaded after Reject — carrying that very string.

**Why it matters:** protocol-level, undeniable proof + deep domain mastery most teams don't even know
exists. It's the demo mic-drop and the top of the evidence hierarchy (🔒 above behavior, semantics,
and blocklist).

---

## 1. Project context (30 seconds)
ConsentGuard / "Reject-All Radar" is a GDPR scanner. A headless browser clicks **Reject All** and
records requests that fire anyway. Big EU sites use IAB TCF consent-management platforms (Sourcepoint,
OneTrust, Didomi, Quantcast, Usercentrics). TCF encodes the user's choices in a base64 **TC string**.
You decode it and cross-check it against the traffic. Backend = FastAPI in `backend/`.

## 2. How to run & verify (do this first)
```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest -q                     # your unit tests (feed synthetic scan_data — no browser needed)
MOCK=true python -m uvicorn main:app --port 8000
```
Your unit tests feed **synthetic** `scan_data` (a decoded `tc_data` dict, or request URLs with a
`gdpr_consent` param). No live browser needed for tests.

---

## 3. GROUND TRUTH — the data you read
`scanner.run_scan(url)` → `scan_data`:
```python
scan_data["consent_platform"]  # "Sourcepoint"|"OneTrust"|"Didomi"|"Quantcast"|"Usercentrics"|... |None
scan_data["reject"]["post_consent_request_records"]  # [{url, method, resource_type, post_data}, ...]
scan_data["reject"]["tc_data"]   # ⚠️ ONLY exists after you do P0.3 (§4b). None/absent otherwise.
```
**Two ways to get the consent state — implement 3a first:**
- **3a. Fallback (no scanner change):** vendor requests often carry `gdpr=1&gdpr_consent=<TCstring>` in
  the URL. Pull `gdpr_consent` from `reject.post_consent_request_records` and decode it. Works today.
- **3b. Authoritative (needs P0.3):** read the already-decoded `tc_data` object from `__tcfapi`
  captured in-page. Better (gives purpose + vendor + legitimate-interest maps directly), but requires
  a scanner edit.

Cookie **values are stripped**, so you cannot read the `euconsent-v2` cookie value — use the request
`gdpr_consent` param (3a) or `tc_data` (3b).

---

## 4. Build it

### 4a. `backend/tcf.py` — decoder + analyzer (start here)
```python
def decode_tc_string(tc: str) -> dict:
    """base64url TC string -> {gdpr_applies, purposes:{1:False,...}, vendors:{755:False,...},
       purpose_li:{...}, vendor_li:{...}}. Returns {} on failure."""

def analyze_tcf(scan_data: dict) -> dict: ...   # see return shape in §6
```
Decoding: use the `iab-tcf` library (add to requirements). **Handle base64url padding** — TC strings
drop `=`; re-pad to `len % 4 == 0` before decode. Wrap decode in try/except → `{}` on any error.

**`analyze_tcf` algorithm:**
1. **Detect TCF.** `tcf_present` if ANY: `consent_platform ∈ {Sourcepoint, OneTrust, Didomi,
   Quantcast, Usercentrics, TrustArc, Cookiebot}`, OR `scan_data["reject"].get("tc_data")`, OR any
   reject request URL has a `gdpr_consent` param.
2. **Get consent-after-reject.**
   - If `tc_data` present (3b): read `purposeConsents`, `vendorConsents`, `purposeLegitimateInterests`,
     `vendorLegitimateInterests` directly.
   - Else (3a): extract the `gdpr_consent` value from reject requests (via `parse_qs`), pick the most
     common if several, `decode_tc_string(it)`.
   - Compliant reject state = **Purpose 1 (store/access info) = false** AND all `vendorConsents = false`.
3. **Map fired vendors → TCF vendor IDs.** Load the IAB **Global Vendor List** (GVL JSON) — fetch
   `https://vendor-list.consensu.org/v2/vendor-list.json`, cache to disk; ship a **curated fallback
   map** for the demo's key vendors so you never depend on the network:
   ```python
   CURATED = {"doubleclick.net":755, "googlesyndication.com":755, "google-analytics.com":755,
              "facebook.com":"meta", "connect.facebook.net":"meta", "criteo.com":91,
              "adnxs.com":32, "amazon-adsystem.com":793, "adsrvr.org":21, "bing.com":"microsoft"}
   ```
   For each after-reject request domain, resolve to a vendor (curated map first, then GVL name/domain
   heuristic).
4. **Prove the mismatch.** A **violation** = a request fired after reject to vendor `V`'s domain, where
   the site's own string encodes `vendorConsents[V] == false` AND `purposeConsents[1] == false`. The
   evidence is that exact request URL carrying `gdpr_consent`.
5. **Legitimate-interest nuance.** If `vendorConsents[V]==false` but `vendorLegitimateInterests[V]==true`
   → put it in a separate `legitimate_interest_abuse` bucket ("fired under *claimed* legitimate
   interest after Reject" — a known dark pattern, still a strong finding).

### 4b. (Optional, needs scanner edit) P0.3 — capture `tc_data` in-page
In `backend/scanner.py`, inside `PLAYWRIGHT_SCRIPT` → `scan_branch`, **after** the reject click +
reload (just before `cookies = ...`), add:
```python
tc_data = await page.evaluate("""() => new Promise((resolve) => {
  try {
    if (typeof window.__tcfapi !== 'function') return resolve(null);
    let settled = false;
    window.__tcfapi('addEventListener', 2, (d, ok) => {
      if (ok && d && (d.eventStatus === 'tcloaded' || d.eventStatus === 'useractioncomplete') && !settled) {
        settled = true; resolve(d);
      }
    });
    setTimeout(() => resolve(null), 3000);   // never hang the scan
  } catch (e) { resolve(null); }
})""")
```
Add `"tc_data": tc_data` to the branch's returned dict. If `__tcfapi` is absent it's `null` and you
use the 3a fallback. **This is the only scanner change you make.**

---

## 5. Requirements
Append to `backend/requirements.txt` (teammates also append — keep to your line):
```
iab-tcf
```
Your 3a fallback still needs a decoder; if `iab-tcf` install is problematic, a minimal hand-rolled
core-string bit decoder (segments: purposes consent = bits 116..139, vendor consent range-encoded) is
acceptable, but try the library first.

## 6. Return shape (exact)
```python
{
  "tcf_present": true,
  "cmp": "Sourcepoint",
  "gdpr_applies": true,
  "source": "tcfapi" | "request_param",
  "consent_after_reject": {"purpose_1": false, "purpose_2": false, "...": false},
  "mismatches": [
    {"vendor":"Criteo","vendor_id":91,"consent":false,"legitimate_interest":false,
     "fired":true,"evidence_url":"https://…/?gdpr=1&gdpr_consent=CPx…","tc_string_preview":"CPx…AAA"}
  ],
  "legitimate_interest_abuse": [ {"vendor":"Xandr","vendor_id":32,"...":"..."} ],
  "verdict": "consent_string_contradicts_traffic" | "no_mismatch" | "inconclusive",
  "available": true                        # false when TCF absent
}
```

## 7. Edge cases — handle every one
| Case | Required handling |
|---|---|
| No TCF (non-TCF CMP or none) | `{"tcf_present": false, "available": false}`; skip silently |
| `gdpr_applies == false` | site claims GDPR N/A → report as a NOTE, not a violation; `verdict="inconclusive"` |
| CMP present but reject not registered | require `tc_data.eventStatus == useractioncomplete/tcloaded`; else `inconclusive` |
| several differing `gdpr_consent` values | report anomaly; prefer `tc_data` if available; else most common |
| base64url without padding | re-pad before decode; catch errors → skip that string |
| GVL fetch fails / offline | curated map fallback; unmatched vendor → lower-confidence "unmapped vendor fired" |
| CMP / consent-infra domains (privacy-mgmt.com, cookielaw.org, consensu.org, sourcepoint) | **whitelist** — firing is expected, never a violation |
| legitimate interest true for a purpose/vendor | separate `legitimate_interest_abuse` bucket, not a hard mismatch |
| `__tcfapi` in stub state | the addEventListener + 3s timeout in P0.3 handles it; else fall back to 3a |
| vendor on a shared CDN it doesn't own | match only via curated map / GVL, not generic CDNs → avoid FPs |
| `iab-tcf` not installed | catch ImportError; fall back to minimal decoder or return `inconclusive` gracefully |

## 8. Coordination (three agents, shared files)
- **`scanner.py`** — your ONLY edit is adding the `tc_data` capture **after the reject reload** (bottom
  of `scan_branch`). Pillar 2's agent edits a **different** region (`find_cookie_policy_url` + the
  `if False` line near the top). Different spots → low conflict; keep your change minimal, don't
  reformat surrounding code. If you skip P0.3 (fallback-only), you don't touch `scanner.py` at all.
- **`agent.scan_one()`** — add ONE line: `card["tcf"] = analyze_tcf(scan_data)`. Leave the others'
  `card[...]` lines alone. Also mirror in `main.scan_endpoint`'s response dict.
- **`requirements.txt`** — append only `iab-tcf`.
- You do **not** touch `analyzer.py`, `semantic.py`, or `behavioral.py`.

## 9. Definition of done (acceptance criteria)
1. `backend/tcf.py` exists; `py_compile` passes; `decode_tc_string` handles unpadded base64url.
2. Unit tests in `backend/test_tcf.py` (synthetic `scan_data`, no browser):
   - `tc_data` with `purposeConsents[1]=false`, `vendorConsents[91]=false`, + an after-reject request
     to `criteo.com` → one mismatch for vendor 91;
   - `gdpr_applies=false` → `verdict="inconclusive"`, zero mismatches;
   - no TCF signal at all → `{"tcf_present": false, "available": false}`;
   - a `consensu.org`/CMP request firing → NOT a mismatch (whitelisted);
   - vendor with `vendorConsents=false` but `vendorLegitimateInterests=true` → lands in
     `legitimate_interest_abuse`, not `mismatches`.
3. Wired into `agent.scan_one` + `main.scan_endpoint`; `MOCK=true pytest -q` still green.
4. If P0.3 was added: a live TCF site (e.g., a Sourcepoint-based German news site) returns
   `tcf_present: true` with a populated `consent_after_reject`.

## 10. What the demo shows
A 🔒 badge: *"The site's own consent string encodes Criteo = NO. Yet Criteo fired after Reject —
carrying that exact string. This isn't our opinion; it's their own signal contradicting itself."*
Renders as the top evidence tier above behavioral/semantic/blocklist.
