from urllib.parse import urlparse

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

COOKIE_NAME_RULES = {
    "_ga": {
        "category": "analytics",
        "purpose": "Google Analytics visitor measurement",
        "severity": "high",
        "confidence": "high",
    },
    "_gid": {
        "category": "analytics",
        "purpose": "Google Analytics short-lived visitor measurement",
        "severity": "high",
        "confidence": "high",
    },
    "_gat": {
        "category": "analytics",
        "purpose": "Google Analytics request throttling and measurement",
        "severity": "high",
        "confidence": "high",
    },
    "_gcl_au": {
        "category": "advertising",
        "purpose": "Google Ads conversion and attribution measurement",
        "severity": "high",
        "confidence": "high",
    },
    "_fbp": {
        "category": "advertising",
        "purpose": "Meta/Facebook browser identifier for advertising measurement",
        "severity": "high",
        "confidence": "high",
    },
    "_fbc": {
        "category": "advertising",
        "purpose": "Meta/Facebook click identifier for advertising attribution",
        "severity": "high",
        "confidence": "high",
    },
    "fr": {
        "category": "advertising",
        "purpose": "Meta/Facebook advertising cookie",
        "severity": "high",
        "confidence": "high",
    },
    "ide": {
        "category": "advertising",
        "purpose": "Google DoubleClick advertising identifier",
        "severity": "high",
        "confidence": "high",
    },
    "test_cookie": {
        "category": "advertising",
        "purpose": "Google DoubleClick browser support check",
        "severity": "medium",
        "confidence": "medium",
    },
    "muid": {
        "category": "advertising",
        "purpose": "Microsoft advertising/user identifier",
        "severity": "high",
        "confidence": "high",
    },
    "_uetsid": {
        "category": "advertising",
        "purpose": "Microsoft Ads session identifier",
        "severity": "high",
        "confidence": "high",
    },
    "_uetvid": {
        "category": "advertising",
        "purpose": "Microsoft Ads visitor identifier",
        "severity": "high",
        "confidence": "high",
    },
    "__gads": {
        "category": "advertising",
        "purpose": "Google advertising cookie",
        "severity": "high",
        "confidence": "high",
    },
    "__gpi": {
        "category": "advertising",
        "purpose": "Google advertising cookie",
        "severity": "high",
        "confidence": "high",
    },
    "optanonconsent": {
        "category": "strictly_necessary",
        "purpose": "Stores the visitor's cookie consent preferences",
        "severity": "low",
        "confidence": "high",
    },
    "optanonalertboxclosed": {
        "category": "strictly_necessary",
        "purpose": "Remembers that the consent banner was closed",
        "severity": "low",
        "confidence": "high",
    },
    "cookieconsent": {
        "category": "strictly_necessary",
        "purpose": "Stores the visitor's cookie consent preferences",
        "severity": "low",
        "confidence": "high",
    },
    "didomi_token": {
        "category": "strictly_necessary",
        "purpose": "Stores the visitor's consent state",
        "severity": "low",
        "confidence": "high",
    },
    "euconsent-v2": {
        "category": "strictly_necessary",
        "purpose": "Stores IAB consent choices",
        "severity": "low",
        "confidence": "high",
    },
}

PREFIX_RULES = [
    ("_ga_", "analytics", "Google Analytics measurement identifier", "high", "high"),
    ("_gcl_", "advertising", "Google Ads conversion/linker identifier", "high", "high"),
    ("_uet", "advertising", "Microsoft Ads tracking identifier", "high", "high"),
    ("_hj", "analytics", "Hotjar behavior analytics identifier", "high", "high"),
    ("amplitude", "analytics", "Amplitude product analytics identifier", "high", "medium"),
    ("mp_", "analytics", "Mixpanel product analytics identifier", "high", "medium"),
    ("ajs_", "analytics", "Segment analytics identifier", "high", "medium"),
    ("__stripe", "strictly_necessary", "Payment or fraud-prevention support cookie", "low", "medium"),
]

NECESSARY_HINTS = (
    "consent",
    "cookie",
    "csrf",
    "xsrf",
    "session",
    "sess",
    "auth",
    "login",
    "token",
    "secure",
    "cf_clearance",
)

PREFERENCE_HINTS = (
    "lang",
    "locale",
    "currency",
    "theme",
    "region",
    "country",
)


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


