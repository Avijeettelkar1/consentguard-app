"""Reject-All Radar - the autonomous compliance-raid agent.

Instead of scanning one URL, this points at a whole *industry*:

    [TAVILY]  find the real sites in the category        -> the agent's eyes
    [SCANNER] click Reject All, catch trackers firing    -> the ConsentGuard engine
    [OPENAI]  judge each site, reason out loud            -> the agent's brain
    [COGNEE]  remember patterns across every site         -> the agent's memory

Endpoints (wired into main.py):
    POST /raid/discover  {industry, limit}     -> list of sites Tavily found
    POST /raid           {industry, limit}     -> full graded board (blocks until done)
    GET  /raid/stream?industry=...&limit=...   -> SSE, one card per site as it lands

The heavy scan pipeline is imported lazily so the app still boots (and MOCK mode
still runs) without Playwright installed.
"""

from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/raid", tags=["raid"])

USE_MOCK = os.getenv("MOCK", "false").lower() == "true"
RAID_CONCURRENCY = int(os.getenv("RAID_CONCURRENCY", "4"))
COGNEE_ENABLED = os.getenv("COGNEE_ENABLED", "false").lower() == "true"


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class RaidRequest(BaseModel):
    industry: str = Field(..., min_length=2, max_length=120)
    limit: int = Field(8, ge=1, le=20)


# --------------------------------------------------------------------------- #
# 1) DISCOVERY  --  Tavily (partner tech): "find me the sites in this category"
# --------------------------------------------------------------------------- #
def discover_sites(industry: str, limit: int = 8) -> list[dict]:
    """Return [{"name", "url"}] of real sites in an industry.

    Uses Tavily when TAVILY_API_KEY is set, otherwise a small curated fallback so
    the demo works fully offline.
    """
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if key and not USE_MOCK:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=key)
            res = client.search(
                query=f"most popular {industry} websites homepages",
                max_results=max(limit * 2, 10),
            )
            sites: list[dict] = []
            seen: set[str] = set()
            for item in res.get("results", []):
                host = _root_host(item.get("url", ""))
                if not host or host in seen or _is_junk_host(host):
                    continue
                seen.add(host)
                sites.append({"name": host, "url": f"https://{host}"})
                if len(sites) >= limit:
                    break
            if sites:
                return sites
        except Exception:
            pass

    return _fallback_sites(industry, limit)


def _root_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_junk_host(host: str) -> bool:
    # Aggregators / search results that aren't a company's own property.
    junk = ("wikipedia.", "youtube.", "reddit.", "similarweb.", "google.", "facebook.")
    return any(host.startswith(j) or f".{j}" in host for j in junk)


def _fallback_sites(industry: str, limit: int) -> list[dict]:
    key = industry.lower()
    curated: dict[str, list[str]] = {
        "german news": ["spiegel.de", "bild.de", "zeit.de", "faz.net", "welt.de", "focus.de", "sueddeutsche.de", "tagesschau.de"],
        "news": ["bbc.com", "cnn.com", "theguardian.com", "reuters.com", "nytimes.com", "forbes.com", "aljazeera.com", "bloomberg.com"],
        "ecommerce": ["zalando.de", "otto.de", "aboutyou.com", "mediamarkt.de", "asos.com", "hm.com", "ikea.com", "notino.de"],
        "fashion": ["zalando.de", "aboutyou.com", "asos.com", "hm.com", "zara.com", "aboutyou.de", "boohoo.com", "shein.com"],
        "travel": ["booking.com", "expedia.com", "airbnb.com", "kayak.com", "lufthansa.com", "ryanair.com", "trivago.com", "skyscanner.net"],
    }
    for name, hosts in curated.items():
        if name in key or key in name:
            return [{"name": h, "url": f"https://{h}"} for h in hosts[:limit]]
    # Generic default so *any* input produces a runnable demo.
    default = curated["news"]
    return [{"name": h, "url": f"https://{h}"} for h in default[:limit]]


