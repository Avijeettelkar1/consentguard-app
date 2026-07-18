# Technical Pillars — Engineering Spec

> Audience: the engineers building Reject-All Radar for the {Tech: Europe} × Almedia hackathon.
> This is the "technical strength" half of the score. Read the pillar you own end-to-end
> before writing code. Every design decision here is grounded in what the scanner *actually*
> returns today — see **Ground truth** below.

---

## Ground truth: what the scanner already gives us

`scanner.run_scan(url, auth)` returns a dict. The fields that matter for these pillars:

```python
scan_data = {
  "before": [url, ...],                      # reject branch, pre-consent request URLs (deduped)
  "after":  [url, ...],                      # reject branch, POST-consent request URLs (deduped)
  "clicked_accept": bool, "clicked_reject": bool,
  "consent_platform": "OneTrust" | "Sourcepoint" | ... | None,
  "cookie_policy_url": None,                 # ⚠️ HARDCODED None in the Playwright path today
  "page_html_for_fallback": "<...first 8000 chars...>",
  "accept": <branch>, "reject": <branch>,
  "comparison": {...},                       # accept_only/reject_only/common requests + cookie KEYS
  "scanner": "playwright" | "daytona" | "http",
}

# each <branch> (accept / reject):
branch = {
  "action": "accept" | "reject",
  "clicked": bool, "clicked_selector": str | None,
  "initial_requests": [url, ...],            # pre-consent URLs
  "post_consent_requests": [url, ...],       # post-consent URLs
  "initial_request_records":      [{ "url", "method", "resource_type", "post_data" }, ...],
  "post_consent_request_records": [{ "url", "method", "resource_type", "post_data" }, ...],  # ← GOLD
  "cookies": [{ "name","domain","path","expires","httpOnly","secure","sameSite" }, ...],  # ⚠️ NO value
  "consent_platform": str | None,
  "page_html_for_fallback": "<...>",
}
```

**Key consequences**
- `post_consent_request_records` carry **full URLs (with query strings) and POST bodies (≤2000 chars)** → Pillar 1 works purely on this, no scanner change.
- **Cookie values are stripped** (`sanitize_cookies`) → we cannot correlate cookie *values*; we correlate identifier values found in **request URLs and bodies** instead.
- **`cookie_policy_url` is `None`** in the Playwright path (`find_cookie_policy_url` is gated behind `if False`) → **Pillar 2 must fix policy discovery first**.
- The **HTTP fallback** scanner produces no `*_records` → all three pillars must **degrade gracefully to empty** when records are missing.
- `tag_audit.py` already classifies *known* payloads (GA4, Google Ads, DoubleClick, Bing, Meta). Pillar 1 is deliberately **identifier-driven**, so it catches *unknown/unlisted* trackers — that's the novelty.

**Integration surface (all three pillars):**
- Per-site assembly lives in `agent.scan_one()` → add pillar outputs to the site **card**.
- Single scan lives in `main.scan_endpoint()` → add pillar outputs to the `/scan` response.
- Pillar 2 plugs into `analyzer.analyze_violations()` as a new preferred path.

---

## Prerequisite fixes (do these before Pillars 2 & 3)

### P0.1 — Restore cookie-policy discovery (blocks Pillar 2)
In `scanner.PLAYWRIGHT_SCRIPT`, `scan_branch` currently returns:
```python
"cookie_policy_url": await find_cookie_policy_url(page, url) if False else None,
```
Remove the `if False else None`. Then harden `find_cookie_policy_url`:
- Match anchors whose href **or** text contains: `cookie`, `privacy`, `datenschutz`, `cookie-policy`, `cookie-richtlinie`, `privacy-policy`.
- Prefer the most specific ("cookie" > "privacy" > "datenschutz").
- Resolve relative → absolute with `urljoin`.
- **Fallback probe** (in Python, `analyzer.fetch_cookie_policy` side): if still `None`, try common paths: `/cookie-policy`, `/privacy`, `/datenschutz`, `/legal/cookies`, `/cookies`. HEAD/GET each with a 5s timeout; take the first `200` whose body length > 500.
- Edge: policy behind consent wall / JS-rendered → `fetch_cookie_policy` gets partial text; that's acceptable, Pillar 2 degrades to "vague/no_policy".

