"""
Person 2 owns this file.
GPT-4o generates:
  policy_fix  — HTML paragraph disclosing each undeclared tracker
  banner_fix  — platform-specific steps to block trackers on reject
"""
import os
import re
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_fixes(
    undeclared: list[dict],
    platform: str,
    site_url: str,
) -> dict:
    if not undeclared:
        return {"policy_fix": "", "banner_fix": "No violations found — nothing to fix."}

    tracker_list = "\n".join(
        f"- {t['domain']} (category: {t['category']}): {t['data_collected']}"
        for t in undeclared
    )

    prompt = f"""You are a GDPR legal and technical advisor.

Website: {site_url}
Consent platform: {platform or "unknown"}

After the user clicked "Reject All", these undeclared third-party trackers still fired:
{tracker_list}

Generate two precise fixes:

1. policy_fix: A ready-to-paste HTML snippet (use <p> and <ul><li> tags) to add to the cookie policy.
   It must explicitly name each tracker domain, its company, purpose, data collected, and legal basis under GDPR Art. 6(1)(a).

2. banner_fix: Numbered step-by-step technical instructions (plain text) specific to "{platform or 'the consent platform'}"
   explaining exactly how to configure it so these scripts are blocked when the user rejects.
   Be platform-specific — reference actual dashboard sections, menu names, toggle names where known.

Return ONLY valid JSON, no markdown fences:
{{
  "policy_fix": "<p>...</p><ul>...</ul>",
  "banner_fix": "1. ...\\n2. ...\\n3. ..."
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"policy_fix": raw, "banner_fix": ""}


if __name__ == "__main__":
    mock = [
        {"domain": "facebook.net", "category": "advertising", "data_collected": "Cross-site ad tracking"},
        {"domain": "bat.bing.com", "category": "advertising", "data_collected": "Microsoft ad conversion"},
    ]
    fixes = generate_fixes(mock, "OneTrust", "https://example.com")
    print(fixes["policy_fix"][:400])
    print("---")
    print(fixes["banner_fix"][:400])