# --------------------------------------------------------------------------- #
# 2) SCAN ONE SITE  --  reuse the ConsentGuard engine, return a compact "card"
# --------------------------------------------------------------------------- #
def scan_one(url: str, auth: dict | None = None) -> dict:
    """Run the existing single-site pipeline and boil it down to a board card."""
    # Lazy imports: keep the app bootable without Playwright / in MOCK mode.
    from analyzer import analyze_violations, fetch_cookie_policy, find_violations
    from reporter import calculate_exposure
    from scanner import run_scan
    from tag_audit import audit_tags, filter_domain_violations_with_tag_audit

    scan_data = run_scan(url, auth)
    tag_audit = audit_tags(scan_data)
    tracker_hits = find_violations(scan_data.get("after", []))
    policy_text = fetch_cookie_policy(scan_data.get("cookie_policy_url"))
    analysis = analyze_violations(tracker_hits, policy_text, scan_data.get("page_html_for_fallback", ""))
    violations = filter_domain_violations_with_tag_audit(analysis["violations"], tag_audit)

    undeclared = [
        v for v in violations
        if not v.get("declared") and not v.get("needs_review")
    ]
    exposure = calculate_exposure(len(undeclared))

    return {
        "url": url,
        "name": _root_host(url) or url,
        "grade": grade_from_count(len(undeclared)),
        "undeclared_count": len(undeclared),
        "consent_platform": scan_data.get("consent_platform"),
        "clicked_reject": scan_data.get("clicked_reject", False),
        "top_trackers": [v["domain"] for v in undeclared[:5]],
        "undeclared": [
            {
                "domain": v["domain"],
                "company": v.get("company", ""),
                "category": v.get("category", ""),
                "reasoning": v.get("reasoning", ""),
            }
            for v in undeclared
        ],
        # first-person "AI reasons out loud" lines for the live ticker
        "reasoning_log": [v["reasoning"] for v in violations if v.get("reasoning")],
        "exposure": exposure,
        "error": None,
    }


def grade_from_count(undeclared: int) -> str:
    if undeclared <= 0:
        return "A"
    if undeclared == 1:
        return "C"
    if undeclared <= 3:
        return "D"
    return "F"


# --------------------------------------------------------------------------- #
# 3) CROSS-SITE MEMORY  --  Cognee hook (partner tech) + working local fallback
# --------------------------------------------------------------------------- #
def aggregate_patterns(cards: list[dict]) -> dict:
    """The headline finding: which tracker is illegally firing across the most
    sites. Local aggregation always works; Cognee augments it when enabled."""
    tracker_sites: dict[str, set[str]] = {}
    company_of: dict[str, str] = {}
    total_undeclared = 0
    graded = [c for c in cards if not c.get("error")]

    for card in graded:
        total_undeclared += card.get("undeclared_count", 0)
        for tr in card.get("undeclared", []):
            dom = tr["domain"]
            tracker_sites.setdefault(dom, set()).add(card["name"])
            if tr.get("company"):
                company_of.setdefault(dom, tr["company"])

    pervasive = sorted(
        tracker_sites.items(), key=lambda kv: len(kv[1]), reverse=True
    )
    most_pervasive = None
    if pervasive:
        dom, sites = pervasive[0]
        most_pervasive = {
            "domain": dom,
            "company": company_of.get(dom, ""),
            "sites_count": len(sites),
            "total_sites": len(graded),
            "sites": sorted(sites),
        }

    worst = max(graded, key=lambda c: c.get("undeclared_count", 0), default=None)

    patterns = {
        "total_sites": len(graded),
        "total_undeclared_trackers": total_undeclared,
        "failing_sites": sum(1 for c in graded if c.get("grade") in ("D", "F")),
        "most_pervasive_tracker": most_pervasive,
        "worst_offender": {"name": worst["name"], "grade": worst["grade"], "undeclared_count": worst["undeclared_count"]} if worst else None,
        "top_trackers": [
            {"domain": d, "company": company_of.get(d, ""), "sites_count": len(s)}
            for d, s in pervasive[:5]
        ],
    }

    if COGNEE_ENABLED:
        try:
            _remember_in_cognee(cards, patterns)
        except Exception:
            pass  # memory is a bonus; never break the raid on it.

    return patterns


