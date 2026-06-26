import html
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()


def generate_fixes(
    undeclared: list[dict],
    platform: str | None,
    site_url: str,
) -> dict:
    if not undeclared:
        return {
            "policy_fix": "",
            "banner_fix": "No undeclared trackers were found. Keep consent categories and script blocking rules under regular review.",
        }

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        try:
            return _generate_with_claude(api_key, undeclared, platform or "unknown", site_url)
        except Exception:
            pass

    return _generate_locally(undeclared, platform or "unknown")


def _generate_with_claude(api_key: str, undeclared: list[dict], platform: str, site_url: str) -> dict:
    import anthropic

    tracker_list = "\n".join(
        f"- {t['domain']} ({t['category']}): {t['data_collected']}"
        for t in undeclared
    )

    prompt = f"""You are a GDPR legal and technical advisor.

The website {site_url} uses the consent management platform "{platform}".
After clicking "Reject All", these undeclared trackers still fired:

{tracker_list}

Generate:
1. policy_fix: a ready-to-paste HTML paragraph that discloses each tracker, purpose, and legal basis.
2. banner_fix: numbered plain-text steps for configuring "{platform}" so these trackers are blocked before consent.

Return only valid JSON:
{{
  "policy_fix": "<p>...</p>",
  "banner_fix": "1. ...\\n2. ..."
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"policy_fix": html.escape(raw), "banner_fix": ""}


def _generate_locally(undeclared: list[dict], platform: str) -> dict:
    services = []
    for tracker in undeclared:
        domain = html.escape(tracker["domain"])
        category = html.escape(tracker.get("category", "tracking"))
        purpose = html.escape(tracker.get("data_collected", "Collects user data"))
        company = html.escape(tracker.get("company") or domain)
        services.append(f"{company} ({domain}) for {category}: {purpose}")

    policy_fix = (
        "<p>We use the following third-party services only where you have given prior consent: "
        + "; ".join(services)
        + ". These services may process identifiers, device information, page views, and interaction events. "
        + "They must remain disabled until the user grants explicit consent and can be withdrawn at any time.</p>"
    )

    domains = ", ".join(t["domain"] for t in undeclared)
    banner_fix = "\n".join([
        f"1. Open the {platform} administration dashboard or tag manager connected to the banner.",
        f"2. Find these domains/scripts: {domains}.",
        "3. Move advertising trackers to the marketing/targeting category and analytics trackers to the analytics category.",
        "4. Configure each script to load only after an explicit opt-in signal, not on initial page load.",
        "5. Ensure the Reject All path disables every non-essential category and clears queued tags.",
        "6. Republish the banner, clear CDN/cache layers, and re-run ConsentGuard to confirm zero post-reject tracker requests.",
    ])

    return {"policy_fix": policy_fix, "banner_fix": banner_fix}


if __name__ == "__main__":
    mock_undeclared = [
        {"domain": "facebook.net", "category": "advertising", "data_collected": "Tracks user behavior for ad targeting"},
        {"domain": "bat.bing.com", "category": "advertising", "data_collected": "Microsoft ad conversion tracking"},
    ]
    print(json.dumps(generate_fixes(mock_undeclared, "OneTrust", "https://example.com"), indent=2))
