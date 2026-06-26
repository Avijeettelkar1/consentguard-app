"""
Person 2 owns this file.
Given a list of undeclared trackers, asks Claude to generate:
1. policy_fix  — updated cookie policy paragraph to add
2. banner_fix  — step-by-step instructions to fix the consent platform config
"""
import os
import re
import json
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_fixes(
    undeclared: list[dict],
    platform: str,
    site_url: str,
) -> dict:
    if not undeclared:
        return {"policy_fix": "", "banner_fix": "No violations found — nothing to fix."}

    tracker_list = "\n".join(
        f"- {t['domain']} ({t['category']}): {t['data_collected']}"
        for t in undeclared
    )

    prompt = f"""You are a GDPR legal and technical advisor.

The website {site_url} uses the consent management platform "{platform}".
After clicking "Reject All", these undeclared trackers still fired:

{tracker_list}

Generate two fixes:

1. **policy_fix**: A ready-to-paste HTML paragraph (2-4 sentences) to add to their cookie policy that properly discloses each tracker, its purpose, and legal basis.

2. **banner_fix**: Step-by-step technical instructions (numbered list, plain text) for configuring "{platform}" so these trackers are blocked on reject. Be specific to the platform if known.

Return ONLY valid JSON:
{{
  "policy_fix": "<p>...</p>",
  "banner_fix": "1. ...\\n2. ...\\n3. ..."
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"policy_fix": raw, "banner_fix": ""}


if __name__ == "__main__":
    mock_undeclared = [
        {"domain": "facebook.net", "category": "advertising", "data_collected": "Tracks user behavior for ad targeting"},
        {"domain": "bat.bing.com", "category": "advertising", "data_collected": "Microsoft ad conversion tracking"},
    ]
    fixes = generate_fixes(mock_undeclared, "OneTrust", "https://example.com")
    print(fixes["policy_fix"][:500])
    print("---")
    print(fixes["banner_fix"][:500])
