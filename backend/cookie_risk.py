from tracker_db import is_tracker

TRACKING_COOKIE_NAMES = {
    "_ga": "Google Analytics client identifier",
    "_gid": "Google Analytics session/user identifier",
    "_gat": "Google Analytics throttling/tracking cookie",
    "_gcl_au": "Google Ads conversion/linker cookie",
    "_fbp": "Meta/Facebook browser identifier",
    "_fbc": "Meta/Facebook click identifier",
    "fr": "Meta/Facebook advertising cookie",
    "ide": "Google DoubleClick advertising cookie",
    "test_cookie": "Google DoubleClick browser support cookie",
    "anid": "Google advertising identifier",
    "nid": "Google preference/advertising cookie",
    "muid": "Microsoft advertising/user identifier",
    "_uetsid": "Microsoft Ads session identifier",
    "_uetvid": "Microsoft Ads visitor identifier",
    "__gads": "Google advertising cookie",
    "__gpi": "Google advertising cookie",
}


def build_cookie_transparency(scan_data: dict) -> dict:
    accept_cookies = scan_data.get("accept", {}).get("cookies", [])
    reject_cookies = scan_data.get("reject", {}).get("cookies", [])
    comparison = scan_data.get("comparison", {})

    risky_after_reject = [
        risk
        for cookie in reject_cookies
        if (risk := classify_cookie(cookie))
    ]

    return {
        "accept_count": len(accept_cookies),
        "reject_count": len(reject_cookies),
        "accept_only": comparison.get("accept_only_cookies", []),
        "reject_only": comparison.get("reject_only_cookies", []),
        "common": comparison.get("common_cookies", []),
        "risky_after_reject": risky_after_reject,
        "note": "Cookie values are intentionally omitted because they can contain personal identifiers.",
    }


def classify_cookie(cookie: dict) -> dict | None:
    name = (cookie.get("name") or "").lower()
    domain = (cookie.get("domain") or "").lower().lstrip(".").lstrip("www.")

    reasons = []
    severity = "medium"

    if name in TRACKING_COOKIE_NAMES:
        severity = "high"
        reasons.append(TRACKING_COOKIE_NAMES[name])
    elif any(name.startswith(prefix) for prefix in ("_ga_", "_gcl_", "_uet")):
        severity = "high"
        reasons.append("Known analytics or advertising cookie name pattern")

    tracker_info = is_tracker(domain)
    if tracker_info:
        severity = "high"
        reasons.append(f"Cookie belongs to known tracker domain ({tracker_info.get('company', domain)})")

    if cookie.get("secure") is False:
        reasons.append("Cookie is not marked Secure")
    if cookie.get("sameSite") in (None, "None") and cookie.get("secure") is False:
        reasons.append("Cross-site cookie lacks Secure protection")

    if not reasons:
        return None

    return {
        "name": cookie.get("name"),
        "domain": cookie.get("domain"),
        "path": cookie.get("path"),
        "secure": cookie.get("secure"),
        "httpOnly": cookie.get("httpOnly"),
        "sameSite": cookie.get("sameSite"),
        "severity": severity,
        "reason": "; ".join(reasons),
    }
