# ConsentGuard — Full Team Context

## What We're Building

ConsentGuard is a GDPR cookie compliance scanner. It:
1. Visits a website inside a sandboxed browser
2. Clicks the "Reject All" cookie button
3. Watches which third-party trackers fire network requests **anyway** (GDPR violation)
4. Uses Claude AI to check whether those trackers are even declared in the cookie policy
5. Generates: a policy fix, banner config fix, fine estimate, and formal DPA complaint letter

**The core insight:** Most websites that show "Reject All" buttons still fire ad trackers. This is illegal under GDPR Art. 7. We make that visible and actionable.

---

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Sandbox | Daytona | Isolated browser environment with Playwright pre-installed |
| Browser automation | Playwright (inside Daytona) | Clicks cookie banners, intercepts network traffic |
| Tracker database | Disconnect.me | Open-source list of 5000+ known tracking domains |
| AI analysis | Claude claude-sonnet-4-6 (Anthropic) | Reads cookie policies, determines violations, writes fixes |
| Backend | FastAPI (Python) | REST API, deployed on Railway |
| Frontend | Vanilla HTML/CSS/JS | Single file, deployed on Vercel |
| Backend deploy | Railway | Free tier, auto-deploys from git push |
| Frontend deploy | Vercel | Free tier, CDN-distributed |

---

## How the Scan Flow Works (end to end)

```
User enters URL
      ↓
FastAPI /scan endpoint (main.py)
      ↓
scanner.py → Daytona sandbox → Playwright opens URL
                              → records all network requests (before)
                              → clicks "Reject All" button
                              → waits 3s
                              → reloads page
                              → records all new network requests (after)
                              → returns {before, after, clicked_reject, consent_platform, cookie_policy_url}
      ↓
tracker_db.py → downloads Disconnect.me tracker list (cached)
analyzer.py → find_violations(): cross-refs "after" requests against tracker DB
            → fetch_cookie_policy(): fetches the cookie policy text from the site
            → analyze_violations(): sends to Claude → returns {violations, undeclared, declared}
      ↓
fixer.py → generate_fixes(): sends undeclared trackers to Claude → returns {policy_fix, banner_fix}
reporter.py → calculate_exposure(): estimates GDPR fine based on violation count
            → generate_complaint(): Claude drafts a formal DPA complaint letter
            → run_verify_scan(): re-scans with tracker domains blocked to confirm fix
      ↓
FastAPI returns full JSON response
      ↓
frontend/index.html renders results: violations table, fixes, fine estimate, complaint letter
```

---

## File Map — Who Owns What

```
consentguard/
├── snapshot_setup.py        ← Person 1: run FIRST, builds Daytona snapshot
├── backend/
│   ├── scanner.py           ← Person 1: Playwright scan inside Daytona
│   ├── tracker_db.py        ← Person 1: Disconnect.me tracker lookup
│   ├── analyzer.py          ← Person 2: tracker matching + Claude policy analysis
│   ├── fixer.py             ← Person 2: Claude fix generation
│   ├── reporter.py          ← Person 2: GDPR exposure + complaint letter
│   ├── main.py              ← Person 3: FastAPI app (imports P1 + P2)
│   ├── requirements.txt     ← Person 3
│   └── .env.example         ← Person 3
├── frontend/
│   └── index.html           ← Person 3: entire UI
├── railway.toml             ← Person 3: Railway deploy config
└── vercel.json              ← Person 3: Vercel deploy config
```

**Nobody touches another person's files.** No merge conflicts this way.

---

## Environment Variables

Create `backend/.env` (copy from `.env.example`):

```
DAYTONA_API_KEY=      ← from app.daytona.io → API Keys
ANTHROPIC_API_KEY=    ← from console.anthropic.com → API Keys
DAYTONA_SNAPSHOT=     ← Person 1 fills this after running snapshot_setup.py
MOCK=false            ← set to "true" if you want the mock API (no Daytona needed)
```

---

## Hour-by-Hour Plan

### Hour 0 (first 15 minutes — EVERYONE blocks on Person 1)

**Person 1:** Run `snapshot_setup.py`. Post the `DAYTONA_SNAPSHOT=...` value in the group chat the moment it prints.

```bash
cd backend
cp .env.example .env
# fill in DAYTONA_API_KEY in .env
cd ..
python snapshot_setup.py
```

**Person 2:** Get your Anthropic API key from console.anthropic.com, put it in `backend/.env`. Start coding `analyzer.py` immediately — you don't need the snapshot.

**Person 3:** Create the GitHub repo, clone it. Start the mock backend and build the frontend against it.

```bash
cd backend
cp .env.example .env
MOCK=true uvicorn main:app --reload --port 8000
# now open frontend/index.html in browser and start building UI
```

### Hours 1–2 (parallel work)

