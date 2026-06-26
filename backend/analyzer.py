"""
Person 2 owns this file.
1. find_violations()    — cross-refs network requests against tracker DB
2. fetch_cookie_policy() — fetches and strips HTML from the cookie policy page
3. analyze_violations()  — GPT-4o reads policy text and determines which trackers are declared
"""
import os
import re
import json
import requests
from urllib.parse import urlparse
from openai import OpenAI
from tracker_db import is_tracker

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_STRIP_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


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
        resp = requests.get(policy_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = _STRIP_TAGS.sub(" ", resp.text)
        text = _WHITESPACE.sub(" ", text).strip()
        return text[:10000]
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
        f"- {v['domain']} (category: {v['category']}, company: {v.get('company','')}, collects: {v['data_collected']})"
        for v in violations
    )

    prompt = f"""You are a GDPR compliance auditor with deep expertise in cookie law.

A website's "Reject All" cookie button was clicked. Despite this, the following third-party trackers
still fired network requests — a potential GDPR Article 7 violation:

{tracker_list}

The website's cookie policy text (may be partial or empty):
\"\"\"
{policy_text[:5000] if policy_text else "(cookie policy not found or inaccessible)"}
\"\"\"

For each tracker domain, determine:
1. Is this tracker or its parent company EXPLICITLY mentioned/disclosed in the cookie policy?
   Be thorough — "Google services" covers googlesyndication.com, "analytics tools" alone does NOT.
2. The specific GDPR violation reason if undeclared.

Return ONLY valid JSON — no markdown, no explanation:
{{
  "violations": [
    {{
      "domain": "example.com",
      "category": "advertising",
      "data_collected": "description",
      "declared": false,
      "violation_reason": "Not mentioned in cookie policy and fires after Reject All (GDPR Art. 7 + Art. 5(1)(a))"
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    # strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed = json.loads(match.group()) if match else {"violations": []}

    all_v = parsed.get("violations", [])
    undeclared = [v for v in all_v if not v.get("declared")]
    declared   = [v for v in all_v if v.get("declared")]
    return {"violations": all_v, "undeclared": undeclared, "declared": declared}


if __name__ == "__main__":
    mock_requests = [
        "https://connect.facebook.net/en_US/fbevents.js",
        "https://www.google-analytics.com/analytics.js",
        "https://bat.bing.com/bat.js",
    ]
    violations = find_violations(mock_requests)
    print(f"Found {len(violations)} tracker violations")
    analysis = analyze_violations(violations, policy_text="This website uses Google Analytics only.")
    print(json.dumps(analysis, indent=2))
