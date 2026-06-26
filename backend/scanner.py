import base64
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

SNAPSHOT_ID = os.getenv("DAYTONA_SNAPSHOT", "").strip()
DAYTONA_API_KEY = os.getenv("DAYTONA_API_KEY", "").strip()

ACCEPT_SELECTORS = [
    "input#__framer-cookie-component-button-accept",
    "input[value='Accept All']",
    "input[id*='accept' i]",
    "input[class*='accept' i]",
    "a.c24-cookie-consent-button:has-text('Geht klar')",
    "a:has-text('Geht klar')",
    "button:has-text('Accept All')",
    "button:has-text('Accept all')",
    "button:has-text('Allow All')",
    "button:has-text('Allow all')",
    "button:has-text('I agree')",
    "button:has-text('Yes, I agree')",
    "button:has-text('Alle akzeptieren')",
    "button:has-text('Akzeptieren')",
    "button:has-text('Zustimmen')",
    "a:has-text('Accept All')",
    "a:has-text('Accept all')",
    "a:has-text('Allow All')",
    "a:has-text('I agree')",
    "a:has-text('Yes, I agree')",
    "a:has-text('Alle akzeptieren')",
    "a:has-text('Akzeptieren')",
    "a:has-text('Zustimmen')",
    "[role='button']:has-text('Accept All')",
    "[role='button']:has-text('Alle akzeptieren')",
    "[role='button']:has-text('Geht klar')",
    "button[id*='accept' i]",
    "button[class*='accept' i]",
    "a[id*='accept' i]",
    "a[class*='accept' i]",
    "[aria-label*='accept' i]",
]

REJECT_SELECTORS = [
    "input#__framer-cookie-component-button-reject",
    "input[value='Reject All']",
    "input[id*='reject' i]",
    "input[id*='decline' i]",
    "input[class*='reject' i]",
    "input[class*='decline' i]",
    "a.c24-cookie-consent-functional",
    "button[id*='reject' i]",
    "button[id*='decline' i]",
    "button[id*='deny' i]",
    "button[id*='ablehn' i]",
    "button[class*='reject' i]",
    "button[class*='decline' i]",
    "button[class*='ablehn' i]",
    "a[id*='reject' i]",
    "a[id*='ablehn' i]",
    "a[class*='reject' i]",
    "a[class*='ablehn' i]",
    "[aria-label*='reject' i]",
    "[aria-label*='decline' i]",
    "[aria-label*='ablehn' i]",
    "button:has-text('Reject All')",
    "button:has-text('Reject all')",
    "button:has-text('Decline All')",
    "button:has-text('Decline all')",
    "button:has-text('Reject Cookies')",
    "button:has-text('I do not agree')",
    "button:has-text('Do not agree')",
    "button:has-text('Only necessary')",
    "button:has-text('No, thanks')",
    "button:has-text('Alle ablehnen')",
    "button:has-text('Ablehnen')",
    "button:has-text('Nur notwendige Cookies')",
    "button:has-text('Nur erforderliche Cookies')",
    "button:has-text('Nur essenzielle Cookies')",
    "a:has-text('Alle ablehnen')",
    "a:has-text('I do not agree')",
    "a:has-text('Do not agree')",
    "a:has-text('Ablehnen')",
    "a:has-text('Nur notwendige Cookies')",
    "a:has-text('Nur erforderliche Cookies')",
    "a:has-text('Nur essenzielle Cookies')",
    "[role='button']:has-text('Alle ablehnen')",
    "[role='button']:has-text('Ablehnen')",
    "[role='button']:has-text('Nur notwendige Cookies')",
]

PLATFORM_SIGNALS = {
    "Sourcepoint": ["privacy-mgmt.com", "sp_choice_type"],
    "CHECK24 Cookie Consent": ["c24-cookie-consent"],
    "OneTrust": ["onetrust", "cookielaw.org"],
    "Cookiebot": ["cookiebot"],
    "TrustArc": ["trustarc", "truste.com"],
    "Didomi": ["didomi.io", "didomi"],
    "Quantcast": ["quantcast"],
    "Usercentrics": ["usercentrics"],
}

