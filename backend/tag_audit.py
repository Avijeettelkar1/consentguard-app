import re
from urllib.parse import parse_qs, urlparse

PAYLOAD_KINDS = {
    "ga4_event",
    "universal_analytics_event",
    "google_ads_conversion",
    "doubleclick_ad_request",
    "bing_ads_event",
    "meta_pixel_event",
}


def audit_tags(scan_data: dict) -> dict:
    if not scan_data.get("clicked_accept") or not scan_data.get("clicked_reject"):
        return {
            "verdict": "consent_controls_not_clicked",
            "severity": "inconclusive",
            "summary": "Accept and/or reject controls were not clicked, so tag-level consent comparison is inconclusive.",
            "gtm_containers": {"accept": [], "reject": [], "html": []},
            "accept_payload_count": 0,
            "reject_payload_count": 0,
            "blocked_by_reject": [],
            "still_firing_after_reject": [],
            "reject_only_payloads": [],
            "loader_evidence_after_reject": [],
            "note": "Fix selector coverage for this consent banner before interpreting compliance results.",
        }

    accept_records = scan_data.get("accept", {}).get("post_consent_request_records", [])
    reject_records = scan_data.get("reject", {}).get("post_consent_request_records", [])
    page_html = scan_data.get("page_html_for_fallback", "")

    accept_evidence = [_classify_request(record) for record in accept_records]
    reject_evidence = [_classify_request(record) for record in reject_records]
    accept_evidence = [item for item in accept_evidence if item]
    reject_evidence = [item for item in reject_evidence if item]

    accept_payloads = [item for item in accept_evidence if item["kind"] in PAYLOAD_KINDS]
    reject_payloads = [item for item in reject_evidence if item["kind"] in PAYLOAD_KINDS]
    accept_payload_signatures = {_signature(item) for item in accept_payloads}
    reject_payload_signatures = {_signature(item) for item in reject_payloads}

    accept_containers = sorted({
        item["container_id"]
        for item in accept_evidence
        if item.get("container_id")
    })
    reject_containers = sorted({
        item["container_id"]
        for item in reject_evidence
        if item.get("container_id")
    })
    html_containers = sorted(set(re.findall(r"\bGTM-[A-Z0-9]+", page_html or "", flags=re.I)))

    blocked_payloads = [
        item
        for item in accept_payloads
        if _signature(item) not in reject_payload_signatures
    ]
    unexpected_reject_payloads = [
        item
        for item in reject_payloads
        if _signature(item) not in accept_payload_signatures
    ]

    if reject_payloads:
        verdict = "non_essential_payloads_after_reject"
        severity = "high"
        summary = "Tracking or advertising payload requests were observed after reject."
    elif any(item["kind"] == "gtm_container" for item in reject_evidence):
        verdict = "gtm_loader_after_reject_only"
        severity = "needs_review"
        summary = "GTM loaded after reject, but no GA/Ads/Bing/Meta payload was observed after reject."
    else:
        verdict = "no_tracking_payloads_after_reject"
        severity = "low"
        summary = "No known analytics or advertising payloads were observed after reject."

    return {
        "verdict": verdict,
        "severity": severity,
        "summary": summary,
        "gtm_containers": {
            "accept": accept_containers,
            "reject": reject_containers,
            "html": html_containers,
        },
        "accept_payload_count": len(accept_payloads),
        "reject_payload_count": len(reject_payloads),
        "blocked_by_reject": blocked_payloads,
        "still_firing_after_reject": reject_payloads,
        "reject_only_payloads": unexpected_reject_payloads,
        "loader_evidence_after_reject": [
            item for item in reject_evidence if item["kind"] in {"gtm_container", "gtag_library"}
        ],
        "note": (
            "A GTM loader request is not automatically a GDPR violation. "
            "The strongest evidence is downstream analytics or advertising payloads after reject."
        ),
    }