- **Person 1:** Build `scanner.py`. The scan must return `{before, after, clicked_reject, consent_platform, cookie_policy_url}`.
- **Person 2:** Build `analyzer.py`, `fixer.py`, `reporter.py`. Test each standalone.
- **Person 3:** Complete the full UI using mock data. The UI must handle all fields in `_mock_response()`.

### Hour 3 (integration — all meet)

Person 3 turns off mock mode in `main.py` (set `MOCK=false`) and does real imports. Run one full scan together on a simple site like bbc.com. Fix any import errors or data shape mismatches together.

### Hour 4 (deploy)

```bash
# Backend → Railway
cd backend
railway login && railway init && railway up
# set env vars in Railway dashboard (DAYTONA_API_KEY, ANTHROPIC_API_KEY, DAYTONA_SNAPSHOT)
# copy the Railway URL

# Update API_URL in frontend/index.html to point to your Railway URL

# Frontend → Vercel
cd ../frontend
vercel login && vercel --prod
```

### Hour 4.5 (demo dry run)

Run the full demo flow 3 times. Pick a reliable demo URL (bbc.com works well — it has OneTrust and several undeclared trackers).

---

## API Contract

`POST /scan` request body:
```json
{ "url": "https://bbc.com" }
```

Full response shape (see `_mock_response()` in `main.py` for reference):
```json
{
  "url": "...",
  "scan": { "clicked_reject": true, "consent_platform": "OneTrust", "before_count": 6, "after_count": 14, "violation_count": 9 },
  "violations": [ { "domain": "...", "declared": false, "category": "advertising", "data_collected": "..." } ],
  "undeclared": [ ... ],
  "declared": [ ... ],
  "fixes": { "policy_fix": "<p>...</p>", "banner_fix": "1. ...\n2. ..." },
  "verify": { "remaining_requests": [], "violation_count": 0, "clean": true },
  "exposure": { "violation_count": 3, "max_fine_percent": "4%...", "estimated_range_small": "€50k–€200k", "estimated_range_medium": "...", "estimated_range_large": "...", "relevant_authority": "..." },
  "complaint": "Dear Data Protection Authority,\n\n..."
}
```

---

## Testing Each Module Standalone

**Person 1 — scanner.py:**
```bash
cd backend && python scanner.py
# expects: json with before, after, clicked_reject, consent_platform
```

**Person 1 — tracker_db.py:**
```bash
cd backend && python tracker_db.py
# expects: "Total trackers: XXXX" and "Facebook: {category: advertising, ...}"
```

**Person 2 — analyzer.py:**
```bash
cd backend && python analyzer.py
# expects: "Found X tracker violations" then JSON analysis
```

**Person 2 — fixer.py:**
```bash
cd backend && python fixer.py
# expects: policy_fix HTML and banner_fix numbered steps
```

**Full backend (mock mode):**
```bash
cd backend && MOCK=true uvicorn main:app --reload --port 8000
curl -X POST http://localhost:8000/scan -H "Content-Type: application/json" -d '{"url":"test.com"}'
```

---

## Common Problems + Fixes

| Problem | Who | Fix |
|---------|-----|-----|
| Snapshot build fails | P1 | Check `DAYTONA_API_KEY` in `.env`, retry |
| Cookie banner not clicked | P1 | Add more selectors to `REJECT_SELECTORS` list in `scanner.py` |
| Claude returns invalid JSON | P2 | The regex fallback in `analyzer.py` and `fixer.py` handles this — if still broken, log `raw` and inspect |
| Frontend can't reach backend | P3 | Check `API_URL` constant at top of `index.html`, check CORS is enabled in `main.py` |
| Scan times out | P1 | Reduce `wait_for_timeout` values in Playwright script, lower timeout to 20s |
| Railway deploy fails | P3 | Check `requirements.txt` has every package, check `railway.toml` startCommand |
| `ModuleNotFoundError` on import | P3 | `cd backend` before running uvicorn so Python finds the local modules |

---

## Branching

```
main
├── p1/scanner    ← Person 1
├── p2/analysis   ← Person 2
└── p3/frontend   ← Person 3
```

Push every 30 minutes. Person 3 merges to main at Hour 4.

---

## Demo Script (practice this)

1. Open the Vercel URL
2. Type `bbc.com` → click Scan Now
3. Point to the red "Trackers After Reject" number — "Even after clicking reject, 9 trackers fired"
4. Show the violations table — "Facebook, Bing, Twitter — none declared in their cookie policy"
5. Show Fixes — "Here's exactly what they need to add to their policy, and how to fix their OneTrust config"
6. Show Exposure — "This is a €200k–€800k GDPR fine risk for a medium company"
7. Show Complaint Letter — "And here's the letter you send to the German data protection authority"

Total demo time: 90 seconds. That's the whole pitch.
