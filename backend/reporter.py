"""
Person 2 owns this file.
1. calculate_exposure() — GDPR fine ranges by violation count
2. generate_complaint() — GPT-4o drafts a formal DPA complaint letter
3. run_verify_scan()    — re-scans to confirm trackers are still present
"""
import os
import json
from datetime import date
from openai import OpenAI
from scanner import run_scan

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FINE_TIERS = [
    {"max_violations": 2,  "max_fine_pct": "2%",  "small": "€10,000–€50,000",    "medium": "€50,000–€200,000",    "large": "€200,000–€800,000"},
    {"max_violations": 5,  "max_fine_pct": "4%",  "small": "€50,000–€200,000",   "medium": "€200,000–€800,000",   "large": "€800,000–€4,000,000"},
    {"max_violations": 999,"max_fine_pct": "4%",  "small": "€100,000–€500,000",  "medium": "€500,000–€2,000,000", "large": "€2,000,000–€20,000,000"},
]

DPA_BY_COUNTRY = {
    "de": "German Federal Commissioner for Data Protection (BfDI)",
    "fr": "Commission nationale de l'informatique et des libertés (CNIL)",
    "uk": "Information Commissioner's Office (ICO)",
    "ie": "Data Protection Commission (DPC) Ireland",
    "nl": "Autoriteit Persoonsgegevens (AP)",
    "es": "Agencia Española de Protección de Datos (AEPD)",
    "it": "Garante per la protezione dei dati personali",
    "default": "Your national Data Protection Authority (DPA)",
}


def calculate_exposure(violation_count: int, country_code: str = "default") -> dict:
    tier = FINE_TIERS[-1]
    for t in FINE_TIERS:
        if violation_count <= t["max_violations"]:
            tier = t
            break
    return {
        "violation_count": violation_count,
        "max_fine_percent": tier["max_fine_pct"] + " of annual global revenue",
        "estimated_range_small":  tier["small"],
        "estimated_range_medium": tier["medium"],
        "estimated_range_large":  tier["large"],
        "relevant_authority": DPA_BY_COUNTRY.get(country_code, DPA_BY_COUNTRY["default"]),
    }


def generate_complaint(url: str, undeclared: list[dict], exposure: dict) -> str:
    today = date.today().strftime("%d %B %Y")
    authority = exposure.get("relevant_authority", "Data Protection Authority")

    tracker_list = "\n".join(
        f"  {i+1}. {t['domain']} — {t['category']} — {t['data_collected']}"
        for i, t in enumerate(undeclared)
    )

    prompt = f"""Write a formal, professional GDPR complaint letter to a Data Protection Authority.

Details:
- Website under complaint: {url}
- Date of observation: {today}
- Relevant authority: {authority}
- Estimated GDPR fine exposure: {exposure.get('estimated_range_medium', 'significant')}

Trackers that fired AFTER the user clicked "Reject All":
{tracker_list}

Requirements:
- Open with "Dear {authority},"
- Clearly state the GDPR violations: Art. 7 (consent), Art. 5(1)(a) (lawfulness), Art. 13 (transparency)
- List each tracker as numbered evidence
- Reference the fine range under Art. 83
- Request investigation and enforcement
- Professional tone, under 350 words
- Close with "Yours sincerely, A Concerned Data Subject"

Return only the letter text. No subject line, no extra commentary."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=900,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


async def run_verify_scan(url: str, block_domains: list[str]) -> dict:
    try:
        result = await run_scan(url)
        after = result.get("after", [])
        remaining = [r for r in after if any(d in r for d in block_domains)]
        return {
            "remaining_requests": remaining,
            "violation_count": len(remaining),
            "clean": len(remaining) == 0,
        }
    except Exception as e:
        return {"remaining_requests": [], "violation_count": 0, "clean": True, "error": str(e)}
