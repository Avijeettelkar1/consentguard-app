"""
Person 3 owns this file.
FastAPI application — starts as MOCK, replace with real imports at Hour 3.
Run: uvicorn main:app --reload --port 8000
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

# ── Toggle: set MOCK=true in .env to use mock data ──────────────────────────
USE_MOCK = os.getenv("MOCK", "false").lower() == "true"

app = FastAPI(title="ConsentGuard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    url: str


# ── Real imports (uncomment at Hour 3 when P1 and P2 are done) ──────────────
if not USE_MOCK:
    from scanner import run_scan
    from tracker_db import get_tracker_domains
    from analyzer import find_violations, fetch_cookie_policy, analyze_violations
    from fixer import generate_fixes
    from reporter import calculate_exposure, generate_complaint, run_verify_scan


@app.on_event("startup")
async def startup():
    if not USE_MOCK:
        get_tracker_domains()  # pre-load tracker DB on boot


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "mock" if USE_MOCK else "live"}


@app.post("/scan")
async def scan_endpoint(req: ScanRequest):
    url = req.url
    if not url.startswith("http"):
        url = "https://" + url

    if USE_MOCK:
        return _mock_response(url)

    try:
        scan_data = run_scan(url)
        violations = find_violations(scan_data["after"])
        policy_text = fetch_cookie_policy(scan_data.get("cookie_policy_url", ""))
        analysis = analyze_violations(violations, policy_text, scan_data.get("page_html_for_fallback", ""))
        fixes = generate_fixes(analysis["undeclared"], scan_data.get("consent_platform", "unknown"), url)
        block_domains = [t["domain"] for t in analysis["undeclared"]]
        verify_result = run_verify_scan(url, block_domains)
        exposure = calculate_exposure(len(analysis["undeclared"]))
        complaint = generate_complaint(url, analysis["undeclared"], exposure)

        return {
            "url": url,
            "scan": {
                "clicked_reject": scan_data["clicked_reject"],
                "consent_platform": scan_data.get("consent_platform"),
                "before_count": len(set(scan_data["before"])),
                "after_count": len(set(scan_data["after"])),
                "violation_count": len(analysis["violations"]),
            },
            "violations": analysis["violations"],
            "undeclared": analysis["undeclared"],
            "declared": analysis["declared"],
            "fixes": fixes,
            "verify": verify_result,
            "exposure": exposure,
            "complaint": complaint,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _mock_response(url: str) -> dict:
    return {
        "url": url,
        "scan": {
            "clicked_reject": True,
            "consent_platform": "OneTrust",
            "before_count": 6,
            "after_count": 14,
            "violation_count": 9,
        },
        "violations": [
            {"domain": "facebook.net", "declared": False, "category": "advertising", "data_collected": "Tracks users across websites for ad targeting"},
            {"domain": "google-analytics.com", "declared": True, "category": "analytics", "data_collected": "Page views and user behavior"},
            {"domain": "bat.bing.com", "declared": False, "category": "advertising", "data_collected": "Microsoft ad conversion tracking"},
            {"domain": "ads-twitter.com", "declared": False, "category": "advertising", "data_collected": "Twitter ad pixel"},
            {"domain": "segment.com", "declared": False, "category": "analytics", "data_collected": "User event tracking and data routing"},
        ],
        "undeclared": [
            {"domain": "facebook.net", "declared": False, "category": "advertising", "data_collected": "Tracks users across websites for ad targeting"},
            {"domain": "bat.bing.com", "declared": False, "category": "advertising", "data_collected": "Microsoft ad conversion tracking"},
            {"domain": "ads-twitter.com", "declared": False, "category": "advertising", "data_collected": "Twitter ad pixel"},
        ],
        "declared": [
            {"domain": "google-analytics.com", "declared": True, "category": "analytics", "data_collected": "Page views and user behavior"},
        ],
        "fixes": {
            "policy_fix": "<p>We use the following third-party services for advertising and analytics purposes. These services may collect data about your browsing behavior: Facebook Pixel (facebook.net) for ad retargeting, Microsoft Advertising (bat.bing.com) for conversion tracking, and Twitter Pixel (ads-twitter.com) for campaign measurement. These are only active with your explicit consent.</p>",
            "banner_fix": "In your OneTrust dashboard:\n1. Go to Scripts > Categorization\n2. Find facebook.net — move to 'Targeting Cookies' category\n3. Find bat.bing.com — move to 'Targeting Cookies' category\n4. Find ads-twitter.com — move to 'Targeting Cookies' category\n5. Ensure each script has 'Active' toggled OFF for non-consent state\n6. Republish your cookie banner",
        },
        "verify": {"remaining_requests": [], "violation_count": 0, "clean": True},
        "exposure": {
            "violation_count": 3,
            "max_fine_percent": "4% of annual global revenue",
            "estimated_range_small": "€50,000–€200,000",
            "estimated_range_medium": "€200,000–€800,000",
            "estimated_range_large": "€800,000–€4,000,000",
            "relevant_authority": "Your national Data Protection Authority (DPA)",
        },
        "complaint": "Dear Data Protection Authority,\n\nI hereby submit a formal complaint regarding GDPR violations by the operator of " + url + ".\n\nDespite clicking 'Reject All' on the cookie consent banner, the following undeclared third-party trackers continued to fire network requests:\n\n- facebook.net (advertising): Tracks users across websites for ad targeting\n- bat.bing.com (advertising): Microsoft ad conversion tracking\n- ads-twitter.com (advertising): Twitter ad pixel\n\nThese actions constitute violations of GDPR Article 7 (conditions for consent) and Article 5(1)(a) (lawfulness of processing). I request that your authority investigate this matter and take appropriate enforcement action.\n\nSincerely,\nA Concerned User",
    }
