"""
Person 2 owns this file.
1. find_violations()   — cross-refs network requests against tracker DB
2. fetch_cookie_policy() — fetches and extracts text from the site's cookie policy
3. analyze_violations()  — asks Claude whether each tracker is declared in the policy
"""
import os
import re
import json
from urllib.parse import urlparse
import requests
from openai import OpenAI
from tracker_db import is_tracker

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def find_violations(requests_list: list[str]) -> list[dict]:
    seen = set()
    violations = []
    for url in requests_list:
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if domain in seen:
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


def fetch_cookie_policy(policy_url: str) -> str:
    if not policy_url:
        return ""
    try:
        resp = requests.get(policy_url, timeout=10)
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]
    except Exception:
        return ""


def analyze_violations(
    violations: list[dict],
    policy_text: str,
    page_html: str = "",
) -> dict:
    if not violations:
        return {"violations": [], "undeclared": [], "declared": []}

    tracker_list = "\n".join(
        f"- {v['domain']} ({v['category']}): {v['data_collected']}"
        for v in violations
    )

    prompt = f"""You are a GDPR compliance auditor.

A website's cookie banner was clicked "Reject All". Despite this, the following third-party trackers fired network requests:

{tracker_list}

The website's cookie policy text (may be partial):
\"\"\"
{policy_text[:4000] if policy_text else "(not available)"}
\"\"\"

For each tracker domain, determine:
1. Is it explicitly declared in the cookie policy? (true/false)
2. What is the GDPR legal basis violation if undeclared?

Return ONLY valid JSON in this exact format:
{{
  "violations": [
    {{
      "domain": "example.com",
      "category": "advertising",
      "data_collected": "...",
      "declared": false,
      "violation_reason": "Fires after reject, not listed in policy"
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed = json.loads(match.group()) if match else {"violations": []}

    all_v = parsed.get("violations", [])
    undeclared = [v for v in all_v if not v.get("declared")]
    declared = [v for v in all_v if v.get("declared")]

    return {"violations": all_v, "undeclared": undeclared, "declared": declared}


if __name__ == "__main__":
    mock_requests = [
        "https://connect.facebook.net/en_US/fbevents.js",
        "https://www.google-analytics.com/analytics.js",
        "https://cdn.segment.com/analytics.js/v1/test/analytics.min.js",
        "https://bat.bing.com/bat.js",
        "https://static.ads-twitter.com/uwt.js",
    ]
    violations = find_violations(mock_requests)
    print(f"Found {len(violations)} tracker violations")
    analysis = analyze_violations(violations, policy_text="This website uses Google Analytics only.")
    print(json.dumps(analysis, indent=2))
