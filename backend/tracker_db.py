import json
import os
import tempfile
import requests

DISCONNECT_URL = "https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json"
CACHE_FILE = os.path.join(tempfile.gettempdir(), "consentguard_disconnect_trackers.json")

_tracker_cache: dict = {}

FALLBACK_TRACKERS = {
    "google-analytics.com": {
        "category": "analytics",
        "company": "Google Analytics",
        "data_collected": "Collects page views, user interaction, and device metadata",
    },
    "googletagmanager.com": {
        "category": "analytics",
        "company": "Google Tag Manager",
        "data_collected": "Loads and coordinates analytics and advertising tags",
    },
    "doubleclick.net": {
        "category": "advertising",
        "company": "Google Marketing Platform",
        "data_collected": "Tracks users across websites for ad targeting and conversion measurement",
    },
    "facebook.net": {
        "category": "advertising",
        "company": "Meta",
        "data_collected": "Tracks users across websites for ad targeting and conversion measurement",
    },
    "connect.facebook.net": {
        "category": "advertising",
        "company": "Meta",
        "data_collected": "Loads Meta Pixel and tracks advertising events",
    },
    "bat.bing.com": {
        "category": "advertising",
        "company": "Microsoft Advertising",
        "data_collected": "Tracks ad conversions and user behavior for campaign measurement",
    },
    "ads-twitter.com": {
        "category": "advertising",
        "company": "X / Twitter",
        "data_collected": "Tracks advertising conversions and audience events",
    },
    "segment.com": {
        "category": "analytics",
        "company": "Segment",
        "data_collected": "Collects and routes user event data to third-party destinations",
    },
    "hotjar.com": {
        "category": "analytics",
        "company": "Hotjar",
        "data_collected": "Collects session behavior, heatmaps, and interaction data",
    },
}


def get_tracker_domains() -> dict:
    global _tracker_cache
    if _tracker_cache:
        return _tracker_cache

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                _tracker_cache = json.load(f)
            return _tracker_cache
        except Exception:
            pass

    try:
        print("Downloading Disconnect.me tracker list...")
        resp = requests.get(DISCONNECT_URL, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except Exception:
        _tracker_cache = dict(FALLBACK_TRACKERS)
        return _tracker_cache

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

    trackers.update(FALLBACK_TRACKERS)

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(trackers, f)
    except Exception:
        pass

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