def _remember_in_cognee(cards: list[dict], patterns: dict) -> None:
    """Persist findings into Cognee's memory graph so patterns compound across
    raids. Optional -- guarded by COGNEE_ENABLED. TODO(team): wire cognee.add /
    cognee.cognify / cognee.search here; the local aggregate above already ships
    the demo, so this is pure upside."""
    import cognee  # noqa: F401  (import guarded by caller)
    # Left as an integration point for the hackathon build.
    return None


def build_summary(cards: list[dict], patterns: dict) -> str:
    graded = [c for c in cards if not c.get("error")]
    failing = patterns.get("failing_sites", 0)
    mp = patterns.get("most_pervasive_tracker")
    if mp and mp["sites_count"] >= 2:
        who = mp["company"] or mp["domain"]
        return (
            f"{failing} of {len(graded)} sites are firing undeclared trackers after Reject All. "
            f"{who} alone is firing on {mp['sites_count']} of {mp['total_sites']} - "
            f"this isn't one bad site, it's an industry-wide pattern."
        )
    return f"{failing} of {len(graded)} sites are firing undeclared trackers after Reject All."


# --------------------------------------------------------------------------- #
# 4) ORCHESTRATION
# --------------------------------------------------------------------------- #
async def _scan_site_async(site: dict, auth: dict | None) -> dict:
    try:
        card = await asyncio.to_thread(scan_one, site["url"], auth)
        card["name"] = site.get("name") or card["name"]
        return card
    except Exception as exc:
        return {
            "url": site["url"],
            "name": site.get("name") or _root_host(site["url"]),
            "grade": "?",
            "undeclared_count": 0,
            "undeclared": [],
            "top_trackers": [],
            "reasoning_log": [],
            "exposure": None,
            "error": str(exc),
        }


async def run_raid(industry: str, limit: int = 8, auth: dict | None = None) -> dict:
    if USE_MOCK:
        return _mock_raid(industry)

    sites = discover_sites(industry, limit)
    sem = asyncio.Semaphore(RAID_CONCURRENCY)

    async def bounded(site: dict) -> dict:
        async with sem:
            return await _scan_site_async(site, auth)

    cards = await asyncio.gather(*[bounded(s) for s in sites])
    patterns = aggregate_patterns(cards)
    return {
        "industry": industry,
        "sites": cards,
        "patterns": patterns,
        "summary": build_summary(cards, patterns),
    }


# --------------------------------------------------------------------------- #
# 5) ENDPOINTS
# --------------------------------------------------------------------------- #
@router.post("/discover")
async def discover_endpoint(req: RaidRequest) -> dict:
    return {"industry": req.industry, "sites": discover_sites(req.industry, req.limit)}


@router.post("")
async def raid_endpoint(req: RaidRequest) -> dict:
    return await run_raid(req.industry, req.limit)


