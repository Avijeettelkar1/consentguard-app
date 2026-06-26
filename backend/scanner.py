"""
Person 1 owns this file.
Launches a Daytona sandbox with the pre-built Playwright snapshot,
visits the target URL, clicks "Reject All" on the cookie banner,
and returns all network requests captured before and after consent.
"""
import os
import json
from daytona import Daytona, CreateSandboxFromSnapshotParams
from dotenv import load_dotenv
load_dotenv()

SNAPSHOT_ID = os.getenv("DAYTONA_SNAPSHOT")

PLAYWRIGHT_SCRIPT = """
import asyncio
import json
from playwright.async_api import async_playwright

REJECT_SELECTORS = [
    "button[id*='reject']", "button[id*='decline']", "button[id*='deny']",
    "button[class*='reject']", "button[class*='decline']",
    "a[id*='reject']", "a[class*='reject']",
    "[aria-label*='reject' i]", "[aria-label*='decline' i]",
    "button:has-text('Reject All')", "button:has-text('Reject all')",
    "button:has-text('Decline All')", "button:has-text('Decline all')",
    "button:has-text('Reject Cookies')", "button:has-text('No, thanks')",
    "button:has-text('Only necessary')", "button:has-text('Only Necessary')",
]

PLATFORM_SIGNALS = {
    "OneTrust": ["onetrust", "cookielaw.org"],
    "Cookiebot": ["cookiebot", "cookiebot.com"],
    "TrustArc": ["trustarc", "consent.truste.com"],
    "Didomi": ["didomi.io", "didomi"],
    "Quantcast": ["quantcast", "quantcast.mgr"],
    "Usercentrics": ["usercentrics"],
}

async def scan(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        before_requests = []
        after_requests = []
        consent_platform = None
        cookie_policy_url = None
        page_html = ""
        clicked_reject = False

        page.on("request", lambda req: before_requests.append(req.url))

        await page.goto(url, wait_until="networkidle", timeout=30000)
        page_html = await page.content()

        # detect consent platform
        for platform, signals in {
            "OneTrust": ["onetrust", "cookielaw.org"],
            "Cookiebot": ["cookiebot"],
            "TrustArc": ["trustarc", "truste.com"],
            "Didomi": ["didomi.io"],
            "Quantcast": ["quantcast"],
            "Usercentrics": ["usercentrics"],
        }.items():
            if any(s in page_html.lower() for s in signals):
                consent_platform = platform
                break

        # find cookie policy link
        for link in await page.query_selector_all("a"):
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).lower()
            if "cookie" in text or "privacy" in text:
                cookie_policy_url = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                break

        # snapshot requests before clicking reject
        before_snapshot = list(before_requests)

        # click reject
        for selector in {sels}:
            try:
                el = await page.wait_for_selector(selector, timeout=2000)
                if el:
                    await el.click()
                    clicked_reject = True
                    break
            except Exception:
                continue

        if not clicked_reject:
            # Claude fallback: ask the page to find reject button
            pass

        await page.wait_for_timeout(3000)

        # capture after requests
        page.on("request", lambda req: after_requests.append(req.url))
        await page.reload(wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        await browser.close()

        return json.dumps({
            "before": before_snapshot,
            "after": after_requests,
            "clicked_reject": clicked_reject,
            "consent_platform": consent_platform,
            "cookie_policy_url": cookie_policy_url,
            "page_html_for_fallback": page_html[:5000],
        })

asyncio.run(scan(TARGET_URL))
""".replace("{sels}", json.dumps(REJECT_SELECTORS))


def run_scan(url: str) -> dict:
    daytona = Daytona()
    sandbox = daytona.create(CreateSandboxFromSnapshotParams(snapshot_id=SNAPSHOT_ID))

    try:
        script = PLAYWRIGHT_SCRIPT.replace("TARGET_URL", json.dumps(url))
        result = sandbox.process.start_and_wait(
            f'python3 -c "{script}"',
            timeout=60,
        )
        output = result.result.strip()
        return json.loads(output)
    finally:
        sandbox.delete()


if __name__ == "__main__":
    result = run_scan("https://bbc.com")
    print(json.dumps(result, indent=2))
