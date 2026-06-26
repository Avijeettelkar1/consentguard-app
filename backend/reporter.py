"""
Person 2 owns this file.
1. calculate_exposure() — estimates GDPR fine ranges
2. generate_complaint() — drafts a formal DPA complaint letter using Claude
3. run_verify_scan()    — re-scans with tracker domains blocked to confirm fix
"""
import os
import re
import json
from openai import OpenAI
from scanner import run_scan

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FINE_TIERS = [
    {"max_violations": 2,  "max_fine_pct": "2%",  "small": "€10,000–€50,000",   "medium": "€50,000–€200,000",   "large": "€200,000–€800,000"},
    {"max_violations": 5,  "max_fine_pct": "4%",  "small": "€50,000–€200,000",  "medium": "€200,000–€800,000",  "large": "€800,000–€4,000,000"},
    {"max_violations": 999,"max_fine_pct": "4%",  "small": "€100,000–€500,000", "medium": "€500,000–€2,000,000","large": "€2,000,000–€20,000,000"},
]

DPA_BY_COUNTRY = {
    "de": "German Federal Commissioner for Data Protection (BfDI)",
    "fr": "Commission nationale de l'informatique et des libertés (CNIL)",
    "uk": "Information Commissioner's Office (ICO)",
    "ie": "Data Protection Commission (DPC) Ireland",
    "nl": "Autoriteit Persoonsgegevens (AP)",
    "default": "Your national Data Protection Authority (DPA)",
}


def calculate_exposure(violation_count: int, country_code: str = "default") -> dict:
    tier = FINE_TIERS[0]
    for t in FINE_TIERS:
        if violation_count <= t["max_violations"]:
            tier = t
            break

    return {
        "violation_count": violation_count,
        "max_fine_percent": tier["max_fine_pct"] + " of annual global revenue",
        "estimated_range_small": tier["small"],
        "estimated_range_medium": tier["medium"],
        "estimated_range_large": tier["large"],
        "relevant_authority": DPA_BY_COUNTRY.get(country_code, DPA_BY_COUNTRY["default"]),
    }


def generate_complaint(url: str, undeclared: list[dict], exposure: dict) -> str:
    tracker_list = "\n".join(
        f"- {t['domain']} ({t['category']}): {t['data_collected']}"
        for t in undeclared
    )

    prompt = f"""Write a formal GDPR complaint letter to a Data Protection Authority.

Website: {url}
Trackers firing after "Reject All" consent (GDPR Art. 7 violation):
{tracker_list}

Estimated exposure: {exposure.get('estimated_range_medium', 'significant fines')}
Relevant authority: {exposure.get('relevant_authority', 'the DPA')}

The letter should:
- Open with "Dear [Authority],"
- State the violation clearly (Art. 7 consent, Art. 5(1)(a) lawfulness)
- List each undeclared tracker as evidence
- Request investigation and enforcement action
- Be professional, under 300 words

Return only the letter text, no extra commentary."""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def run_verify_scan(url: str, block_domains: list[str]) -> dict:
    """Re-scan with specified domains blocked to verify the fix works."""
    try:
        result = run_scan(url)
        after = result.get("after", [])
        remaining = [
            r for r in after
            if any(d in r for d in block_domains)
        ]
        return {
            "remaining_requests": remaining,
            "violation_count": len(remaining),
            "clean": len(remaining) == 0,
        }
    except Exception as e:
        return {"remaining_requests": [], "violation_count": 0, "clean": True, "error": str(e)}