@router.get("/stream")
async def raid_stream_endpoint(industry: str, limit: int = 8) -> StreamingResponse:
    """Server-Sent Events: the board fills in live, one site at a time.
    This is the demo centerpiece - grades cascading in as each scan lands."""
    return StreamingResponse(_raid_event_generator(industry, limit), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _raid_event_generator(industry: str, limit: int):
    if USE_MOCK:
        board = _mock_raid(industry)
        yield _sse({"type": "discovered", "industry": industry,
                    "sites": [{"name": c["name"], "url": c["url"]} for c in board["sites"]]})
        for card in board["sites"]:
            await asyncio.sleep(0.6)  # let the UI animate each row landing
            yield _sse({"type": "site", "card": card})
        yield _sse({"type": "done", "patterns": board["patterns"], "summary": board["summary"]})
        return

    sites = discover_sites(industry, limit)
    yield _sse({"type": "discovered", "industry": industry, "sites": sites})

    sem = asyncio.Semaphore(RAID_CONCURRENCY)

    async def bounded(site: dict) -> dict:
        async with sem:
            return await _scan_site_async(site, None)

    tasks = [asyncio.create_task(bounded(s)) for s in sites]
    cards: list[dict] = []
    for coro in asyncio.as_completed(tasks):
        card = await coro
        cards.append(card)
        yield _sse({"type": "site", "card": card})

    patterns = aggregate_patterns(cards)
    yield _sse({"type": "done", "patterns": patterns, "summary": build_summary(cards, patterns)})


# --------------------------------------------------------------------------- #
# MOCK board -- instant, keyless, and safe for the live demo (pre-cache path)
# --------------------------------------------------------------------------- #
def _mock_raid(industry: str) -> dict:
    def card(name, grade, undecl, trackers, reasoning):
        return {
            "url": f"https://{name}",
            "name": name,
            "grade": grade,
            "undeclared_count": undecl,
            "consent_platform": "OneTrust",
            "clicked_reject": True,
            "top_trackers": [t[0] for t in trackers],
            "undeclared": [{"domain": d, "company": c, "category": cat, "reasoning": r} for d, c, cat, r in trackers],
            "reasoning_log": [r for *_, r in trackers] + [reasoning],
            "exposure": {"estimated_range_medium": "EUR 200,000-EUR 800,000"},
            "error": None,
        }

    sites = [
        card("spiegel.de", "F", 4,
             [("connect.facebook.net", "Meta", "advertising", "Policy names Google Analytics only, but the Meta Pixel fired after Reject - undeclared."),
              ("bat.bing.com", "Microsoft Advertising", "advertising", "Microsoft ad tracker fired after Reject and isn't in the policy."),
              ("ads-twitter.com", "X / Twitter", "advertising", "X ad pixel fired after Reject - not declared."),
              ("doubleclick.net", "Google", "advertising", "DoubleClick fired after Reject - not declared.")],
             "spiegel.de keeps 4 ad trackers alive after Reject All."),
        card("bild.de", "F", 5,
             [("doubleclick.net", "Google", "advertising", "DoubleClick fired after Reject - not declared."),
              ("connect.facebook.net", "Meta", "advertising", "Meta Pixel fired after Reject - undeclared."),
              ("adnxs.com", "Xandr", "advertising", "Xandr fired after Reject - not declared."),
              ("criteo.com", "Criteo", "advertising", "Criteo retargeting fired after Reject - undeclared."),
              ("bat.bing.com", "Microsoft Advertising", "advertising", "Bing ads fired after Reject - not declared.")],
             "bild.de is the worst offender - 5 undeclared ad trackers."),
        card("zeit.de", "D", 2,
             [("doubleclick.net", "Google", "advertising", "DoubleClick fired after Reject - not declared."),
              ("scorecardresearch.com", "Comscore", "analytics", "Comscore analytics fired after Reject - not declared.")],
             "zeit.de leaks 2 undeclared trackers."),
        card("faz.net", "D", 2,
             [("doubleclick.net", "Google", "advertising", "DoubleClick fired after Reject - not declared."),
              ("connect.facebook.net", "Meta", "advertising", "Meta Pixel fired after Reject - undeclared.")],
             "faz.net leaks 2 undeclared trackers."),
        card("tagesschau.de", "A", 0, [],
             "tagesschau.de blocked every non-essential tracker after Reject - compliant."),
    ]
    patterns = aggregate_patterns(sites)
    return {"industry": industry, "sites": sites, "patterns": patterns, "summary": build_summary(sites, patterns)}
