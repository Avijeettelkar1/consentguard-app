import json
import os
import re
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from tracker_db import is_tracker

load_dotenv()


def find_violations(requests_list: list[str]) -> list[dict]:
    seen = set()
    violations = []

    for request_url in requests_list:
        domain = urlparse(request_url).netloc.lower().lstrip("www.")
        if not domain or domain in seen:
            continue
        seen.add(domain)

        info = is_tracker(domain)
        if info:
            violations.append({
                "domain": domain,
                "category": info["category"],
                "company": info.get("company", ""),
                "data_collected": info["data_collected"],
            })

    return violations


def fetch_cookie_policy(policy_url: str | None) -> str:
    if not policy_url:
        return ""

    try:
        response = requests.get(
            policy_url,
            timeout=10,
            headers={"User-Agent": "ConsentGuard/1.0 compliance scanner"},
        )
        response.raise_for_status()
        text = re.sub(r"<script\b.*?</script>", " ", response.text, flags=re.I | re.S)
        text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()[:8000]
    except Exception:
        return ""


def analyze_violations(
    violations: list[dict],
    policy_text: str,
    page_html: str = "",
) -> dict:
    if not violations:
        return {"violations": [], "undeclared": [], "declared": []}

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        try:
            return _analyze_with_claude(api_key, violations, policy_text)
        except Exception:
            pass

    return _analyze_locally(violations, policy_text, page_html)


def _analyze_with_claude(api_key: str, violations: list[dict], policy_text: str) -> dict:
    import anthropic

    tracker_list = "\n".join(
        f"- {v['domain']} ({v['category']}): {v['data_collected']}"
        for v in violations
    )

    prompt = f"""You are a GDPR compliance auditor.

A website's cookie banner was clicked "Reject All". Despite this, the following third-party trackers fired network requests:

{tracker_list}

The website's cookie policy text may be partial:
\"\"\"
{policy_text[:4000] if policy_text else "(not available)"}
\"\"\"

For each tracker domain, determine whether it is explicitly declared in the cookie policy.

Return only valid JSON in this exact format:
{{
  "violations": [
    {{
      "domain": "example.com",
      "category": "advertising",
      "data_collected": "...",
      "declared": false,
      "violation_reason": "Fires after reject and is not listed in the policy"
    }}
  ]
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed = json.loads(match.group()) if match else {"violations": []}
    return _split_declared(parsed.get("violations", []))


def _analyze_locally(violations: list[dict], policy_text: str, page_html: str) -> dict:
    searchable = _normalize_text((policy_text or "") + " " + _strip_html(page_html or ""))
    analyzed = []

    for violation in violations:
        domain = violation["domain"]
        root_domain = _root_domain(domain)
        company = violation.get("company", "")
        declared = any(
            token and token in searchable
            for token in {
                domain.lower(),
                root_domain.lower(),
                company.lower(),
                company.lower().replace(" ", ""),
            }
        )

        analyzed.append({
            **violation,
            "declared": declared,
            "violation_reason": (
                "Fires after reject and appears in the available policy/page text"
                if declared
                else "Fires after reject and was not found in the available policy/page text"
            ),
        })

    return _split_declared(analyzed)


def _split_declared(violations: list[dict]) -> dict:
    undeclared = [v for v in violations if not v.get("declared")]
    declared = [v for v in violations if v.get("declared")]
    return {"violations": violations, "undeclared": undeclared, "declared": declared}


def _strip_html(html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _root_domain(domain: str) -> str:
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    return ".".join(parts[-2:])


if __name__ == "__main__":
    mock_requests = [
        "https://connect.facebook.net/en_US/fbevents.js",
        "https://www.google-analytics.com/analytics.js",
        "https://cdn.segment.com/analytics.js/v1/test/analytics.min.js",
        "https://bat.bing.com/bat.js",
        "https://static.ads-twitter.com/uwt.js",
    ]
    found = find_violations(mock_requests)
    print(f"Found {len(found)} tracker violations")
    print(json.dumps(analyze_violations(found, "This website uses Google Analytics only."), indent=2))
