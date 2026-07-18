# P2 HANDOFF — Semantic Policy Grounding (Embeddings + Cognee)

> **You are the agent building Pillar 2.** This file is self-contained — you do not need any
> other file. Cross-pillar view is in `PILLARS.md` (optional).

---

## 0. Mission (one line)
Replace the keyword "is this tracker in the policy?" check with **semantic coverage**: embed the
cookie policy and each tracker's purpose, and decide *declared / vague / undeclared* from cosine
similarity — so we catch *"we may use analytics tools"* failing to disclose a Meta advertising pixel.

**Why it matters:** OpenAI embeddings + a vector store as *the substance* is the exact pattern that
won the {Tech: Europe} Paris edition (MIRROR). Makes **OpenAI** and **Cognee** load-bearing (real
partner-tech points), and gives genuine AI depth instead of a yes/no prompt.

---

## 1. Project context (30 seconds)
ConsentGuard / "Reject-All Radar" is a GDPR scanner. A headless browser clicks **Reject All** and
records trackers that fire anyway. Then it checks whether those trackers are actually **disclosed in
the site's cookie policy**. You own that disclosure decision. Backend = FastAPI in `backend/`. The
current disclosure logic is a substring match in `backend/analyzer.py` — you're replacing it with
embeddings.

## 2. How to run & verify (do this first)
```bash
cd backend
python -m pip install -r requirements.txt
# your path needs an OpenAI key for real runs:
#   put OPENAI_API_KEY=sk-... in backend/.env
python -m pytest -q                       # your unit tests (mock the embeddings client — see §11)
MOCK=true python -m uvicorn main:app --port 8000    # smoke test the app still boots
```
Write unit tests that **mock the OpenAI embeddings call** so they run offline and deterministically.

---

## 3. GROUND TRUTH — the data you read
`scanner.run_scan(url)` → `scan_data`. Your inputs come through `analyzer.analyze_violations`:
```python
analyze_violations(violations, policy_text, page_html="")
# violations: list of dicts, each:
{ "domain":"connect.facebook.net", "category":"advertising",
  "company":"Meta", "data_collected":"Tracks users across sites for ad targeting" }
# policy_text: the cookie-policy text, plain (HTML already stripped), possibly "" (empty)
```
`policy_text` is produced by `analyzer.fetch_cookie_policy(scan_data["cookie_policy_url"])`.

**⚠️ CRITICAL PREREQUISITE — you must fix policy discovery first (see §4, P0.1).**
Today `scan_data["cookie_policy_url"]` is **hardcoded `None`** in the Playwright scanner, so
`policy_text` is usually empty and your embeddings have nothing to compare against. Fixing this is
part of your job.

---

## 4. Prerequisite you own — P0.1: restore cookie-policy discovery

### 4a. In `backend/scanner.py`
Inside `PLAYWRIGHT_SCRIPT`, function `scan_branch`, this line disables discovery:
```python
"cookie_policy_url": await find_cookie_policy_url(page, url) if False else None,
```
Change it to:
```python
"cookie_policy_url": await find_cookie_policy_url(page, url),
```
Then harden `find_cookie_policy_url(page, base_url)` in that same script: match anchors whose href OR
text contains any of `cookie, privacy, datenschutz, cookie-policy, cookie-richtlinie, privacy-policy`;
prefer "cookie" > "privacy" > "datenschutz"; return `urljoin(base_url, href)`.

### 4b. In `backend/analyzer.py` — `fetch_cookie_policy`
- Bump the truncation from `[:8000]` to `[:20000]` (more text = better recall; you chunk it anyway).
- Add a fallback: if `policy_url` is falsy, the caller should try common paths. Add a helper
  `discover_policy_url(base_url)` that GETs, in order, `/cookie-policy /privacy /datenschutz
  /legal/cookies /cookies` (5s timeout each) and returns the first `200` with body length > 500.
  Call it from the pipeline when `cookie_policy_url` is None. (Keep it defensive; never throw.)

> These are small, localized edits. Your teammate on Pillar 3 also edits `scanner.py` but in a
> **different** spot (adding TCF capture after the reject reload). Low conflict — see §10.

