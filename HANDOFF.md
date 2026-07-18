# ConsentGuard — Handoff / Full Context

> **New chat? Start here.** Tell Claude: *"Read HANDOFF.md in C:\Users\ASUS\Desktop\consentguard and continue."*
> This file is the single source of truth for the project's current state.

## What it is
**ConsentGuard** — a GDPR cookie-compliance scanner. It opens a website in a real
headless browser, clicks **"Reject All,"** and records every tracker that fires
**anyway** (a GDPR violation). It then grades the site, estimates the fine, writes
the policy fix, and drafts a DPA complaint letter.

- **Stack:** Frontend = React + Vite (`frontend/`). Backend = FastAPI (`backend/`).
- **Location:** `C:\Users\ASUS\Desktop\consentguard`
- **Repos:** `origin` → github.com/Avijeettelkar1/consentguard (branch `avjeet-frontend`).
  `cgapp` → github.com/Avijeettelkar1/**consentguard-app** (branch `main`, **CI passing**).

## How to run it
```bash
# Backend (from backend/) — LIVE mode = real browser scans, no API keys needed:
python -m uvicorn main:app --host 127.0.0.1 --port 8000
#   prereqs: pip install -r requirements.txt  &&  python -m playwright install chromium
#   set MOCK=true for a keyless/offline fixed-demo mode.

# Frontend (from frontend/):
npx vite --port 5180 --strictPort        # prereq: npm install
```
Demo account: **demo@consentguard.io / supersecret1**. Open http://localhost:5180.
(The Claude preview MCP tool is bound to a different project's port 5173, so run
vite manually as above; to inspect via the preview browser, navigate it to :5180.)

## Design system (wispr-flow-inspired)
Light theme. **Brand = blue** `--brand #2563EB` (pill buttons w/ glow). **Rose** =
violations, **emerald** = pass/compliant. Fonts: **Plus Jakarta Sans** (display,
weight 800), Manrope (body), JetBrains Mono (technical). 16px radius, floating
cards, soft gradient washes. All tokens in `frontend/src/index.css` (kept stable
so every component themes from them).

## What's built (all working + verified)
**Scanner** (`backend/scanner.py`, `analyzer/fixer/reporter/cookie_risk/tag_audit`)
- Real local Playwright scan (Daytona cloud is optional, off; only used if
  `DAYTONA_API_KEY`+`DAYTONA_SNAPSHOT` set). HTTP fallback below that.
- Rule-based analysis (Claude only if `ANTHROPIC_API_KEY` set — currently the
  keyless "without-claude-api" path). Disconnect.me DB = ~6,326 tracker domains.
- **Scan behind a login:** optional Basic-auth (`username`/`password`) or custom
  header (`header_name`/`header_value`) threaded into the browser context — scans
  private/staging sites. Per-scan, not stored.
- **Auth-wall detection:** a 401 returns `{auth_required, notice}` → UI says
  "this site needs a login" instead of a false "compliant".
- Reachability pre-check rejects non-existent domains and picks the working scheme.

**Auth** (`backend/auth.py`) — SQLite users, pbkdf2 hashing, PyJWT. `/auth/signup`,
`/auth/login`, `/auth/me`. Frontend: `src/lib/AuthContext.jsx`, react-router,
protected `/dashboard`, Login/Signup (`src/pages/`).

**Dashboard** (`src/pages/Dashboard.jsx`) — Scan tab: run scan → graded report with
animated **ScoreGauge** (A–F), **scan history** (`backend/scans.py`, per-user CRUD),
KPI cards. Results page (`src/components/Results.jsx`) shows verdict, fine exposure
(only on real violations — "No exposure" when compliant), violations table, and
collapsible fixes + DPA complaint.

**Watchtower** (`backend/watch.py`) — continuous monitoring. Add domains → a
background asyncio scheduler re-scans on interval, diffs vs previous run, raises
**regression/improved alerts**. Frontend `src/components/Watchtower.jsx`: live board
(status dots, score sparklines, deltas, scan-now), polls every 9s. Env:
`WATCH_POLL_SECONDS` (30), `WATCH_INTERVAL_HOURS` (12), `WATCH_MAX` (25).

**Notifications** (`backend/notify.py`) — Slack/Teams/webhook alerts on Watchtower
regressions (`{text}` for Slack/Teams, JSON otherwise). Settings + "Send test" in the
Watchtower tab.

**CI/CD compliance gate** (`gate/`) — `scan-gate.mjs` + `action.yml` GitHub Action
(`uses: Avijeettelkar1/consentguard-app/gate@main`) that **fails a build** if a
URL fires undeclared trackers. Example in `examples/compliance-gate.yml`. Verified:
clean site → exit 0, dirty site → exit 1 with tracker list.

**CI** (`.github/workflows/ci.yml`) — frontend `npm ci`+build, backend
`pip install`+`compileall`+`pytest` (14 tests, MOCK mode). Green on consentguard-app.

## Honest gaps / next steps
- **Not deployed** — runs locally; a public URL is the highest-leverage next step
  (needed for the CI gate and for demos). Frontend `api.js` points to localhost.
- **No billing** — pricing tiers (Free / €79 / €440) are UI-only.
- **No paying customers / real testimonials** (site ones are placeholder).
- **Scale:** each real scan is ~30–60s, one at a time.
- **Watchtower behind a login** would need encrypted credential storage (not built).
- **Hackathon idea (honest path):** it's an AI hackathon (Mistral/Weaviate/Luma
  sponsors). To make it AI-forward, add a **Mistral** analysis path and **Weaviate**
  semantic tracker↔policy matching. Not started.

## Working style / preferences
Prefer real verification over claims (build passes, endpoints tested). Keep the
light/blue design system. Be direct and honest, including pushback.
