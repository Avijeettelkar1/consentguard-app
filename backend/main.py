import os
import socket
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
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

# JWT authentication (independent of the scan pipeline / MOCK mode)
from auth import router as auth_router, init_db  # noqa: E402
from scans import router as scans_router, init_db as init_scans_db  # noqa: E402
from watch import router as watch_router, init_db as init_watch_db, start_scheduler  # noqa: E402
from notify import router as notify_router, init_db as init_notify_db  # noqa: E402

init_db()
init_scans_db()
init_watch_db()
init_notify_db()
app.include_router(auth_router)
app.include_router(scans_router)
app.include_router(watch_router)
app.include_router(notify_router)


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=3)


if not USE_MOCK:
    from analyzer import analyze_violations, fetch_cookie_policy, find_violations
    from cookie_risk import build_cookie_findings, build_cookie_transparency
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
    start_scheduler()  # Watchtower background monitor


@app.get("/")
async def root() -> dict:
    return {
        "name": "ConsentGuard API",
        "status": "ok",
        "health": "/health",
        "scan": "/scan",
    }


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

    reachable, reason, working_url = await asyncio.to_thread(_check_reachable, url)
    if not reachable:
        raise HTTPException(status_code=422, detail=reason)
    url = working_url

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
        cookie_findings = build_cookie_findings(scan_data, url)
        comparison_summary = _summarize_comparison(scan_data)
        plain_summary = _build_plain_summary(
            scan_data=scan_data,
            tag_audit=tag_audit,
            confirmed_issues=undeclared,
            needs_review=needs_review,
            cookie_transparency=cookie_transparency,
        )
        human_report = _build_human_report(
            url=url,
            scan_data=scan_data,
            plain_summary=plain_summary,
            cookie_findings=cookie_findings,
            tag_audit=tag_audit,
            comparison=comparison_summary,
            fixes=fixes,
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
            "comparison": comparison_summary,
            "cookie_transparency": cookie_transparency,
            "cookie_findings": cookie_findings,
            "tag_audit": tag_audit,
            "plain_summary": plain_summary,
            "human_report": human_report,
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


def _check_reachable(url: str) -> tuple[bool, str, str]:
    """Confirm the domain resolves and a server actually responds before scanning.

    Returns (ok, error_message, working_url). Discovers which scheme actually
    answers (some real sites, e.g. check.de, serve HTTP only) and returns that
    URL so the scanner doesn't waste time on a dead port. Only hard failures
    (DNS miss on every host, refused/timed-out on both schemes) count as
    "doesn't exist / unreachable".
    """
    host = (urlparse(url).hostname or "").strip()
    if not host:
        return False, "That doesn't look like a valid website address.", url

    # 1) DNS: does the domain exist at all?
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, f"“{host}” doesn’t exist — we couldn’t resolve that domain. Check the spelling and try again.", url
    except Exception:
        pass  # non-DNS resolver hiccup: fall through to the HTTP probe

    # 2) HTTP: which scheme actually answers? Prefer https, fall back to http.
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ConsentGuardBot/1.0; +https://consentguard.io)"}
    candidates = [url]
    if url.startswith("https://"):
        candidates.append("http://" + url[len("https://"):])
    for scheme_url in candidates:
        try:
            resp = requests.get(scheme_url, timeout=8, allow_redirects=True, stream=True, headers=headers)
            final = resp.url or scheme_url
            resp.close()
            return True, "", final  # any HTTP response = the site is live
        except requests.exceptions.SSLError:
            continue  # https broken → try the http candidate before giving up
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
        except requests.exceptions.RequestException:
            return True, "", scheme_url  # odd protocol error: let the real scanner decide
    return False, f"We couldn’t reach “{host}”. The site may be offline or refusing connections right now.", url


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


def _build_human_report(
    url: str,
    scan_data: dict,
    plain_summary: dict,
    cookie_findings: list[dict],
    tag_audit: dict,
    comparison: dict,
    fixes: dict,
) -> dict:
    host = urlparse(url).netloc or url
    cookie_summary = _summarize_cookie_findings(cookie_findings)
    flagged = [
        finding
        for finding in cookie_findings
        if finding.get("status") in {"potential_consent_issue", "needs_review"}
    ]
    likely_causes = _unique_nonempty(
        finding.get("likely_reason")
        for finding in flagged
    )
    observations = _build_agent_observations(plain_summary, cookie_findings, tag_audit, comparison)

    return {
        "title": f"ConsentGuard cookie report for {host}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": plain_summary.get("status", "Scan complete"),
        "executive_summary": plain_summary.get("result", "ConsentGuard completed the scan."),
        "user_takeaway": plain_summary.get("user_takeaway", ""),
        "cookie_summary": cookie_summary,
        "agent": {
            "name": "ConsentGuard analysis agent",
            "mode": "evidence_based_rules",
            "summary": _agent_summary(cookie_summary, tag_audit),
            "observations": observations,
            "likely_causes": likely_causes or [
                "No obvious non-essential cookie activity was detected after Reject."
            ],
            "confidence_note": (
                "The agent explains scanner evidence and deterministic classifications. "
                "It is not a legal determination."
            ),
        },
        "recommended_actions": _report_actions(cookie_findings, tag_audit, fixes),
        "legal_references": _legal_reference_catalog(),
        "methodology": plain_summary.get("what_we_checked", []),
        "limitations": [
            "Cookie values are omitted because they can contain personal identifiers.",
            "A script loader after Reject is review evidence, not automatically a confirmed GDPR violation.",
            "A final legal conclusion depends on the site's purpose, contracts, and full consent implementation.",
        ],
    }


def _summarize_cookie_findings(cookie_findings: list[dict]) -> dict:
    summary = {
        "total_active_after_reject": len(cookie_findings),
        "potential_consent_issues": 0,
        "needs_review": 0,
        "appears_acceptable": 0,
        "high_severity": 0,
        "medium_severity": 0,
        "low_severity": 0,
        "by_category": {},
    }
    for finding in cookie_findings:
        status = finding.get("status", "needs_review")
        severity = finding.get("severity", "low")
        category = finding.get("category", "unknown")
        if status == "potential_consent_issue":
            summary["potential_consent_issues"] += 1
        elif status == "appears_acceptable":
            summary["appears_acceptable"] += 1
        else:
            summary["needs_review"] += 1
        if severity == "high":
            summary["high_severity"] += 1
        elif severity == "medium":
            summary["medium_severity"] += 1
        else:
            summary["low_severity"] += 1
        summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
    return summary


def _build_agent_observations(
    plain_summary: dict,
    cookie_findings: list[dict],
    tag_audit: dict,
    comparison: dict,
) -> list[str]:
    observations = []
    result = plain_summary.get("result")
    if result:
        observations.append(result)

    potential = [
        finding for finding in cookie_findings
        if finding.get("status") == "potential_consent_issue"
    ]
    review = [
        finding for finding in cookie_findings
        if finding.get("status") == "needs_review"
    ]
    acceptable = [
        finding for finding in cookie_findings
        if finding.get("status") == "appears_acceptable"
    ]

    if potential:
        names = ", ".join(finding.get("name") or "unnamed" for finding in potential[:5])
        observations.append(
            f"{len(potential)} cookie(s) look non-essential after Reject: {names}."
        )
    if review:
        observations.append(
            f"{len(review)} cookie(s) need manual purpose review before they can be treated as acceptable."
        )
    if acceptable:
        observations.append(
            f"{len(acceptable)} cookie(s) appear compatible with necessary consent-state, session, or security use."
        )
    if tag_audit.get("reject_payload_count"):
        observations.append(
            f"{tag_audit.get('reject_payload_count')} analytics or advertising payload(s) were observed after Reject."
        )
    elif tag_audit.get("loader_evidence_after_reject"):
        observations.append(
            "A tag loader appeared after Reject, but no downstream analytics or advertising payload was confirmed."
        )
    if comparison.get("reject_only_request_count"):
        observations.append(
            f"{comparison.get('reject_only_request_count')} request(s) appeared only in the Reject path."
        )

    return observations


def _agent_summary(cookie_summary: dict, tag_audit: dict) -> str:
    if cookie_summary["potential_consent_issues"] or tag_audit.get("reject_payload_count"):
        return (
            "Some non-essential tracking or advertising evidence remained active after the Reject choice. "
            "This should be investigated before treating the banner as compliant."
        )
    if cookie_summary["needs_review"] or tag_audit.get("loader_evidence_after_reject"):
        return (
            "Reject mostly appears to work, but some cookies or tag infrastructure need a privacy review."
        )
    return "No clear non-essential cookie or tracking activity was found after Reject in this scan."


def _report_actions(cookie_findings: list[dict], tag_audit: dict, fixes: dict) -> list[str]:
    actions = []
    if any(finding.get("status") == "potential_consent_issue" for finding in cookie_findings):
        actions.append("Move analytics, advertising, and social cookies behind explicit opt-in consent.")
        actions.append("Check tag-manager triggers and consent-platform category mappings for the listed cookies.")
    if any(finding.get("status") == "needs_review" for finding in cookie_findings):
        actions.append("Map each review-only cookie to a documented purpose and consent category.")
    if tag_audit.get("loader_evidence_after_reject"):
        actions.append("Verify that tag loaders do not fire downstream analytics or advertising payloads after Reject.")
    banner_fix = (fixes or {}).get("banner_fix")
    if banner_fix:
        actions.append("Apply the generated banner-fix notes, then run ConsentGuard again.")
    if not actions:
        actions.extend([
            "Keep the Reject path unchanged.",
            "Rescan after marketing, analytics, or consent-banner changes.",
        ])
    return _unique_nonempty(actions)


def _legal_reference_catalog() -> list[dict]:
    return [
        {
            "ref": "ePrivacy Directive Art. 5(3)",
            "plain": "Storing or accessing information on a user's device generally requires consent unless strictly necessary.",
        },
        {
            "ref": "GDPR Art. 5(1)(a)",
            "plain": "Personal-data processing must be lawful, fair, and transparent.",
        },
        {
            "ref": "GDPR Art. 6",
            "plain": "Processing personal data needs a valid lawful basis.",
        },
        {
            "ref": "GDPR Art. 7",
            "plain": "Consent must be demonstrable, withdrawable, and respected when refused.",
        },
    ]


def _unique_nonempty(values) -> list[str]:
    unique = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _confirmed_issue_count(confirmed_issues: list[dict], tag_audit: dict) -> int:
    reject_payload_count = tag_audit.get("reject_payload_count", 0)
    if reject_payload_count:
        return reject_payload_count
    return len(confirmed_issues)


def _mock_response(url: str) -> dict:
    scan = {
        "clicked_accept": True,
        "clicked_reject": True,
        "consent_platform": "OneTrust",
        "before_count": 6,
        "after_count": 14,
        "accept_after_count": 18,
        "reject_after_count": 14,
        "violation_count": 2,
        "tracker_finding_count": 5,
        "needs_review_count": 1,
        "scanner": "mock",
        "scanner_error": None,
        "cookie_policy_url": url.rstrip("/") + "/privacy/cookies",
        "accept_clicked_selector": "button:has-text('Accept All')",
        "reject_clicked_selector": "button:has-text('Reject All')",
    }
    comparison = {
        "accept_only_request_count": 9,
        "reject_only_request_count": 2,
        "common_request_count": 11,
        "accept_only_domains": [
            {"domain": "google-analytics.com", "count": 3},
            {"domain": "googleads.g.doubleclick.net", "count": 2},
        ],
        "reject_only_domains": [
            {"domain": "connect.facebook.net", "count": 1},
            {"domain": "bat.bing.com", "count": 1},
        ],
        "common_domains": [
            {"domain": urlparse(url).netloc.lower().lstrip("www."), "count": 8},
            {"domain": "cdn.example.com", "count": 3},
        ],
        "accept_only_cookies": [".example.com|_gcl_au"],
        "reject_only_cookies": [".example.com|_fbp"],
        "common_cookie_count": 2,
    }
    cookie_findings = [
        {
            "name": "_fbp",
            "domain": ".example.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
            "category": "advertising",
            "party": "first_party",
            "severity": "high",
            "confidence": "high",
            "active_after_reject": True,
            "presence": "only_after_reject",
            "status": "potential_consent_issue",
            "purpose": "Meta/Facebook browser identifier for advertising measurement",
            "evidence": "Meta/Facebook browser identifier for advertising measurement",
            "legal_assessment": "This looks like a non-essential cookie that normally requires prior consent. Seeing it after Reject is evidence of a potential consent problem.",
            "legal_refs": ["ePrivacy Directive Art. 5(3)", "GDPR Art. 5(1)(a)", "GDPR Art. 6(1)(a)", "GDPR Art. 7"],
            "potentially_implicated_guidelines": ["ePrivacy Directive Art. 5(3)", "GDPR Art. 5(1)(a)", "GDPR Art. 6(1)(a)", "GDPR Art. 7"],
            "likely_reason": "A marketing tag, conversion pixel, or ad platform script may still be firing before the consent banner blocks it.",
            "recommended_action": "Block this cookie or its parent tag until the visitor gives explicit opt-in consent, then rescan.",
            "value_omitted": True,
        },
        {
            "name": "_ga",
            "domain": ".example.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
            "category": "analytics",
            "party": "first_party",
            "severity": "high",
            "confidence": "high",
            "active_after_reject": True,
            "presence": "also_after_accept",
            "status": "potential_consent_issue",
            "purpose": "Google Analytics visitor measurement",
            "evidence": "Google Analytics visitor measurement",
            "legal_assessment": "This looks like a non-essential cookie that normally requires prior consent. Seeing it after Reject is evidence of a potential consent problem.",
            "legal_refs": ["ePrivacy Directive Art. 5(3)", "GDPR Art. 5(1)(a)", "GDPR Art. 6(1)(a)", "GDPR Art. 7"],
            "potentially_implicated_guidelines": ["ePrivacy Directive Art. 5(3)", "GDPR Art. 5(1)(a)", "GDPR Art. 6(1)(a)", "GDPR Art. 7"],
            "likely_reason": "An analytics tag may load before consent state is applied, or the tag manager trigger is not tied to opt-in consent.",
            "recommended_action": "Block this cookie or its parent tag until the visitor gives explicit opt-in consent, then rescan.",
            "value_omitted": True,
        },
        {
            "name": "OptanonConsent",
            "domain": ".example.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
            "category": "strictly_necessary",
            "party": "first_party",
            "severity": "low",
            "confidence": "high",
            "active_after_reject": True,
            "presence": "also_after_accept",
            "status": "appears_acceptable",
            "purpose": "Stores the visitor's cookie consent preferences",
            "evidence": "Stores the visitor's cookie consent preferences",
            "legal_assessment": "This appears consistent with cookies that can remain active after rejection, such as consent-state, security, or session support.",
            "legal_refs": ["ePrivacy Directive Art. 5(3) essential-cookie exemption", "GDPR Art. 5(1)(a)"],
            "potentially_implicated_guidelines": ["ePrivacy Directive Art. 5(3) essential-cookie exemption", "GDPR Art. 5(1)(a)"],
            "likely_reason": "The site may keep this cookie to remember the rejection choice or support essential security/session behavior.",
            "recommended_action": "Document why this cookie is necessary and keep its value out of analytics or advertising workflows.",
            "value_omitted": True,
        },
        {
            "name": "vendor_session",
            "domain": ".thirdparty.example",
            "path": "/",
            "secure": False,
            "httpOnly": False,
            "sameSite": "None",
            "category": "unknown",
            "party": "third_party",
            "severity": "medium",
            "confidence": "low",
            "active_after_reject": True,
            "presence": "after_reject",
            "status": "needs_review",
            "purpose": "Third-party cookie remained after rejection, but its purpose is not in the local rule set",
            "evidence": "Third-party cookie remained after rejection, but its purpose is not in the local rule set; Cookie is missing the Secure flag; Cross-site cookie lacks Secure protection",
            "legal_assessment": "The scanner cannot confirm the purpose, so a privacy owner should review whether it is necessary before consent.",
            "legal_refs": ["ePrivacy Directive Art. 5(3)", "GDPR Art. 5(1)(a)", "GDPR Art. 6"],
            "potentially_implicated_guidelines": ["ePrivacy Directive Art. 5(3)", "GDPR Art. 5(1)(a)", "GDPR Art. 6"],
            "likely_reason": "A third-party script may be setting this cookie directly, outside the consent platform's blocking rules.",
            "recommended_action": "Map this cookie to a consent category, confirm its purpose, and block it before consent if it is not essential.",
            "value_omitted": True,
        },
    ]
    tag_audit = {
        "verdict": "non_essential_payloads_after_reject",
        "severity": "high",
        "summary": "Tracking or advertising payload requests were observed after reject.",
        "gtm_containers": {"accept": ["GTM-MOCK"], "reject": ["GTM-MOCK"], "html": ["GTM-MOCK"]},
        "accept_payload_count": 4,
        "reject_payload_count": 2,
        "blocked_by_reject": [
            {"kind": "google_ads_conversion", "domain": "googleads.g.doubleclick.net", "event_name": "conversion"},
        ],
        "still_firing_after_reject": [
            {"kind": "meta_pixel_event", "domain": "facebook.com", "event_name": "PageView"},
            {"kind": "bing_ads_event", "domain": "bat.bing.com", "event_name": "page_load"},
        ],
        "reject_only_payloads": [
            {"kind": "bing_ads_event", "domain": "bat.bing.com", "event_name": "page_load"},
        ],
        "loader_evidence_after_reject": [
            {"kind": "gtm_container", "domain": "googletagmanager.com", "container_id": "GTM-MOCK"},
        ],
        "note": "A GTM loader request is not automatically a GDPR violation. The strongest evidence is downstream analytics or advertising payloads after reject.",
    }
    cookie_transparency = {
        "accept_count": 5,
        "reject_count": len(cookie_findings),
        "accept_only": comparison["accept_only_cookies"],
        "reject_only": comparison["reject_only_cookies"],
        "common": [".example.com|_ga", ".example.com|OptanonConsent"],
        "risky_after_reject": [
            {
                "name": finding["name"],
                "domain": finding["domain"],
                "path": finding["path"],
                "secure": finding["secure"],
                "httpOnly": finding["httpOnly"],
                "sameSite": finding["sameSite"],
                "severity": finding["severity"],
                "reason": finding["evidence"],
            }
            for finding in cookie_findings
            if finding["status"] != "appears_acceptable"
        ],
        "note": "Cookie values are intentionally omitted because they can contain personal identifiers.",
    }
    plain_summary = {
        "status": "Potential consent problem found",
        "result": "The scanner found 2 advertising or analytics event(s) after the user rejected optional cookies.",
        "comparison": "Accepting cookies caused more activity (18 requests) than rejecting them (14 requests).",
        "user_takeaway": "This site should be reviewed because optional tracking may still be active after rejection.",
        "what_we_checked": [
            "We opened the site in a clean browser.",
            "We clicked Accept All once and recorded what loaded.",
            "We opened it again in a clean browser, clicked Reject All, and recorded what still loaded.",
            "We compared both runs and looked for advertising, analytics, and risky cookies after rejection.",
        ],
        "plain_counts": {
            "extra_activity_when_accepted": comparison["accept_only_request_count"],
            "activity_only_after_reject": comparison["reject_only_request_count"],
            "tracking_events_blocked_by_reject": len(tag_audit["blocked_by_reject"]),
            "tracking_events_after_reject": tag_audit["reject_payload_count"],
            "risky_cookies_after_reject": len(cookie_transparency["risky_after_reject"]),
            "confirmed_issues": 2,
            "review_items": 1,
        },
    }
    fixes = {
        "policy_fix": "<p>We use analytics and advertising services only after opt-in consent. Meta, Microsoft Advertising, and Google Analytics must remain disabled when visitors reject optional cookies.</p>",
        "banner_fix": "1. Open the OneTrust dashboard.\n2. Move Meta, Microsoft Advertising, and Google Analytics into non-essential categories.\n3. Configure each script to load only after opt-in consent.\n4. Ensure Reject All disables marketing and analytics tags.\n5. Republish the banner and re-run the scan.",
    }
    human_report = _build_human_report(
        url=url,
        scan_data={},
        plain_summary=plain_summary,
        cookie_findings=cookie_findings,
        tag_audit=tag_audit,
        comparison=comparison,
        fixes=fixes,
    )

    return {
        "url": url,
        "scan": scan,
        "accept_trackers": [
            {"domain": "google-analytics.com", "category": "analytics", "company": "Google Analytics", "data_collected": "Page views and user behavior"},
            {"domain": "googleads.g.doubleclick.net", "category": "advertising", "company": "Google Marketing Platform", "data_collected": "Ad conversion tracking"},
        ],
        "comparison": comparison,
        "cookie_transparency": cookie_transparency,
        "cookie_findings": cookie_findings,
        "tag_audit": tag_audit,
        "plain_summary": plain_summary,
        "human_report": human_report,
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
        "needs_review": [
            {"domain": "googletagmanager.com", "declared": True, "category": "analytics", "company": "Google Tag Manager", "data_collected": "Loads and coordinates tags", "needs_review": True, "violation_reason": "GTM loader observed after reject; downstream payloads decide severity."},
        ],
        "declared": [
            {"domain": "google-analytics.com", "declared": True, "category": "analytics", "company": "Google Analytics", "data_collected": "Page views and user behavior", "violation_reason": "Fires after reject and appears in the policy"},
        ],
        "fixes": fixes,
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
