"""
Person 1 owns this file.
Downloads and caches the Disconnect.me tracker list.
Returns a dict of {domain: {category, name}} for fast lookup.
"""
import json
import os
import requests

DISCONNECT_URL = "https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json"
CACHE_FILE = "/tmp/disconnect_trackers.json"

_tracker_cache: dict = {}


def get_tracker_domains() -> dict:
    global _tracker_cache
    if _tracker_cache:
        return _tracker_cache

    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            _tracker_cache = json.load(f)
        return _tracker_cache

    print("Downloading Disconnect.me tracker list...")
    resp = requests.get(DISCONNECT_URL, timeout=15)
    resp.raise_for_status()
    raw = resp.json()

    trackers = {}
    for category, companies in raw.get("categories", {}).items():
        for company_block in companies:
            for company_name, domains_map in company_block.items():
                for main_domain, subdomains in domains_map.items():
                    all_domains = [main_domain] + (subdomains if isinstance(subdomains, list) else [])
                    for d in all_domains:
                        trackers[d.lower()] = {
                            "category": category.lower(),
                            "company": company_name,
                            "data_collected": _describe(category),
                        }

    with open(CACHE_FILE, "w") as f:
        json.dump(trackers, f)

    _tracker_cache = trackers
    print(f"Loaded {len(trackers)} tracker domains.")
    return trackers


def _describe(category: str) -> str:
    descriptions = {
        "advertising": "Tracks user behavior across websites for ad targeting",
        "analytics": "Collects user interaction and page view data",
        "social": "Tracks social sharing and embeds user identity",
        "disconnect": "General tracking / fingerprinting",
        "content": "Content delivery with embedded tracking",
    }
    return descriptions.get(category.lower(), "Collects and transmits user data")


def is_tracker(domain: str) -> dict | None:
    db = get_tracker_domains()
    domain = domain.lower().lstrip("www.")
    if domain in db:
        return db[domain]
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in db:
            return db[parent]
    return None


if __name__ == "__main__":
    db = get_tracker_domains()
    print(f"Total trackers: {len(db)}")
    test = is_tracker("connect.facebook.net")
    print(f"Facebook: {test}")