def filter_domain_violations_with_tag_audit(violations: list[dict], audit: dict) -> list[dict]:
    """Avoid overclaiming GTM loader-only evidence as a hard violation."""
    filtered = []
    for violation in violations:
        domain = (violation.get("domain") or "").lower()
        category = (violation.get("category") or "").lower()

        if category == "content" or domain in {"fonts.gstatic.com", "fonts.googleapis.com"}:
            filtered.append({
                **violation,
                "declared": True,
                "violation_reason": (
                    "Static content/font request observed after reject. Treat as low-risk infrastructure unless it sets identifiers "
                    "or triggers analytics/advertising payloads."
                ),
                "needs_review": True,
            })
            continue

        if audit.get("verdict") == "gtm_loader_after_reject_only" and "googletagmanager.com" in domain:
            filtered.append({
                **violation,
                "declared": True,
                "violation_reason": (
                    "GTM loader observed after reject, but no downstream analytics or advertising payload was observed. "
                    "Treat as needs-review infrastructure, not a confirmed tracking violation."
                ),
                "needs_review": True,
            })
            continue

        filtered.append(violation)
    return filtered


def _classify_request(record: dict) -> dict | None:
    url = record.get("url") or ""
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    path = parsed.path.lower()
    params = parse_qs(parsed.query)
    method = record.get("method") or "GET"
    resource_type = record.get("resource_type") or "unknown"

    if host == "googletagmanager.com" and path.endswith("/gtm.js"):
        container_id = _first(params, "id")
        return _evidence("gtm_container", url, host, method, resource_type, container_id=container_id)

    if host == "googletagmanager.com" and path.endswith("/gtag/js"):
        measurement_id = _first(params, "id")
        return _evidence("gtag_library", url, host, method, resource_type, target_id=measurement_id)

    if host.endswith("google-analytics.com") and path.endswith("/g/collect"):
        return _evidence(
            "ga4_event",
            url,
            host,
            method,
            resource_type,
            target_id=_first(params, "tid"),
            event_name=_first(params, "en") or "page_view",
            consent_state=_first(params, "gcs") or _first(params, "gcd"),
        )

    if host.endswith("google-analytics.com") and path.endswith("/collect"):
        return _evidence(
            "universal_analytics_event",
            url,
            host,
            method,
            resource_type,
            target_id=_first(params, "tid"),
            event_name=_first(params, "t"),
            consent_state=_first(params, "gcs") or _first(params, "gcd"),
        )

    if host in {"googleads.g.doubleclick.net", "www.googleadservices.com"} and (
        "/pagead/conversion" in path or "/pagead/1p-conversion" in path
    ):
        return _evidence(
            "google_ads_conversion",
            url,
            host,
            method,
            resource_type,
            target_id=_first(params, "id") or _first(params, "label"),
            event_name="conversion",
            consent_state=_first(params, "gcs") or _first(params, "gcd"),
        )

    if host.endswith("doubleclick.net"):
        return _evidence(
            "doubleclick_ad_request",
            url,
            host,
            method,
            resource_type,
            target_id=_first(params, "id") or _first(params, "src"),
            event_name="ad_request",
            consent_state=_first(params, "gcs") or _first(params, "gcd"),
        )

    if host == "bat.bing.com" and ("/action" in path or path.endswith("/bat.js")):
        return _evidence(
            "bing_ads_event",
            url,
            host,
            method,
            resource_type,
            target_id=_first(params, "ti"),
            event_name=_first(params, "evt") or "page_load",
        )

    if host.endswith("facebook.com") and path == "/tr/":
        return _evidence(
            "meta_pixel_event",
            url,
            host,
            method,
            resource_type,
            target_id=_first(params, "id"),
            event_name=_first(params, "ev") or "pixel_event",
        )

    return None


def _evidence(
    kind: str,
    url: str,
    domain: str,
    method: str,
    resource_type: str,
    target_id: str | None = None,
    event_name: str | None = None,
    container_id: str | None = None,
    consent_state: str | None = None,
) -> dict:
    return {
        "kind": kind,
        "domain": domain,
        "target_id": target_id,
        "container_id": container_id,
        "event_name": event_name,
        "consent_state": consent_state,
        "method": method,
        "resource_type": resource_type,
        "url": _redact_url(url),
    }


def _signature(item: dict) -> tuple:
    return (
        item.get("kind"),
        item.get("domain"),
        item.get("target_id"),
        item.get("event_name"),
    )


def _first(params: dict, key: str) -> str | None:
    value = params.get(key)
    if not value:
        return None
    return value[0]


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    safe_keys = {
        "id",
        "tid",
        "en",
        "t",
        "ti",
        "evt",
        "ev",
        "label",
        "gcs",
        "gcd",
        "src",
    }
    safe_params = []
    for key in safe_keys:
        if key in params:
            safe_params.append(f"{key}={params[key][0]}")
    query = "&".join(sorted(safe_params))
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{query}" if query else "")
