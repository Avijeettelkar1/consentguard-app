import os
import asyncio
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).with_name(".env"))

USE_MOCK = os.getenv("MOCK", "false").lower() == "true"
VERIFY_SCAN = os.getenv("VERIFY_SCAN", "false").lower() == "true"

app = FastAPI(title="ConsentGuard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=3)


if not USE_MOCK:
    from analyzer import analyze_violations, fetch_cookie_policy, find_violations
    from cookie_risk import build_cookie_transparency
    from fixer import generate_fixes
    from reporter import calculate_exposure, generate_complaint, run_verify_scan
    from scanner import run_scan
    from tag_audit import audit_tags, filter_domain_violations_with_tag_audit
    from tracker_db import get_tracker_domains


@app.on_event("startup")
async def startup() -> None:
    if not USE_MOCK:
        try:
            get_tracker_domains()
        except Exception:
            # The tracker module has a local fallback. Startup should not fail a demo.
            pass


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "mode": "mock" if USE_MOCK else "live",
        "verify_scan": VERIFY_SCAN,
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        "daytona_configured": bool(os.getenv("DAYTONA_API_KEY", "").strip() and os.getenv("DAYTONA_SNAPSHOT", "").strip()),
    }


@app.post("/scan")
async def scan_endpoint(req: ScanRequest) -> dict:
    url = _normalize_url(req.url)

    if USE_MOCK:
        return _mock_response(url)

    try:
        scan_data = await asyncio.to_thread(run_scan, url)
        tag_audit = audit_tags(scan_data)
        tracker_hits = find_violations(scan_data.get("after", []))
        accept_tracker_hits = find_violations(scan_data.get("accept", {}).get("post_consent_requests", []))
        policy_text = fetch_cookie_policy(scan_data.get("cookie_policy_url"))
        analysis = analyze_violations(
            tracker_hits,
            policy_text,
            scan_data.get("page_html_for_fallback", ""),
        )
        analysis["violations"] = filter_domain_violations_with_tag_audit(analysis["violations"], tag_audit)
        analysis["undeclared"] = [
            violation
            for violation in analysis["violations"]
            if not violation.get("declared") and not violation.get("needs_review")
        ]
        analysis["declared"] = [
            violation
            for violation in analysis["violations"]
            if violation.get("declared")
        ]
        needs_review = [
            violation
            for violation in analysis["violations"]
            if violation.get("needs_review")
        ]
        undeclared = analysis["undeclared"]
        fixes = generate_fixes(undeclared, scan_data.get("consent_platform"), url)
        exposure = calculate_exposure(len(undeclared))
        complaint = generate_complaint(url, undeclared, exposure)
        cookie_transparency = build_cookie_transparency(scan_data)
        plain_summary = _build_plain_summary(
            scan_data=scan_data,
            tag_audit=tag_audit,
            confirmed_issues=undeclared,
            needs_review=needs_review,
            cookie_transparency=cookie_transparency,
        )

        if VERIFY_SCAN:
            verify_result = run_verify_scan(url, [tracker["domain"] for tracker in undeclared])
        else:
            verify_result = {
                "remaining_requests": [],
                "violation_count": 0,
                "clean": len(undeclared) == 0,
                "skipped": True,
                "reason": "Set VERIFY_SCAN=true to run a second verification scan.",
            }

        return {
            "url": url,
            "scan": {
                "clicked_accept": scan_data.get("clicked_accept", False),
                "clicked_reject": scan_data.get("clicked_reject", False),
                "consent_platform": scan_data.get("consent_platform"),
                "before_count": len(set(scan_data.get("before", []))),
                "after_count": len(set(scan_data.get("after", []))),
                "accept_after_count": len(set(scan_data.get("accept", {}).get("post_consent_requests", []))),
                "reject_after_count": len(set(scan_data.get("reject", {}).get("post_consent_requests", []))),
                "violation_count": _confirmed_issue_count(undeclared, tag_audit),
                "tracker_finding_count": len(analysis["violations"]),
                "needs_review_count": len(needs_review),
                "scanner": scan_data.get("scanner", "unknown"),
                "scanner_error": scan_data.get("scanner_error"),
                "cookie_policy_url": scan_data.get("cookie_policy_url"),
                "accept_clicked_selector": scan_data.get("accept", {}).get("clicked_selector"),
                "reject_clicked_selector": scan_data.get("reject", {}).get("clicked_selector"),
            },
            "accept_trackers": accept_tracker_hits,
            "comparison": _summarize_comparison(scan_data),
            "cookie_transparency": cookie_transparency,
            "tag_audit": tag_audit,
            "plain_summary": plain_summary,
            "needs_review": needs_review,
            "violations": analysis["violations"],
            "undeclared": undeclared,
            "declared": analysis["declared"],
            "fixes": fixes,
            "verify": verify_result,
            "exposure": exposure,
            "complaint": complaint,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    return cleaned


def _summarize_comparison(scan_data: dict) -> dict:
    comparison = scan_data.get("comparison", {})
    accept_only = comparison.get("accept_only_requests", [])
    reject_only = comparison.get("reject_only_requests", [])
    common = comparison.get("common_requests", [])

    return {
        "accept_only_request_count": len(accept_only),
        "reject_only_request_count": len(reject_only),
        "common_request_count": len(common),
        "accept_only_domains": _top_domains(accept_only),
        "reject_only_domains": _top_domains(reject_only),
        "common_domains": _top_domains(common),
        "accept_only_cookies": comparison.get("accept_only_cookies", []),
        "reject_only_cookies": comparison.get("reject_only_cookies", []),
        "common_cookie_count": len(comparison.get("common_cookies", [])),
    }


def _top_domains(urls: list[str], limit: int = 15) -> list[dict]:
    counts: dict[str, int] = {}
    for url in urls:
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if not domain:
            continue
        counts[domain] = counts.get(domain, 0) + 1
    return [
        {"domain": domain, "count": count}
        for domain, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _build_plain_summary(
    scan_data: dict,
    tag_audit: dict,
    confirmed_issues: list[dict],
    needs_review: list[dict],
    cookie_transparency: dict,
) -> dict:
    clicked_accept = scan_data.get("clicked_accept", False)
    clicked_reject = scan_data.get("clicked_reject", False)
    accept_count = len(set(scan_data.get("accept", {}).get("post_consent_requests", [])))
    reject_count = len(set(scan_data.get("reject", {}).get("post_consent_requests", [])))
    blocked_count = len(tag_audit.get("blocked_by_reject", []))
    reject_payload_count = tag_audit.get("reject_payload_count", 0)
    risky_cookie_count = len(cookie_transparency.get("risky_after_reject", []))
    confirmed_count = reject_payload_count if reject_payload_count else len(confirmed_issues)

    if not clicked_accept or not clicked_reject:
        status = "Could not complete the consent test"
        result = (
            "The scanner could not click both consent choices, so the result should not be treated as a final compliance judgement."
        )
        user_takeaway = "Try this site again after we add support for its cookie banner."
    elif confirmed_count:
        status = "Potential consent problem found"
        result = (
            f"The scanner found {confirmed_count} advertising or analytics event(s) after the user rejected optional cookies."
        )
        user_takeaway = "This site should be reviewed because optional tracking may still be active after rejection."
    elif reject_payload_count == 0 and blocked_count > 0:
        status = "Reject appears to work"
        result = (
            "The site loaded extra marketing or analytics activity only after accepting cookies, and blocked that activity after rejection."
        )
        user_takeaway = "This is a good sign: the reject choice appears to be respected for the tracking checks we ran."
    elif needs_review:
        status = "No clear violation, but review recommended"
        result = (
            "Some supporting services still loaded after rejection, but the scanner did not see them sending advertising or analytics events."
        )
        user_takeaway = "This is not a confirmed problem, but a privacy/compliance owner should review the supporting services."
    else:
        status = "No obvious tracking after reject"
        result = "The scanner did not observe known advertising or analytics activity after rejection."
        user_takeaway = "No immediate consent issue was found in this scan."

    if accept_count > reject_count:
        comparison = (
            f"Accepting cookies caused more activity ({accept_count} requests) than rejecting them ({reject_count} requests)."
        )
    elif accept_count == reject_count:
        comparison = (
            f"Accepting and rejecting produced about the same amount of activity ({accept_count} requests each)."
        )
    else:
        comparison = (
            f"Rejecting produced more observed activity ({reject_count} requests) than accepting ({accept_count} requests)."
        )

    return {
        "status": status,
        "result": result,
        "comparison": comparison,
        "user_takeaway": user_takeaway,
        "what_we_checked": [
            "We opened the site in a clean browser.",
            "We clicked Accept All once and recorded what loaded.",
            "We opened it again in a clean browser, clicked Reject All, and recorded what still loaded.",
            "We compared both runs and looked for advertising, analytics, and risky cookies after rejection.",
        ],
        "plain_counts": {
            "extra_activity_when_accepted": len(scan_data.get("comparison", {}).get("accept_only_requests", [])),
            "activity_only_after_reject": len(scan_data.get("comparison", {}).get("reject_only_requests", [])),
            "tracking_events_blocked_by_reject": blocked_count,
            "tracking_events_after_reject": reject_payload_count,
            "risky_cookies_after_reject": risky_cookie_count,
            "confirmed_issues": confirmed_count,
            "review_items": len(needs_review),
        },
    }


def _confirmed_issue_count(confirmed_issues: list[dict], tag_audit: dict) -> int:
    reject_payload_count = tag_audit.get("reject_payload_count", 0)
    if reject_payload_count:
        return reject_payload_count
    return len(confirmed_issues)


def _mock_response(url: str) -> dict:
    return {
        "url": url,
        "scan": {
            "clicked_reject": True,
            "consent_platform": "OneTrust",
            "before_count": 6,
            "after_count": 14,
            "violation_count": 5,
            "scanner": "mock",
            "cookie_policy_url": url.rstrip("/") + "/privacy/cookies",
        },
        "violations": [
            {"domain": "facebook.net", "declared": False, "category": "advertising", "company": "Meta", "data_collected": "Tracks users across websites for ad targeting", "violation_reason": "Fires after reject and is not listed in the policy"},
            {"domain": "google-analytics.com", "declared": True, "category": "analytics", "company": "Google Analytics", "data_collected": "Page views and user behavior", "violation_reason": "Fires after reject and appears in the policy"},
            {"domain": "bat.bing.com", "declared": False, "category": "advertising", "company": "Microsoft Advertising", "data_collected": "Microsoft ad conversion tracking", "violation_reason": "Fires after reject and is not listed in the policy"},
            {"domain": "ads-twitter.com", "declared": False, "category": "advertising", "company": "X / Twitter", "data_collected": "Twitter ad pixel", "violation_reason": "Fires after reject and is not listed in the policy"},
            {"domain": "segment.com", "declared": False, "category": "analytics", "company": "Segment", "data_collected": "User event tracking and data routing", "violation_reason": "Fires after reject and is not listed in the policy"},
        ],
        "undeclared": [
            {"domain": "facebook.net", "declared": False, "category": "advertising", "company": "Meta", "data_collected": "Tracks users across websites for ad targeting", "violation_reason": "Fires after reject and is not listed in the policy"},
            {"domain": "bat.bing.com", "declared": False, "category": "advertising", "company": "Microsoft Advertising", "data_collected": "Microsoft ad conversion tracking", "violation_reason": "Fires after reject and is not listed in the policy"},
            {"domain": "ads-twitter.com", "declared": False, "category": "advertising", "company": "X / Twitter", "data_collected": "Twitter ad pixel", "violation_reason": "Fires after reject and is not listed in the policy"},
            {"domain": "segment.com", "declared": False, "category": "analytics", "company": "Segment", "data_collected": "User event tracking and data routing", "violation_reason": "Fires after reject and is not listed in the policy"},
        ],
        "declared": [
            {"domain": "google-analytics.com", "declared": True, "category": "analytics", "company": "Google Analytics", "data_collected": "Page views and user behavior", "violation_reason": "Fires after reject and appears in the policy"},
        ],
        "fixes": {
            "policy_fix": "<p>We use the following third-party services only where you have given prior consent: Meta (facebook.net), Microsoft Advertising (bat.bing.com), X/Twitter (ads-twitter.com), and Segment (segment.com). These services may process identifiers, device data, page views, and interaction events for advertising or analytics. They must remain disabled until you grant explicit consent.</p>",
            "banner_fix": "1. Open the OneTrust dashboard.\n2. Move facebook.net, bat.bing.com, ads-twitter.com, and segment.com into non-essential categories.\n3. Configure each script to load only after opt-in consent.\n4. Ensure Reject All disables marketing and analytics tags.\n5. Republish the banner and re-run the scan.",
        },
        "verify": {"remaining_requests": [], "violation_count": 0, "clean": True},
        "exposure": {
            "violation_count": 4,
            "max_fine_percent": "4% of annual global revenue",
            "estimated_range_small": "EUR 50,000-EUR 200,000",
            "estimated_range_medium": "EUR 200,000-EUR 800,000",
            "estimated_range_large": "EUR 800,000-EUR 4,000,000",
            "relevant_authority": "Your national Data Protection Authority (DPA)",
        },
        "complaint": (
            "Dear Data Protection Authority,\n\n"
            f"I submit this complaint regarding the website {url}.\n\n"
            "After selecting Reject All, third-party advertising and analytics trackers continued to fire, including facebook.net, bat.bing.com, ads-twitter.com, and segment.com. "
            "This may breach GDPR Article 7 and Article 5(1)(a). I request investigation and appropriate enforcement action.\n\n"
            "Sincerely,\nA concerned user"
        ),
    }