### P0.2 — (Pillar 1 optional strengthener) capture response metadata
Not required for v1 of Pillar 1. If time allows, in `make_record` add response capture via a `page.on("response")` handler to record `Set-Cookie` names and response `Location` redirects (cookie-sync often happens through 302 redirect chains). Keep values hashed, never raw.

### P0.3 — (Pillar 3 enabler) capture TCF state in-page
Pillar 3's authoritative path needs the decoded consent object. After the reject click + reload in `scan_branch`, add:
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
    setTimeout(() => resolve(null), 3000); // never hang the scan
  } catch (e) { resolve(null); }
})""")
```
Return `tc_data` in the branch dict. If `__tcfapi` is absent, this is `null` and Pillar 3 falls back to reading `gdpr_consent` from request params (no scanner change needed for the fallback).

---

# PILLAR 1 — Behavioral tracker detection (identity syncing)

**One line for judges:** *"We don't use a blocklist. We detect trackers by behavior — the same
user identifier being shared across unrelated companies — straight from the raw traffic."*

**Why it scores technical strength:** it's a real algorithm over real data (systems work, no LLM),
it catches trackers **not** on any list, and it produces a visceral, defensible demo (an identity
graph forming live). This is the crown jewel.

### Module: `backend/behavioral.py`

```python
def detect_id_syncing(scan_data: dict, site_url: str) -> dict: ...
```
Operates on `scan_data["reject"]["post_consent_request_records"]` (primary — this is the
after-Reject traffic, where sharing = a violation). Also read the accept branch to compute
"blocked_by_reject vs still_syncing".

### Algorithm

**Step 1 — Registrable-domain helper.** Sharing must be measured at the *organization* level,
not host level (`ads.google.com` and `google-analytics.com` are both Google → still cross-org vs
`facebook.com`). Implement `registrable_domain(host)`:
- Prefer `tldextract` if installed (add to requirements). Else a fallback using a small built-in
  multi-part-suffix set (`co.uk, org.uk, com.au, co.jp, com.br, co.in, ...`) and "last 2 labels"
  otherwise.
- Lowercase, strip `www.`, strip port.

**Step 2 — Token extraction.** For each request record, pull candidate identifier strings from:
- **Query params:** `parse_qs(urlparse(url).query)` → every value.
- **Path segments:** split path on `/`, `;`, `,` → segments (some IDs ride in the path).
- **POST body:** try, in order: (a) `parse_qs(body)`; (b) `json.loads(body)` then recurse over
  string leaves; (c) treat as opaque and regex out long tokens.
- **Fragment:** rare, but parse if present.
- Decode each value up to **2 levels** of `urllib.parse.unquote`. Also attempt a base64url decode;
  if it yields printable JSON/keyvals, recurse into it (pixels pack params in base64).
- Record for every token: `(value, source_domain, location, param_name)` where `source_domain =
  registrable_domain(request host)`.

**Step 3 — Identifier filter (the precision-critical part).** Keep a token only if it "looks like a
per-user identifier". Apply, in order:
- Length in `[ID_MIN=8, ID_MAX=128]`.
- Passes at least one *positive* shape test:
  - UUID/GUID regex `^[0-9a-f]{8}-[0-9a-f]{4}-...`;
  - hex of length ∈ {16,24,32,40,48,64} (covers md5/sha1/sha256 → **hashed-PII candidates**);
  - base64/base64url of length ≥ 16;
  - high **Shannon entropy** ≥ `ENTROPY_MIN=3.0` bits/char over the alphabet.
- Fails **none** of the *negative* tests (drop if any true):
  - pure integer that parses as a plausible **epoch** (10 digits ≈ 2001–2033, or 13-digit ms) → timestamp/cache-buster;
  - matches a resolution/size pattern `^\d{3,4}[xX]\d{3,4}$`;
  - a known constant / low-value token: `{true,false,null,undefined,none,0,1}`, language codes (`en,de,en-US`), boolean-ish, currency codes;
  - equals the site's own registrable domain, a bare hostname, a URL, a MIME type, or a version string `^v?\d+(\.\d+)+$`;
  - **the TCF consent string** or a `gdpr_consent`/`euconsent`/`gdpr`/`us_privacy` param value — consent signals are shared across vendors *by design*; excluding them prevents the biggest false-positive class (this is also where Pillar 3 picks them up);
  - appears verbatim in `page_html_for_fallback` (likely a public/site-wide constant, e.g., a GTM ID, publisher ID, or asset hash — not a per-user id).
- Normalize survivors: strip quotes/whitespace; keep original casing (IDs are case-sensitive).

**Step 4 — Build the sharing map.** `token -> set(source_domain)`. Also keep, per token, the list
of `(domain, param_name, location)` for evidence.

**Step 5 — Select sync identifiers.** A token is a **sync identifier** when:
- it reached **≥ 2 distinct registrable domains**, AND
- **≥ 2 of those are third-party** (≠ the site's own registrable domain). First-party-only
  sharing across the site's own subdomains is *not* syncing → drop.
- Strength tiers: `domains≥3` or any hashed-PII candidate → **high**; `domains==2` (both third-party)
  → **medium**.

**Step 6 — After-Reject weighting.** Compute the same over the **accept** branch. For each sync
identifier, set `after_reject=True` if it appears in the reject branch. `blocked_by_reject` = synced
under accept but not reject (good). The headline is **sync identifiers with `after_reject=True`** —
identity sharing that survives the user saying "no".

**Step 7 — Identity graph.** Nodes = registrable domains (tag `first_party|third_party`, enrich
`company/category` via `tracker_db.is_tracker`). Edge `(a,b)` weight = number of shared identifiers.
`worst_cluster` = connected component / highest-degree third-party hub.

### Return shape
```python
{
  "sync_identifiers": [
    {
      "token_preview": "3f9a…c1d7",           # masked: first4…last4, never the raw value
      "token_hash": "sha256:…",               # stable id for the UI, not reversible
      "kind": "uuid" | "hex32" | "base64" | "opaque" | "hashed_pii",
      "entropy": 3.94,
      "domains": ["doubleclick.net","facebook.com","criteo.com"],
      "third_party_domain_count": 3,
      "after_reject": true,
      "severity": "high",
      "evidence": [
        {"domain":"doubleclick.net","param":"uid","location":"query",
         "url_preview":"https://…/pixel?uid=3f9a…"},
        ...
      ]
    }, ...
  ],
  "identity_graph": {
    "nodes": [{"id":"doubleclick.net","type":"third_party","company":"Google","category":"advertising"}, ...],
    "edges": [{"source":"doubleclick.net","target":"facebook.com","shared_ids":2}, ...]
  },
  "worst_cluster_size": 3,
  "hashed_pii_suspected": true,
  "summary": "1 identifier was shared with 3 unrelated ad companies after Reject All.",
  "available": true      # false when records are missing (HTTP fallback) → callers fall back to blocklist
}
```

### Edge cases (handle explicitly)
| Case | Handling |
|---|---|
| HTTP-fallback scan (no `*_records`) | return `{"available": false, ...empty}`; caller keeps blocklist result |
| Empty query + empty body request | skip (no tokens) |
| Same value legitimately shared (public API key, font hash, publisher ID) | dropped by "appears in page HTML" + version/constant tests |
| Shared **timestamp** / cache-buster | dropped by epoch test; also rarely equal across domains |
| TCF consent string shared across vendors | dropped by consent-param test (by design, not a user ID) |
| Screen size / locale shared | dropped by resolution pattern + low entropy + language-code list |
| Hashed email (md5/sha1/sha256) | **kept & flagged** `hashed_pii` (strongest signal) |
| Double-/base64-encoded params | decode ≤2 levels + base64 attempt before filtering |
| Non-ASCII / malformed values | wrap decode in try/except; skip on error |
| Google-owned multi-domain (`doubleclick.net` + `google-analytics.com`) | both → registrable `google.com`? No — they are distinct registrable domains; treat as distinct orgs but note in enrichment they map to the same `company` — the demo still holds (Google → Meta → Criteo is the money shot) |
| Very short IDs (<8) | skip (collision-prone) |
| Performance blowup on huge pages | cap tokens/request at 50, total tokens at 5000, requests at 1500; dedupe aggressively |
| Privacy of our own output | **never** emit raw token values; mask + hash only |

### Integration
- `agent.scan_one()` → `card["identity_sync"] = detect_id_syncing(scan_data, url)`; set
  `card["behavioral_flag"] = worst_cluster_size >= 2`.
- Feed graph nodes/edges up into the raid-level `aggregate_patterns()` so the industry board can show
  a **cross-site identity graph** (a tracker that syncs on many sites = a mega-hub).
- Frontend: force-directed graph; animate edges appearing as the raid streams.

### Test plan
- Unit: feed synthetic records where token `T` hits 3 domains after reject → expect one `high` sync
  identifier with those 3 domains. Feed a shared epoch → expect none. Feed a `gdpr_consent` value on
  3 domains → expect none (excluded).
- Live: `theguardian.com`, `bild.de`, `zeit.de` reliably cookie-sync; use one as the demo.
- Deterministic demo: extend `test_site/` (see below) with two pixels that echo the same `uid`.

### Effort: ~3–4 h. No scanner change, no LLM, no external API.

---

# PILLAR 2 — Semantic policy grounding (embeddings + Cognee)

**One line for judges:** *"'Declared?' isn't a keyword match. We embed the policy and the tracker's
purpose and score semantic coverage — so we catch 'we may use analytics tools' failing to cover a
Meta advertising pixel."*

**Why it scores:** OpenAI embeddings + a vector store as *the substance* is the exact pattern that won
the Paris edition (MIRROR). Makes OpenAI **and** Cognee load-bearing, not decorative.

### Prerequisite: P0.1 (policy discovery) must be done. Also raise the fetch cap.
In `analyzer.fetch_cookie_policy`, bump the truncation from `[:8000]` to `[:20000]` for the embeddings
path (chunking handles length; more text = better recall).

### Module: `backend/semantic.py`

```python
class SemanticPolicyGrounder:
    def __init__(self, api_key: str, model="text-embedding-3-small"): ...
    def embed_policy(self, policy_text: str) -> PolicyIndex: ...     # cached by sha256(text)+model
    def score_tracker(self, tracker: dict, index: PolicyIndex) -> dict: ...
    def analyze(self, violations: list[dict], policy_text: str) -> dict: ...  # analyzer-compatible
```

### Algorithm

**Step 1 — Chunk the policy.**
- Split into clauses: sentence-split (`re.split(r'(?<=[.!?])\s+')`), then further split list items
  (`•`, `-`, `\n`) and headings. Merge tiny fragments so each chunk is ~1–3 sentences (target
  120–500 chars). Drop chunks < 25 chars and obvious nav/boilerplate.
- Dedupe identical chunks (hash). Cap at `MAX_CHUNKS=120` (embed cost bound); if over, keep the
  longest/most-informative (or window-sample) — a policy rarely needs more.

**Step 2 — Build the tracker "declaration query."** For each tracker construct a NL statement to
match against the policy, enriched with aliases:
```
f"{company} ({domain}): a {category} technology that {data_collected}."
+ aliases from a small map, e.g. Meta→{facebook, meta pixel, fbevents},
  Google Ads→{doubleclick, google marketing, adsense}, etc.
```
Short/empty `data_collected` → backfill from `tracker_db`.

**Step 3 — Embed.** One batched OpenAI embeddings call for **all** chunks (list input) and one for all
tracker queries. `text-embedding-3-small`, 1536-dim, ~$0.00002/1k tokens → whole policy is a fraction
of a cent. L2-normalize all vectors.

**Step 4 — Store / retrieve in Cognee.** Persist the policy chunk vectors in Cognee keyed by
`sha256(policy_text)` so (a) all trackers on the same site reuse one index, and (b) it compounds across
raids. **Graceful fallback:** if Cognee is unavailable, keep vectors in an in-process
`numpy` matrix — identical interface. Cosine = dot product of normalized vectors.

**Step 5 — Score.** For each tracker: cosine vs every chunk → `top_score`, `top_clause`, `top_k=3`.

**Step 6 — Decide (calibrated + hybrid).**
```
string_hit = domain/root-domain/company literally present in policy   # high precision
if string_hit or top_score >= T_DECLARED (0.62):   status = "declared"
elif top_score >= T_VAGUE (0.45):                  status = "vague"        # partial/ambiguous
else:                                              status = "undeclared"
declared = (status == "declared")
```
- `final_score = max(top_score, 1.0 if string_hit else 0)`.
- Expose the numbers; thresholds are env-overridable (`SEM_T_DECLARED`, `SEM_T_VAGUE`). Because we
  *show the score and the closest clause*, a mis-set threshold is still defensible on stage.
- `vague` is its own bucket — this is the "we may use analytics tools" story: medium score, no
  vendor named → not lawful disclosure.

### Return shape (superset of the existing analyzer contract)
```python
{
  "violations": [ { ...tracker,
      "declared": false,
      "disclosure_status": "declared" | "vague" | "undeclared",
      "disclosure_score": 0.29,
      "closest_clause": {"text": "We may use analytics tools to…", "score": 0.29},
      "reasoning": "…",            # optional NL line, see hybrid below
      "violation_reason": "…"
  }, ...],
  "undeclared": [...], "declared": [...], "vague": [...],
  "policy_status": "ok" | "no_policy" | "too_short",
  "engine": "embeddings"
}
```

### Wiring into `analyzer.analyze_violations`
Add a new **preferred** path, ordered before the LLM:
```
if OPENAI_API_KEY and policy_text:  _analyze_with_embeddings(...)   # deterministic, defensible
elif OPENAI_API_KEY:                _analyze_with_openai(...)        # existing, for the reasoning line
elif ANTHROPIC_API_KEY:             _analyze_with_claude(...)
else:                               _analyze_locally(...)
```
**Hybrid (recommended):** embeddings decide `declared/vague/undeclared` (numbers), then make **one**
cheap `gpt-4o-mini` call to write the first-person `reasoning` sentence *given the score + closest
clause*. Deterministic verdict + narrative flair — depth and demo in one.

### Edge cases
| Case | Handling |
|---|---|
| No policy found (P0.1 also failed) | `policy_status="no_policy"`; that's itself a finding ("no locatable cookie policy"); fall back to `_analyze_locally` for declared/undeclared |
| Policy too short / cookie-wall stub | `policy_status="too_short"`; treat all as `undeclared` with low confidence note |
| German policy vs English purpose | `text-embedding-3-small` is multilingual → works; strengthen by adding German aliases (`Datenschutz`, vendor German names) |
| PDF-only policy | not fetched (HTML only) → `no_policy`; document as a known limitation |
| Very long policy (>20k) | chunk + `MAX_CHUNKS` cap |
| OpenAI key missing | embeddings path unavailable → fall back to keyword/local; log once |
| OpenAI rate limit / 429 | retry w/ backoff (2 tries); on failure fall back to local for that site |
| Duplicate trackers on a site | score once per (domain,purpose); memoize |
| Cost blowup across a raid | policy embedded **once per site** (cache by hash) and reused for all its trackers |
| Cognee down | in-memory numpy fallback, same interface |
| Threshold miscalibration | show score + clause; env-tunable; never hide the number |
| Embedding dim mismatch (model change) | key cache by `model` too; never mix dims |

### Test plan
- Craft a policy that says only "we use analytics." Expect: Google Analytics → `vague` (~0.4–0.55),
  Meta advertising pixel → `undeclared` (<0.4). Assert ordering, not exact values.
- A policy that names "Meta Pixel" explicitly → `declared` via string_hit even if score is mid.
- No-policy site → `no_policy` + local fallback still returns undeclared for known trackers.

### Effort: ~2–3 h. Partner tech: **OpenAI embeddings (load-bearing) + Cognee (vector store).**

---

# PILLAR 3 — TCF consent-string decoding + protocol mismatch (stretch)

**One line for judges:** *"On sites using the IAB consent protocol, we decode the site's own consent
string and prove it byte-for-byte contradicts what fired — the site's own signal says 'no', yet the
vendor loaded anyway."*

**Why it scores:** protocol-level, byte-exact proof + deep domain mastery most teams don't know exists.
It's the mic-drop. It's also the **highest risk** (coverage limited to TCF sites, needs the GVL + a
decoder), so build it **only after Pillars 1 & 2 land.**

### Two acquisition paths (implement the fallback first — it needs no scanner change)
1. **Fallback (no scanner change):** many vendor requests carry `gdpr_consent=<TCstring>` and
   `gdpr=1` in the query. Pull these from `reject.post_consent_request_records` and decode.
2. **Authoritative (needs P0.3):** read the decoded `tc_data` object from `__tcfapi` captured in-page.
   Prefer this when present — it gives `purposeConsents`, `vendorConsents`,
   `purposeLegitimateInterests`, `vendorLegitimateInterests` directly, already decoded.

### Module: `backend/tcf.py`
```python
def decode_tc_string(tc: str) -> dict: ...          # base64url → {purposes:{1:False,...}, vendors:{755:False,...}, gdpr_applies}
def analyze_tcf(scan_data: dict) -> dict: ...        # top-level: presence, consent-after-reject, mismatches
```
Use the `iab-tcf` library for decoding (add to requirements, optional). Handle base64url **padding**
(TC strings drop `=`; re-pad to len%4==0 before decode).

### Algorithm
**Step 1 — Detect TCF.** `tcf_present` if any of: `consent_platform ∈ {Sourcepoint, OneTrust, Didomi,
Quantcast, Usercentrics, TrustArc, Cookiebot}`, `scan_data.reject.tc_data` not null, or any reject
request has a `gdpr_consent` param.

**Step 2 — Consent state after reject.**
- Authoritative: from `tc_data` → `purposeConsents`, `vendorConsents`, and the legitimate-interest maps.
- Fallback: `decode_tc_string(gdpr_consent_value)`.
- After "Reject All," a compliant state has **Purpose 1 (store/access info) = false** and all
  `vendorConsents = false`.

**Step 3 — Map fired vendors → TCF vendor IDs.** Load the IAB **Global Vendor List** (GVL JSON;
fetch + cache; ship a curated fallback map for the demo's key vendors: Google Advertising Products
755, Meta 'Meta Platforms' , Criteo 91, Xandr 32, Amazon 793, The Trade Desk 21, …). For each
after-reject request domain, resolve to a vendor entry (by vendor `name`/known domains; heuristic
substring match with a curated override table).

**Step 4 — Prove the mismatch.** A **violation** = a request fired after reject to a domain owned by
vendor `V`, where the site's own consent string encodes `vendorConsents[V] = false` **and**
`purposeConsents[1] = false`. The evidence is the exact request **carrying that very consent string**.
Also surface the nuanced case: `vendorConsents[V]=false` but `vendorLegitimateInterests[V]=true` →
"fired under **claimed legitimate interest** after Reject" (a known dark pattern — flag distinctly).

### Return shape
```python
{
  "tcf_present": true,
  "cmp": "Sourcepoint",
  "gdpr_applies": true,
  "consent_after_reject": {"purpose_1": false, "purpose_2": false, ...},
  "mismatches": [
    {"vendor": "Criteo", "vendor_id": 91, "consent": false, "legitimate_interest": false,
     "fired": true, "evidence_url": "https://…/?gdpr=1&gdpr_consent=CPx…",
     "tc_string_preview": "CPx…AAA"},
    ...
  ],
  "legitimate_interest_abuse": [ {"vendor":"Xandr","vendor_id":32,...} ],
  "verdict": "consent_string_contradicts_traffic",
  "available": true
}
```

### Edge cases
| Case | Handling |
|---|---|
| No TCF (non-TCF CMP or none) | `{"tcf_present": false, "available": false}`; skip silently |
| `gdpr_applies == false` | site claims GDPR N/A → report as a note, not a violation |
| CMP present but reject not registered | read `eventStatus`; require `useractioncomplete`/`tcloaded`; else mark inconclusive |
| Multiple differing `gdpr_consent` values | report anomaly; use the `tc_data` authoritative one if available |
| Base64url without padding | re-pad before decode; catch decode errors → skip that string |
| GVL fetch fails / offline | curated vendor map fallback; unmatched vendor → lower-confidence "unmapped vendor fired" |
| CMP / consent-infra domains (privacy-mgmt.com, cookielaw.org, consensu.org) | whitelist — firing is expected, not a violation |
| Legitimate-interest true for a purpose | separate `legitimate_interest_abuse` bucket, not a hard mismatch (but still a strong finding) |
| `__tcfapi` in stub state | the addEventListener path + 3s timeout in P0.3 handles it; fallback to param decode |
| Vendor uses a shared CDN not owned by them | match on known vendor endpoints/curated map, not generic CDNs, to avoid FPs |

### Integration
- `agent.scan_one()` → `card["tcf"] = analyze_tcf(scan_data)`.
- In the UI, when `tcf.mismatches` is non-empty, show the "🔒 protocol proof" badge — the strongest
  evidence tier, above blocklist and semantic.

### Test plan
- Feed a synthetic `tc_data` with purpose1=false + vendor 91 false, plus an after-reject request to a
  Criteo domain → expect one mismatch for vendor 91.
- Feed `gdpr_applies=false` → expect a note, zero mismatches.
- Live TCF sites for a real demo: German news via Sourcepoint (e.g., a Spiegel/Bild-style CMP).

### Effort: ~3 h + risk. Needs `iab-tcf` + GVL handling + vendor mapping. Build last.

---

## Evidence hierarchy (how the three pillars combine in the verdict)

Rank findings by strength; the UI shows the highest available badge per tracker:

1. **🔒 Protocol proof (Pillar 3)** — the site's own consent string says no, yet it fired. Undeniable.
2. **🕸️ Behavioral proof (Pillar 1)** — the same user ID shared across unrelated orgs after reject.
3. **🧠 Semantic gap (Pillar 2)** — the policy does not cover this tracker's purpose (with score).
4. **📋 Blocklist match (existing)** — a known tracker domain fired (baseline).

Pitch line: *"Four independent evidence tiers, from a downloaded list all the way to the site's own
cryptographic consent signal — no claim without a source."*

---

## Shared: deterministic local demo (de-risk the stage)

Extend `test_site/` (already in the repo) into a reproducible fixture so a pillar demo can't fail on a
flaky live site:
- `test_site/index.html`: load two `<img>`/`fetch` pixels to two different fake vendor hosts, both
  echoing the **same** `uid=<uuid>` (triggers Pillar 1 deterministically). Add a hidden `__tcfapi`
  stub returning purpose1=false (triggers Pillar 3). Fire them **after** a fake "Reject" handler.
- `test_site/privacy.html`: a policy that only says "we may use analytics" (triggers Pillar 2 `vague`
  for analytics, `undeclared` for the ad pixel).
Serve with `python -m http.server`; scan `http://localhost:PORT`. This is your safety demo.

---

## Requirements to add
```
tldextract      # Pillar 1 registrable-domain (optional; has fallback)
numpy           # Pillar 2 cosine fallback when Cognee is absent
iab-tcf         # Pillar 3 consent-string decode (optional; fallback path exists)
# openai already present (embeddings); cognee optional
```

## Build order (given the hours)
1. **P0.1** policy discovery fix (5 min, unblocks P2).
2. **Pillar 1** — highest technical ROI, no deps on keys. Ship the identity graph.
3. **Pillar 2** — embeddings + Cognee; hybrid reasoning line.
4. **Self-verify loop** — wire existing `run_verify_scan` into the card (cheap agent credibility).
5. **Pillar 3** — only if 1+2 are solid. It's the mic-drop, not the foundation.