PLAYWRIGHT_SCRIPT = r"""
import asyncio
import json
from urllib.parse import urljoin
from playwright.async_api import async_playwright

TARGET_URL = __TARGET_URL__
ACCEPT_SELECTORS = __ACCEPT_SELECTORS__
REJECT_SELECTORS = __REJECT_SELECTORS__
PLATFORM_SIGNALS = __PLATFORM_SIGNALS__

async def find_cookie_policy_url(page, base_url):
    for link in await page.query_selector_all("a"):
        try:
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).lower()
        except Exception:
            continue
        if href and ("cookie" in text or "privacy" in text or "cookie" in href.lower()):
            return urljoin(base_url, href)
    return None

def detect_platform(html):
    lower_html = html.lower()
    for platform, signals in PLATFORM_SIGNALS.items():
        if any(signal in lower_html for signal in signals):
            return platform
    return None

def sanitize_cookies(cookies):
    return [{
        "name": c.get("name"),
        "domain": c.get("domain"),
        "path": c.get("path"),
        "expires": c.get("expires"),
        "httpOnly": c.get("httpOnly"),
        "secure": c.get("secure"),
        "sameSite": c.get("sameSite"),
    } for c in cookies]

def score_candidate(text, element_id, class_name, action):
    haystack = " ".join([text or "", element_id or "", class_name or ""]).lower()
    normalized = " ".join(haystack.split())
    reject_phrases = [
        "i do not agree", "do not agree", "reject all", "reject", "decline all", "decline",
        "deny", "only necessary", "necessary only", "alle ablehnen", "ablehnen",
        "nur notwendige cookies", "nur erforderliche cookies", "nur essenzielle cookies",
        "opt out", "do not sell", "do not share"
    ]
    accept_phrases = [
        "yes, i agree", "i agree", "accept all", "accept", "allow all", "allow",
        "agree", "alle akzeptieren", "akzeptieren", "zustimmen", "geht klar"
    ]
    settings_phrases = ["settings", "manage options", "preferences", "customize", "anpassen"]

    if action == "reject":
        for index, phrase in enumerate(reject_phrases):
            if phrase in normalized:
                return 100 - index
        if any(phrase in normalized for phrase in settings_phrases):
            return 5
        return 0

    if any(phrase in normalized for phrase in reject_phrases):
        return 0
    for index, phrase in enumerate(accept_phrases):
        if phrase in normalized:
            return 100 - index
    return 0

async def click_first(page, action, selectors):
    deadline = asyncio.get_running_loop().time() + 10
    while asyncio.get_running_loop().time() < deadline:
        for selector in selectors:
            for frame in page.frames:
                try:
                    locator = frame.locator(selector).first
                    if await locator.count() and await locator.is_visible():
                        await locator.click(timeout=3000)
                        return {"clicked": True, "selector": selector}
                except Exception:
                    continue

        best = None
        for frame in page.frames:
            try:
                locator = frame.locator("button, a, input, [role='button']")
                count = min(await locator.count(), 150)
                for index in range(count):
                    item = locator.nth(index)
                    if not await item.is_visible():
                        continue
                    text = (
                        await item.inner_text(timeout=500)
                        if await item.evaluate("(e) => e.tagName !== 'INPUT'")
                        else ""
                    )
                    value = await item.get_attribute("value") or ""
                    aria = await item.get_attribute("aria-label") or ""
                    element_id = await item.get_attribute("id") or ""
                    class_name = await item.get_attribute("class") or ""
                    candidate_text = " ".join([text, value, aria]).strip()
                    score = score_candidate(candidate_text, element_id, class_name, action)
                    if score and (best is None or score > best["score"]):
                        best = {"score": score, "locator": item, "text": candidate_text}
            except Exception:
                continue
        if best:
            await best["locator"].click(timeout=3000)
            return {"clicked": True, "selector": f"dynamic:{best['text'][:80]}"}
        await page.wait_for_timeout(250)
    return {"clicked": False, "selector": None}

async def scan_branch(browser, url, action, selectors):
    context = await browser.new_context(ignore_https_errors=True, locale="de-DE")
    page = await context.new_page()
    initial_requests = []
    post_consent_requests = []
    initial_request_records = []
    post_consent_request_records = []

    def make_record(req):
        try:
            post_data = req.post_data or ""
        except Exception:
            post_data = ""
        return {
            "url": req.url,
            "method": req.method,
            "resource_type": req.resource_type,
            "post_data": post_data[:2000],
        }

    def on_initial_request(req):
        initial_requests.append(req.url)
        initial_request_records.append(make_record(req))

    def on_post_consent_request(req):
        post_consent_requests.append(req.url)
        post_consent_request_records.append(make_record(req))

    page.on("request", on_initial_request)

    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)

    page_html = await page.content()
    click = await click_first(page, action, selectors)
    await page.wait_for_timeout(2000)

    page.remove_listener("request", on_initial_request)
    page.on("request", on_post_consent_request)
    try:
        await page.reload(wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
    except Exception:
        pass

    cookies = sanitize_cookies(await context.cookies())
    await context.close()
    return {
        "action": action,
        "clicked": click["clicked"],
        "clicked_selector": click["selector"],
        "initial_requests": list(dict.fromkeys(initial_requests)),
        "post_consent_requests": list(dict.fromkeys(post_consent_requests)),
        "initial_request_records": dedupe_records(initial_request_records),
        "post_consent_request_records": dedupe_records(post_consent_request_records),
        "cookies": cookies,
        "consent_platform": detect_platform(page_html),
        "cookie_policy_url": await find_cookie_policy_url(page, url) if False else None,
        "page_html_for_fallback": page_html[:8000],
    }

def cookie_key(cookie):
    return f"{cookie.get('domain', '')}|{cookie.get('name', '')}"

def dedupe_records(records):
    seen = set()
    unique = []
    for record in records:
        key = (record.get("method"), record.get("url"), record.get("post_data"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique

def compare(accept, reject):
    accept_requests = set(accept["post_consent_requests"])
    reject_requests = set(reject["post_consent_requests"])
    accept_cookies = {cookie_key(c) for c in accept["cookies"]}
    reject_cookies = {cookie_key(c) for c in reject["cookies"]}
    return {
        "accept_only_requests": sorted(accept_requests - reject_requests),
        "reject_only_requests": sorted(reject_requests - accept_requests),
        "common_requests": sorted(accept_requests & reject_requests),
        "accept_only_cookies": sorted(accept_cookies - reject_cookies),
        "reject_only_cookies": sorted(reject_cookies - accept_cookies),
        "common_cookies": sorted(accept_cookies & reject_cookies),
    }

async def scan(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        accept = await scan_branch(browser, url, "accept", ACCEPT_SELECTORS)
        reject = await scan_branch(browser, url, "reject", REJECT_SELECTORS)
        await browser.close()
        return {
            "before": reject["initial_requests"],
            "after": reject["post_consent_requests"],
            "clicked_accept": accept["clicked"],
            "clicked_reject": reject["clicked"],
            "accept": accept,
            "reject": reject,
            "comparison": compare(accept, reject),
            "consent_platform": reject["consent_platform"] or accept["consent_platform"],
            "cookie_policy_url": reject["cookie_policy_url"] or accept["cookie_policy_url"],
            "page_html_for_fallback": reject["page_html_for_fallback"] or accept["page_html_for_fallback"],
            "scanner": "playwright",
        }

print(json.dumps(asyncio.run(scan(TARGET_URL))))
"""