---

## 5. Build it — `backend/semantic.py`

### Public API
```python
class SemanticPolicyGrounder:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"): ...
    def analyze(self, violations: list[dict], policy_text: str) -> dict: ...   # analyzer-compatible
```

### Algorithm

**Step 1 — chunk the policy.**
- Sentence-split: `re.split(r'(?<=[.!?])\s+', policy_text)`; further split list items on `•`, `-`,
  newlines; merge tiny fragments so each chunk is ~120–500 chars (1–3 sentences).
- Drop chunks < 25 chars and obvious nav/boilerplate. Dedupe identical chunks by hash.
- Cap at `MAX_CHUNKS = 120` (embedding-cost bound); if over, keep the longest chunks.

**Step 2 — build a "declaration query" per tracker** (enriched with aliases):
```python
query = f"{company} ({domain}): a {category} technology that {data_collected}."
# + aliases, e.g. Meta→{facebook, meta pixel, fbevents},
#   Google Ads→{doubleclick, google marketing, adsense}, Microsoft→{bing, clarity}
```
If `data_collected` is short/empty, backfill from `from tracker_db import is_tracker`.

**Step 3 — embed** (batched):
```python
from openai import OpenAI
client = OpenAI(api_key=self.api_key)
resp = client.embeddings.create(model=self.model, input=[all_chunks... and separately all_queries...])
```
One call for all chunks, one for all tracker queries. **L2-normalize** every vector.

**Step 4 — store/retrieve in Cognee** (partner tech), keyed by `sha256(policy_text)` so all trackers
on a site reuse ONE index and it compounds across raids.
- **Graceful fallback:** if `cognee` import/config unavailable, hold vectors in a `numpy` matrix.
  Identical interface. Cosine = dot product of normalized vectors. Guard cognee with try/except and
  an env flag `COGNEE_ENABLED` (default false) — never let Cognee break the analysis.

**Step 5 — score.** For each tracker: cosine vs every chunk → `top_score`, `top_clause` (the chunk
text), and `top_3`.

**Step 6 — decide (hybrid, calibrated):**
```python
string_hit = any(tok in policy_lower for tok in {domain, root_domain, company, company.replace(" ","")})
if string_hit or top_score >= T_DECLARED:   status = "declared"       # T_DECLARED = 0.62
elif top_score >= T_VAGUE:                  status = "vague"          # T_VAGUE   = 0.45
else:                                        status = "undeclared"
declared = (status == "declared")
```
- Thresholds via env `SEM_T_DECLARED`, `SEM_T_VAGUE`. **Always expose the score + closest clause** so
  a mis-set threshold is still defensible on stage.
- `vague` = the "we may use analytics tools" case: medium score, no vendor named → not lawful
  disclosure.

---

## 6. Return shape (superset of the existing analyzer contract — keep it compatible!)
The existing pipeline expects `{"violations": [...], "undeclared": [...], "declared": [...]}`.
You **add** fields; you must not remove those keys.
```python
{
  "violations": [ { ...original tracker fields...,
      "declared": false,
      "disclosure_status": "declared" | "vague" | "undeclared",
      "disclosure_score": 0.29,
      "closest_clause": {"text": "We may use analytics tools to…", "score": 0.29},
      "reasoning": "The policy only vaguely mentions analytics; a Meta advertising pixel is not covered.",
      "violation_reason": "Not semantically disclosed (score 0.29 vs closest clause)"
  } ],
  "undeclared": [ ...where declared == False and status != "declared"... ],
  "declared":   [ ...where declared == True... ],
  "vague":      [ ...where status == "vague"... ],
  "policy_status": "ok" | "no_policy" | "too_short",
  "engine": "embeddings"
}
```
Keep `undeclared` = items with `declared == False`. Downstream code (`fixer`, `reporter`, `agent`)
already consumes `undeclared`/`declared` — don't break that.

