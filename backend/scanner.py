"""
Person 1 owns this file.

Two modes controlled by LOCAL_PLAYWRIGHT env var:
  LOCAL_PLAYWRIGHT=true  → runs Playwright directly on this machine (no Daytona)
  LOCAL_PLAYWRIGHT=false → spins up a Daytona cloud sandbox (production mode)

Local mode is used for development and testing against the test_site/.
"""
import os
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()

LOCAL_PLAYWRIGHT = os.getenv("LOCAL_PLAYWRIGHT", "false").lower() == "true"
SNAPSHOT_ID = os.getenv("DAYTONA_SNAPSHOT")

REJECT_SELECTORS = [
    # generic attribute patterns
    "button[id*='reject']", "button[id*='decline']", "button[id*='deny']",
    "button[class*='reject']", "button[class*='decline']",
    "a[id*='reject']", "a[class*='reject']",
    "[aria-label*='reject' i]", "[aria-label*='decline' i]",
    # text-based (covers most CMPs)
    "button:has-text('Reject All')", "button:has-text('Reject all')",
    "button:has-text('Decline All')", "button:has-text('Decline all')",
    "button:has-text('Reject Cookies')", "button:has-text('Reject cookies')",
    "button:has-text('No, thanks')", "button:has-text('No Thanks')",
    "button:has-text('Only necessary')", "button:has-text('Only Necessary')",
    "button:has-text('Only Required')", "button:has-text('Necessary Only')",
    "button:has-text('Continue without accepting')",
    "button:has-text('Continue without agreeing')",
    # SourcePoint (BBC, Guardian)
    "button[title*='Reject' i]", "button[title*='Decline' i]",
    "[data-sp-button='reject']",
    "button:has-text('Do not consent')", "button:has-text('Do Not Consent')",
    # Cookiebot
    "#CybotCookiebotDialogBodyButtonDecline",
    # OneTrust
    "#onetrust-reject-all-handler",
    # TrustArc
    ".call",
    # Didomi
    "#didomi-notice-disagree-button",
    # Quantcast
    ".qc-cmp2-summary-buttons button:last-child",
    # Usercentrics
    "[data-testid='uc-deny-all-button']",
]

PLATFORM_SIGNALS = {
    "OneTrust":       ["onetrust", "cookielaw.org"],
    "Cookiebot":      ["cookiebot"],
    "TrustArc":       ["trustarc", "truste.com"],
    "Didomi":         ["didomi.io"],
    "Quantcast":      ["quantcast"],
    "Usercentrics":   ["usercentrics"],
    "SourcePoint":    ["privacy-mgmt.com", "sourcepoint", "sp-cdn"],
    "Axeptio":        ["axeptio"],
    "CookieYes":      ["cookieyes", "cookie-law-info"],
    "Termly":         ["termly.io"],
    "Custom":       ["cookie-banner", "cookie_banner", "cookiebanner"],
}


async def _playwright_scan(url: str) -> dict:
    """Core Playwright scan logic — shared by both local and Daytona modes."""
    from playwright.async_api import async_playwright

    before_requests = []
    after_requests = []
    clicked_reject = False
    consent_platform = None
    cookie_policy_url = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("request", lambda req: before_requests.append(req.url))

        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page_html = await page.content()

        for platform, signals in PLATFORM_SIGNALS.items():
            if any(s in page_html.lower() for s in signals):
                consent_platform = platform
                break

        for link in await page.query_selector_all("a"):
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).lower()
            if "cookie" in text or "privacy" in text:
                if href.startswith("http"):
                    cookie_policy_url = href
                elif href.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    cookie_policy_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                break

        before_snapshot = list(before_requests)

        for selector in REJECT_SELECTORS:
            try:
                el = await page.wait_for_selector(selector, timeout=2000)
                if el:
                    await el.click()
                    clicked_reject = True
                    break
            except Exception:
                continue

        await page.wait_for_timeout(3000)

        page.on("request", lambda req: after_requests.append(req.url))
        await page.reload(wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)

        await browser.close()

    return {
        "before": before_snapshot,
        "after": after_requests,
        "clicked_reject": clicked_reject,
        "consent_platform": consent_platform,
        "cookie_policy_url": cookie_policy_url,
        "page_html_for_fallback": page_html[:5000],
    }


async def _run_local(url: str) -> dict:
    """Run Playwright directly on this machine — no Daytona needed."""
    print(f"[LOCAL] Scanning {url} with local Playwright...")
    return await _playwright_scan(url)


def _run_daytona(url: str) -> dict:
    """Run Playwright inside a Daytona cloud sandbox."""
    from daytona import Daytona, CreateSandboxFromSnapshotParams

    script_body = f"""
import asyncio, json
from playwright.async_api import async_playwright

REJECT_SELECTORS = {json.dumps(REJECT_SELECTORS)}

async def scan():
    before_requests = []
    after_requests = []
    clicked_reject = False
    consent_platform = None
    cookie_policy_url = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.on("request", lambda req: before_requests.append(req.url))
        await page.goto({json.dumps(url)}, wait_until="domcontentloaded", timeout=45000)
        page_html = await page.content()

        platform_signals = {{
            "OneTrust": ["onetrust", "cookielaw.org"],
            "Cookiebot": ["cookiebot"],
            "TrustArc": ["trustarc"],
            "Didomi": ["didomi.io"],
            "Custom": ["cookie-banner"],
        }}
        for platform, signals in platform_signals.items():
            if any(s in page_html.lower() for s in signals):
                consent_platform = platform
                break

        for link in await page.query_selector_all("a"):
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).lower()
            if "cookie" in text or "privacy" in text:
                cookie_policy_url = href if href.startswith("http") else {json.dumps(url)}.rstrip("/") + "/" + href.lstrip("/")
                break

        before_snapshot = list(before_requests)

        for selector in REJECT_SELECTORS:
            try:
                el = await page.wait_for_selector(selector, timeout=2000)
                if el:
                    await el.click()
                    clicked_reject = True
                    break
            except Exception:
                continue

        await page.wait_for_timeout(3000)
        page.on("request", lambda req: after_requests.append(req.url))
        await page.reload(wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        await browser.close()

    print(json.dumps({{
        "before": before_snapshot,
        "after": after_requests,
        "clicked_reject": clicked_reject,
        "consent_platform": consent_platform,
        "cookie_policy_url": cookie_policy_url,
        "page_html_for_fallback": page_html[:5000],
    }}))

asyncio.run(scan())
"""
    daytona = Daytona()
    sandbox = daytona.create(CreateSandboxFromSnapshotParams(snapshot_id=SNAPSHOT_ID))
    try:
        result = sandbox.process.start_and_wait(
            f"python3 -c {json.dumps(script_body)}",
            timeout=90,
        )
        return json.loads(result.result.strip())
    finally:
        sandbox.delete()


async def run_scan(url: str) -> dict:
    if LOCAL_PLAYWRIGHT:
        return await _run_local(url)
    return _run_daytona(url)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    result = asyncio.run(run_scan(target))
    print(json.dumps(result, indent=2))