def run_scan(url: str) -> dict:
    if SNAPSHOT_ID and DAYTONA_API_KEY:
        try:
            return _run_daytona_scan(url)
        except Exception as exc:
            fallback = _run_http_scan(url)
            fallback["scanner_error"] = f"Daytona scan failed: {exc}"
            return fallback

    try:
        return _run_local_playwright_scan(url)
    except Exception as exc:
        fallback = _run_http_scan(url)
        fallback["scanner_error"] = f"Playwright unavailable: {exc}"
        return fallback


def _render_playwright_script(url: str) -> str:
    return (
        PLAYWRIGHT_SCRIPT
        .replace("__TARGET_URL__", json.dumps(url))
        .replace("__ACCEPT_SELECTORS__", json.dumps(ACCEPT_SELECTORS))
        .replace("__REJECT_SELECTORS__", json.dumps(REJECT_SELECTORS))
        .replace("__PLATFORM_SIGNALS__", json.dumps(PLATFORM_SIGNALS))
    )


def _run_daytona_scan(url: str) -> dict:
    from daytona import CreateSandboxFromSnapshotParams, Daytona

    daytona = Daytona()
    sandbox = daytona.create(CreateSandboxFromSnapshotParams(snapshot_id=SNAPSHOT_ID))
    try:
        script = _render_playwright_script(url)
        encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
        command = f"python3 -c \"import base64; exec(base64.b64decode('{encoded}'))\""
        result = sandbox.process.start_and_wait(command, timeout=100)
        return json.loads((result.result or "").strip())
    finally:
        sandbox.delete()


