import os

from dotenv import load_dotenv

load_dotenv()

FINE_TIERS = [
    {"max_violations": 2, "max_fine_pct": "2%", "small": "EUR 10,000-EUR 50,000", "medium": "EUR 50,000-EUR 200,000", "large": "EUR 200,000-EUR 800,000"},
    {"max_violations": 5, "max_fine_pct": "4%", "small": "EUR 50,000-EUR 200,000", "medium": "EUR 200,000-EUR 800,000", "large": "EUR 800,000-EUR 4,000,000"},
    {"max_violations": 999, "max_fine_pct": "4%", "small": "EUR 100,000-EUR 500,000", "medium": "EUR 500,000-EUR 2,000,000", "large": "EUR 2,000,000-EUR 20,000,000"},
]

DPA_BY_COUNTRY = {
    "de": "German Federal Commissioner for Data Protection (BfDI)",
    "fr": "Commission nationale de l'informatique et des libertes (CNIL)",
    "uk": "Information Commissioner's Office (ICO)",
    "ie": "Data Protection Commission (DPC) Ireland",
    "nl": "Autoriteit Persoonsgegevens (AP)",
    "default": "Your national Data Protection Authority (DPA)",
}


def calculate_exposure(violation_count: int, country_code: str = "default") -> dict:
    tier = FINE_TIERS[-1]
    for candidate in FINE_TIERS:
        if violation_count <= candidate["max_violations"]:
            tier = candidate
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
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        try:
            return _generate_complaint_with_claude(api_key, url, undeclared, exposure)
        except Exception:
            pass

    return _generate_complaint_locally(url, undeclared, exposure)


def _generate_complaint_with_claude(api_key: str, url: str, undeclared: list[dict], exposure: dict) -> str:
    import anthropic

    tracker_list = "\n".join(
        f"- {t['domain']} ({t['category']}): {t['data_collected']}"
        for t in undeclared
    )

    prompt = f"""Write a formal GDPR complaint letter to a Data Protection Authority.

Website: {url}
Trackers firing after "Reject All":
{tracker_list}

Estimated exposure: {exposure.get('estimated_range_medium', 'significant fines')}
Relevant authority: {exposure.get('relevant_authority', 'the DPA')}

The letter should cite GDPR Article 7 and Article 5(1)(a), request investigation and enforcement, and stay under 300 words.
Return only the letter text."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _generate_complaint_locally(url: str, undeclared: list[dict], exposure: dict) -> str:
    tracker_lines = "\n".join(
        f"- {t['domain']} ({t.get('category', 'tracking')}): {t.get('data_collected', 'tracking request observed')}"
        for t in undeclared
    ) or "- No undeclared trackers were identified."

    return (
        f"Dear {exposure.get('relevant_authority', 'Data Protection Authority')},\n\n"
        f"I submit this complaint regarding the website {url}.\n\n"
        "After selecting the Reject All option in the cookie banner, the scanner observed third-party tracking requests that appear to continue without valid consent:\n\n"
        f"{tracker_lines}\n\n"
        "This may breach GDPR Article 7, because consent must be freely given and respected when refused, and Article 5(1)(a), because processing must be lawful, fair, and transparent. "
        f"The estimated enforcement exposure for a medium-sized organization is {exposure.get('estimated_range_medium', 'significant')}.\n\n"
        "I request that the authority investigate whether these trackers are activated without a valid legal basis and require corrective measures where appropriate.\n\n"
        "Sincerely,\nA concerned user"
    )


def run_verify_scan(url: str, block_domains: list[str]) -> dict:
    if not block_domains:
        return {"remaining_requests": [], "violation_count": 0, "clean": True}

    try:
        from scanner import run_scan

        result = run_scan(url)
        after = result.get("after", [])
        remaining = [
            request_url
            for request_url in after
            if any(domain in request_url for domain in block_domains)
        ]
        return {
            "remaining_requests": remaining,
            "violation_count": len(remaining),
            "clean": len(remaining) == 0,
        }
    except Exception as exc:
        return {
            "remaining_requests": [],
            "violation_count": 0,
            "clean": False,
            "error": str(exc),
        }