## 7. Wire into `backend/analyzer.py`
In `analyze_violations(violations, policy_text, page_html="")`, add your path as **preferred** when a
policy exists:
```python
provider   = os.getenv("LLM_PROVIDER", "auto").strip().lower()
openai_key = os.getenv("OPENAI_API_KEY", "").strip()

if provider in ("auto","openai") and openai_key and policy_text.strip():
    try:
        from semantic import SemanticPolicyGrounder
        return SemanticPolicyGrounder(openai_key).analyze(violations, policy_text)
    except Exception:
        pass
# ... then the existing OpenAI → Claude → local fallbacks stay as-is ...
```
**Recommended hybrid:** embeddings decide the status (deterministic), then make ONE cheap
`gpt-4o-mini` chat call to write the `reasoning` sentence *given the score + closest clause*. If that
call fails, fill `reasoning` from a template — never throw.

## 8. Edge cases — handle every one
| Case | Required handling |
|---|---|
| No policy found (even after P0.1 fallback) | `policy_status="no_policy"`; return all as `undeclared` (low-confidence); don't crash |
| Policy too short / cookie-wall stub (<200 chars) | `policy_status="too_short"`; treat as undeclared w/ note |
| German policy vs English purpose | `text-embedding-3-small` is multilingual → works; add German aliases to strengthen |
| PDF-only policy | not fetched (HTML only) → `no_policy`; documented limitation |
| Policy > 20k chars | chunk + `MAX_CHUNKS` cap |
| `OPENAI_API_KEY` missing | your path is skipped by the guard in §7 → falls back to local; also handle inside `analyze` defensively |
| OpenAI 429 / rate limit | retry twice w/ backoff; on failure raise so the guard falls back |
| Duplicate trackers on a site | score once per (domain,purpose); memoize |
| Cost blowup across a raid | embed the policy ONCE per site (cache by `sha256(policy_text)`); reuse for all its trackers |
| Cognee unavailable | numpy in-memory fallback, same interface |
| Model/dim change | key the cache by `model` too; never mix vector dims |
| Empty `violations` | return the empty `{"violations":[],"undeclared":[],"declared":[]}` immediately |

## 9. Requirements
Append to `backend/requirements.txt` (your teammates also append — keep to these lines):
```
numpy
# cognee   # optional, heavy; enable with COGNEE_ENABLED=true
```
`openai` is already present.

## 10. Coordination (three agents, shared files)
- **`scanner.py`** — you edit `find_cookie_policy_url` + the `if False` line (top area of
  `PLAYWRIGHT_SCRIPT`). Pillar 3's agent edits a **different** region (adds `tc_data` capture *after
  the reject reload*, near the bottom of `scan_branch`). Different spots → low conflict; if you both
  edit, keep each change minimal and don't reformat surrounding code.
- **`analyzer.py`** — this is yours to modify (adding the embeddings path). No other pillar touches it.
- **`agent.scan_one()`** — you likely don't need to touch it: your disclosure fields ride through the
  existing `violations` dicts automatically. If you want to surface `policy_status`, add ONE line
  `card["policy_status"] = analysis.get("policy_status")` and leave the others' lines alone.
- **`requirements.txt`** — append only `numpy` (+ optional cognee comment).

## 11. Definition of done (acceptance criteria)
1. P0.1 done: a live (or fixture) scan now returns a non-null `cookie_policy_url` and non-empty
   `policy_text`.
2. `backend/semantic.py` exists; `py_compile` passes.
3. Unit tests in `backend/test_semantic.py` (mock the embeddings client to return fixed vectors):
   - policy = "we use analytics" → Google Analytics = `vague`, Meta ad pixel = `undeclared` (assert
     the *ordering*/buckets, not exact floats);
   - policy naming "Meta Pixel" explicitly → `declared` via `string_hit`;
   - empty policy → `policy_status="no_policy"` and everything `undeclared`.
4. `analyze_violations` returns the superset shape; `undeclared`/`declared` still populated; existing
   `MOCK=true pytest -q` still green (you didn't break the contract).

## 12. What the demo shows
Under each flagged tracker: *"Policy says 'we may use analytics' — similarity 0.29 to Facebook's
advertising purpose. Vague ≠ disclosure."* The `closest_clause` + `disclosure_score` render as the
"🧠 semantic gap" evidence tier.