def build_cookie_findings(scan_data: dict, site_url: str) -> list[dict]:
    reject_cookies = scan_data.get("reject", {}).get("cookies", [])
    comparison = scan_data.get("comparison", {})
    reject_only = set(comparison.get("reject_only_cookies", []))
    common = set(comparison.get("common_cookies", []))

    findings = []
    seen = set()
    for cookie in sorted(reject_cookies, key=lambda item: (_cookie_domain(item), _cookie_name(item))):
        key = _cookie_key(cookie)
        if key in seen:
            continue
        seen.add(key)
        if key in reject_only:
            presence = "only_after_reject"
        elif key in common:
            presence = "also_after_accept"
        else:
            presence = "after_reject"
        findings.append(classify_cookie_finding(cookie, site_url, presence))

    return findings


def classify_cookie_finding(cookie: dict, site_url: str, presence: str = "after_reject") -> dict:
    name = _cookie_name(cookie)
    domain = _cookie_domain(cookie)
    rule = _match_cookie_rule(name)
    tracker_info = is_tracker(domain)
    party = _party(domain, site_url)

    category = rule["category"] if rule else "unknown"
    purpose = rule["purpose"] if rule else "Purpose could not be identified from known cookie patterns"
    severity = rule["severity"] if rule else "low"
    confidence = rule["confidence"] if rule else "low"
    evidence = []

    if rule:
        evidence.append(rule["purpose"])
    if tracker_info:
        category = _normalize_tracker_category(tracker_info.get("category"), category)
        purpose = tracker_info.get("data_collected") or purpose
        severity = "high"
        confidence = "high"
        evidence.append(f"Cookie domain matches known tracker service: {tracker_info.get('company', domain)}")
    if not rule and not tracker_info:
        category, purpose, severity, confidence = _heuristic_cookie_category(name, party)
        evidence.append(purpose)
    if cookie.get("secure") is False:
        severity = "medium" if severity == "low" else severity
        evidence.append("Cookie is missing the Secure flag")
    if cookie.get("sameSite") in (None, "None") and cookie.get("secure") is False:
        severity = "medium" if severity == "low" else severity
        evidence.append("Cross-site cookie lacks Secure protection")

    status = _finding_status(category, severity)
    legal_refs = _legal_refs(category, status)

    return {
        "name": cookie.get("name"),
        "domain": cookie.get("domain"),
        "path": cookie.get("path"),
        "secure": cookie.get("secure"),
        "httpOnly": cookie.get("httpOnly"),
        "sameSite": cookie.get("sameSite"),
        "category": category,
        "party": party,
        "severity": severity,
        "confidence": confidence,
        "active_after_reject": True,
        "presence": presence,
        "status": status,
        "purpose": purpose,
        "evidence": "; ".join(dict.fromkeys(evidence)),
        "legal_assessment": _legal_assessment(category, status),
        "legal_refs": legal_refs,
        "potentially_implicated_guidelines": legal_refs,
        "likely_reason": _likely_reason(category, party, status),
        "recommended_action": _recommended_action(category, status),
        "value_omitted": True,
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


def _match_cookie_rule(name: str) -> dict | None:
    if name in COOKIE_NAME_RULES:
        return COOKIE_NAME_RULES[name]
    for prefix, category, purpose, severity, confidence in PREFIX_RULES:
        if name.startswith(prefix):
            return {
                "category": category,
                "purpose": purpose,
                "severity": severity,
                "confidence": confidence,
            }
    return None


def _heuristic_cookie_category(name: str, party: str) -> tuple[str, str, str, str]:
    if any(token in name for token in NECESSARY_HINTS):
        return (
            "strictly_necessary",
            "Likely supports session, security, or consent-state functionality",
            "low",
            "medium",
        )
    if any(token in name for token in PREFERENCE_HINTS):
        return (
            "preferences",
            "Likely remembers a user preference such as language, region, or display setting",
            "medium",
            "medium",
        )
    if party == "third_party":
        return (
            "unknown",
            "Third-party cookie remained after rejection, but its purpose is not in the local rule set",
            "medium",
            "low",
        )
    return (
        "unknown",
        "First-party cookie remained after rejection, but its purpose is not in the local rule set",
        "low",
        "low",
    )


def _normalize_tracker_category(tracker_category: str | None, fallback: str) -> str:
    category = (tracker_category or "").lower()
    if category == "social":
        return "social_media"
    if category in {"advertising", "analytics", "content"}:
        return "tag_manager" if category == "content" else category
    return fallback


def _finding_status(category: str, severity: str) -> str:
    if category in {"analytics", "advertising", "social_media"}:
        return "potential_consent_issue"
    if category == "tag_manager":
        return "needs_review"
    if severity == "medium":
        return "needs_review"
    if category in {"strictly_necessary", "security"}:
        return "appears_acceptable"
    return "needs_review"


def _legal_assessment(category: str, status: str) -> str:
    if status == "potential_consent_issue":
        return (
            "This looks like a non-essential cookie that normally requires prior consent. "
            "Seeing it after Reject is evidence of a potential consent problem."
        )
    if status == "appears_acceptable":
        return (
            "This appears consistent with cookies that can remain active after rejection, "
            "such as consent-state, security, or session support."
        )
    if category == "preferences":
        return "Preference cookies may require consent unless they are strictly necessary for a user-requested setting."
    return "The scanner cannot confirm the purpose, so a privacy owner should review whether it is necessary before consent."


def _legal_refs(category: str, status: str) -> list[str]:
    if status == "potential_consent_issue":
        return [
            "ePrivacy Directive Art. 5(3)",
            "GDPR Art. 5(1)(a)",
            "GDPR Art. 6(1)(a)",
            "GDPR Art. 7",
        ]
    if status == "appears_acceptable":
        return [
            "ePrivacy Directive Art. 5(3) essential-cookie exemption",
            "GDPR Art. 5(1)(a)",
        ]
    if category == "preferences":
        return [
            "ePrivacy Directive Art. 5(3)",
            "GDPR Art. 5(1)(a)",
            "GDPR Art. 7",
        ]
    return [
        "ePrivacy Directive Art. 5(3)",
        "GDPR Art. 5(1)(a)",
        "GDPR Art. 6",
    ]


def _likely_reason(category: str, party: str, status: str) -> str:
    if status == "potential_consent_issue" and category == "advertising":
        return "A marketing tag, conversion pixel, or ad platform script may still be firing before the consent banner blocks it."
    if status == "potential_consent_issue" and category == "analytics":
        return "An analytics tag may load before consent state is applied, or the tag manager trigger is not tied to opt-in consent."
    if status == "potential_consent_issue" and category == "social_media":
        return "A social embed or pixel may be setting identifiers independently of the cookie banner."
    if status == "appears_acceptable":
        return "The site may keep this cookie to remember the rejection choice or support essential security/session behavior."
    if party == "third_party":
        return "A third-party script may be setting this cookie directly, outside the consent platform's blocking rules."
    return "The cookie may be set by first-party application code that is not yet mapped to a consent category."


def _recommended_action(category: str, status: str) -> str:
    if status == "potential_consent_issue":
        return "Block this cookie or its parent tag until the visitor gives explicit opt-in consent, then rescan."
    if status == "appears_acceptable":
        return "Document why this cookie is necessary and keep its value out of analytics or advertising workflows."
    if category == "preferences":
        return "Confirm this preference is user-requested and necessary; otherwise place it behind consent."
    return "Map this cookie to a consent category, confirm its purpose, and block it before consent if it is not essential."


def _party(cookie_domain: str, site_url: str) -> str:
    site_host = urlparse(site_url).netloc.lower().lstrip("www.")
    cookie_root = _root_domain(cookie_domain)
    site_root = _root_domain(site_host)
    if cookie_root and site_root and cookie_root == site_root:
        return "first_party"
    return "third_party"


def _root_domain(domain: str) -> str:
    cleaned = (domain or "").lower().lstrip(".").lstrip("www.")
    parts = cleaned.split(".")
    if len(parts) <= 2:
        return cleaned
    return ".".join(parts[-2:])


def _cookie_key(cookie: dict) -> str:
    return f"{cookie.get('domain', '')}|{cookie.get('name', '')}"


def _cookie_name(cookie: dict) -> str:
    return (cookie.get("name") or "").lower()


def _cookie_domain(cookie: dict) -> str:
    return (cookie.get("domain") or "").lower().lstrip(".").lstrip("www.")
