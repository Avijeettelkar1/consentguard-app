# ConsentGuard Compliance Gate

Block a release before it becomes a GDPR violation. This GitHub Action scans a
URL (your staging or preview deploy) and **fails the check if any undeclared
tracker fires after "Reject All."** Catch the breach in the pull request — not
in production.

## Usage

Add a workflow to your repo (see [`examples/compliance-gate.yml`](../examples/compliance-gate.yml)):

```yaml
name: Compliance gate
on: [pull_request]

jobs:
  gdpr:
    runs-on: ubuntu-latest
    steps:
      - name: ConsentGuard — cookie compliance
        uses: Avijeettelkar1/consentguard-app/gate@main
        with:
          url: https://staging.your-company.com
          api-url: https://api.your-consentguard.com     # your deployed ConsentGuard API
          # For a password-protected staging site:
          username: ${{ secrets.STAGING_USER }}
          password: ${{ secrets.STAGING_PASS }}
```

The step **fails the workflow** (red ❌ on the PR) when undeclared trackers are
found, and lists exactly which ones. It passes (green ✅) when the page is clean.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | yes | — | Page to scan (staging / preview URL). |
| `api-url` | no | `http://localhost:8000` | Your deployed ConsentGuard API base. |
| `username` / `password` | no | — | HTTP Basic auth for protected staging. |
| `header-name` / `header-value` | no | — | Custom header (e.g. a staging-bypass token). |
| `max-undeclared` | no | `0` | Allowed undeclared trackers before failing. |

## Run it locally

```bash
URL=bbc.com API_URL=http://localhost:8000 node gate/scan-gate.mjs
echo "exit code: $?"   # 0 = compliant, 1 = violations, 2 = couldn't run
```

> Note: `api-url` must be a ConsentGuard API reachable from the CI runner
> (i.e. a deployed instance), and the scanned `url` must be reachable from the
> runner too — public, or private with the credentials/header above.