def _run_local_playwright_scan(url: str) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        accept = _scan_branch(browser, url, "accept", ACCEPT_SELECTORS)
        reject = _scan_branch(browser, url, "reject", REJECT_SELECTORS)
        browser.close()

    return {
        "before": reject["initial_requests"],
        "after": reject["post_consent_requests"],
        "clicked_accept": accept["clicked"],
        "clicked_reject": reject["clicked"],
        "accept": accept,
        "reject": reject,
        "comparison": _compare_scan_branches(accept, reject),
        "consent_platform": reject["consent_platform"] or accept["consent_platform"],
        "cookie_policy_url": reject["cookie_policy_url"] or accept["cookie_policy_url"],
        "page_html_for_fallback": reject["page_html_for_fallback"] or accept["page_html_for_fallback"],
        "scanner": "local_playwright",
    }


def _scan_branch(browser, url: str, action: str, selectors: list[str]) -> dict:
    context = browser.new_context(ignore_https_errors=True, locale="de-DE")
    page = context.new_page()
    initial_requests = []
    post_consent_requests = []
    initial_request_records = []
    post_consent_request_records = []

    def make_record(req):
        try:
            post_data = req.post_data or ""
        except Exception:
            post_data = ""
        return {
            "url": req.url,
            "method": req.method,
            "resource_type": req.resource_type,
            "post_data": post_data[:2000],
        }

    def on_initial_request(req):
        initial_requests.append(req.url)
        initial_request_records.append(make_record(req))

    def on_post_consent_request(req):
        post_consent_requests.append(req.url)
        post_consent_request_records.append(make_record(req))

    page.on("request", on_initial_request)

    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(1500)

    page_html = page.content()
    consent_platform = _detect_platform(page_html)
    cookie_policy_url = _find_policy_url(page_html, url)
    click_result = _click_first(page, action, selectors)
    page.wait_for_timeout(2000)

    page.remove_listener("request", on_initial_request)
    page.on("request", on_post_consent_request)
    try:
        page.reload(wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
    except Exception:
        pass

    cookies = _sanitize_cookies(context.cookies())
    context.close()
    return {
        "action": action,
        "clicked": click_result["clicked"],
        "clicked_selector": click_result["selector"],
        "initial_requests": list(dict.fromkeys(initial_requests)),
        "post_consent_requests": list(dict.fromkeys(post_consent_requests)),
        "initial_request_records": _dedupe_records(initial_request_records),
        "post_consent_request_records": _dedupe_records(post_consent_request_records),
        "cookies": cookies,
        "consent_platform": consent_platform,
        "cookie_policy_url": cookie_policy_url,
        "page_html_for_fallback": page_html[:8000],
    }


def _score_candidate(text: str, element_id: str, class_name: str, action: str) -> int:
    haystack = " ".join([text or "", element_id or "", class_name or ""]).lower()
    normalized = " ".join(haystack.split())
    reject_phrases = [
        "i do not agree",
        "do not agree",
        "reject all",
        "reject",
        "decline all",
        "decline",
        "deny",
        "only necessary",
        "necessary only",
        "alle ablehnen",
        "ablehnen",
        "nur notwendige cookies",
        "nur erforderliche cookies",
        "nur essenzielle cookies",
        "opt out",
        "do not sell",
        "do not share",
    ]
    accept_phrases = [
        "yes, i agree",
        "i agree",
        "accept all",
        "accept",
        "allow all",
        "allow",
        "agree",
        "alle akzeptieren",
        "akzeptieren",
        "zustimmen",
        "geht klar",
    ]
    settings_phrases = ["settings", "manage options", "preferences", "customize", "anpassen"]

    if action == "reject":
        for index, phrase in enumerate(reject_phrases):
            if phrase in normalized:
                return 100 - index
        if any(phrase in normalized for phrase in settings_phrases):
            return 5
        return 0

    if any(phrase in normalized for phrase in reject_phrases):
        return 0
    for index, phrase in enumerate(accept_phrases):
        if phrase in normalized:
            return 100 - index
    return 0


def _click_first(page, action: str, selectors: list[str]) -> dict:
    deadline = time.time() + 10
    while time.time() < deadline:
        for selector in selectors:
            for frame in page.frames:
                try:
                    locator = frame.locator(selector).first
                    if locator.count() and locator.is_visible():
                        locator.click(timeout=3000)
                        return {"clicked": True, "selector": selector}
                except Exception:
                    continue

        best = None
        for frame in page.frames:
            try:
                locator = frame.locator("button, a, input, [role='button']")
                count = min(locator.count(), 150)
                for index in range(count):
                    item = locator.nth(index)
                    if not item.is_visible():
                        continue
                    tag_name = item.evaluate("(e) => e.tagName")
                    text = "" if tag_name == "INPUT" else item.inner_text(timeout=500)
                    value = item.get_attribute("value") or ""
                    aria = item.get_attribute("aria-label") or ""
                    element_id = item.get_attribute("id") or ""
                    class_name = item.get_attribute("class") or ""
                    candidate_text = " ".join([text, value, aria]).strip()
                    score = _score_candidate(candidate_text, element_id, class_name, action)
                    if score and (best is None or score > best["score"]):
                        best = {"score": score, "locator": item, "text": candidate_text}
            except Exception:
                continue
        if best:
            best["locator"].click(timeout=3000)
            return {"clicked": True, "selector": f"dynamic:{best['text'][:80]}"}
        page.wait_for_timeout(250)
    return {"clicked": False, "selector": None}


def _sanitize_cookies(cookies: list[dict]) -> list[dict]:
    return [
        {
            "name": cookie.get("name"),
            "domain": cookie.get("domain"),
            "path": cookie.get("path"),
            "expires": cookie.get("expires"),
            "httpOnly": cookie.get("httpOnly"),
            "secure": cookie.get("secure"),
            "sameSite": cookie.get("sameSite"),
        }
        for cookie in cookies
    ]


def _cookie_key(cookie: dict) -> str:
    return f"{cookie.get('domain', '')}|{cookie.get('name', '')}"


def _dedupe_records(records: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for record in records:
        key = (record.get("method"), record.get("url"), record.get("post_data"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def _compare_scan_branches(accept: dict, reject: dict) -> dict:
    accept_requests = set(accept.get("post_consent_requests", []))
    reject_requests = set(reject.get("post_consent_requests", []))
    accept_cookies = {_cookie_key(cookie) for cookie in accept.get("cookies", [])}
    reject_cookies = {_cookie_key(cookie) for cookie in reject.get("cookies", [])}
    return {
        "accept_only_requests": sorted(accept_requests - reject_requests),
        "reject_only_requests": sorted(reject_requests - accept_requests),
        "common_requests": sorted(accept_requests & reject_requests),
        "accept_only_cookies": sorted(accept_cookies - reject_cookies),
        "reject_only_cookies": sorted(reject_cookies - accept_cookies),
        "common_cookies": sorted(accept_cookies & reject_cookies),
    }


def _run_http_scan(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        html = response.text or ""
        final_url = response.url or url
    except Exception as exc:
        return _empty_fallback(url, str(exc))

    requests_seen = [final_url]
    requests_seen.extend(_extract_asset_urls(html, final_url))
    unique_requests = list(dict.fromkeys(requests_seen))
    common_branch = {
        "clicked": False,
        "clicked_selector": None,
        "initial_requests": unique_requests,
        "post_consent_requests": unique_requests,
        "initial_request_records": [{"url": request_url, "method": "GET", "resource_type": "unknown", "post_data": ""} for request_url in unique_requests],
        "post_consent_request_records": [{"url": request_url, "method": "GET", "resource_type": "unknown", "post_data": ""} for request_url in unique_requests],
        "cookies": [],
        "consent_platform": _detect_platform(html),
        "cookie_policy_url": _find_policy_url(html, final_url),
        "page_html_for_fallback": html[:8000],
    }
    return {
        "before": unique_requests,
        "after": unique_requests,
        "clicked_accept": False,
        "clicked_reject": _has_reject_button(html),
        "accept": {"action": "accept", **common_branch},
        "reject": {"action": "reject", **common_branch, "clicked": _has_reject_button(html)},
        "comparison": {
            "accept_only_requests": [],
            "reject_only_requests": [],
            "common_requests": unique_requests,
            "accept_only_cookies": [],
            "reject_only_cookies": [],
            "common_cookies": [],
        },
        "consent_platform": _detect_platform(html),
        "cookie_policy_url": _find_policy_url(html, final_url),
        "page_html_for_fallback": html[:8000],
        "scanner": "http_fallback",
    }


def _empty_fallback(url: str, error: str) -> dict:
    return {
        "before": [url],
        "after": [],
        "clicked_accept": False,
        "clicked_reject": False,
        "accept": {"action": "accept", "clicked": False, "clicked_selector": None, "initial_requests": [url], "post_consent_requests": [], "initial_request_records": [], "post_consent_request_records": [], "cookies": []},
        "reject": {"action": "reject", "clicked": False, "clicked_selector": None, "initial_requests": [url], "post_consent_requests": [], "initial_request_records": [], "post_consent_request_records": [], "cookies": []},
        "comparison": {"accept_only_requests": [], "reject_only_requests": [], "common_requests": [], "accept_only_cookies": [], "reject_only_cookies": [], "common_cookies": []},
        "consent_platform": None,
        "cookie_policy_url": None,
        "page_html_for_fallback": "",
        "scanner": "http_fallback",
        "scanner_error": error,
    }


def _extract_asset_urls(html: str, base_url: str) -> list[str]:
    urls = []
    patterns = [
        r"""(?:src|href)=["']([^"']+)["']""",
        r"""https?://[^\s"'<>]+""",
    ]
    for pattern in patterns:
        for value in re.findall(pattern, html, flags=re.IGNORECASE):
            if value.startswith(("data:", "mailto:", "tel:", "#")):
                continue
            absolute = urljoin(base_url, value)
            if urlparse(absolute).scheme in {"http", "https"}:
                urls.append(absolute)
    return urls[:300]


def _find_policy_url(html: str, base_url: str) -> str | None:
    link_pattern = re.compile(r"""<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""", re.I | re.S)
    for href, text in link_pattern.findall(html):
        cleaned = re.sub(r"<[^>]+>", " ", text).lower()
        href_lower = href.lower()
        if "cookie" in cleaned or "privacy" in cleaned or "cookie" in href_lower:
            return urljoin(base_url, href)
    return None


def _detect_platform(html: str) -> str | None:
    lower_html = html.lower()
    for platform, markers in PLATFORM_SIGNALS.items():
        if any(marker in lower_html for marker in markers):
            return platform
    return None


def _has_reject_button(html: str) -> bool:
    lowered = re.sub(r"\s+", " ", html.lower())
    return any(
        phrase in lowered
        for phrase in [
            "reject all",
            "decline all",
            "reject cookies",
            "only necessary",
            "no, thanks",
            "alle ablehnen",
            "nur notwendige cookies",
        ]
    )


if __name__ == "__main__":
    print(json.dumps(run_scan("https://www.check24.de/"), indent=2))
