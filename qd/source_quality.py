from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class SourceTier(int, Enum):
    TIER_1 = 1   # highest trust — gov, edu, major peer-reviewed, wire services
    TIER_2 = 2   # established institutions — reputable journalism, encyclopedic
    TIER_3 = 3   # general web — blogs, magazines, company sites, unclassified
    TIER_4 = 4   # low trust — social media, forums, unverified user content


TIER_LABELS = {
    SourceTier.TIER_1: "TIER_1 (authoritative)",
    SourceTier.TIER_2: "TIER_2 (established)",
    SourceTier.TIER_3: "TIER_3 (general web)",
    SourceTier.TIER_4: "TIER_4 (social/low-trust)",
}

# Confidence multiplier applied per tier — TIER_4 is heavily discounted, never zeroed.
# Zeroing would hide the source rather than weighing it honestly.
TIER_MULTIPLIER = {
    SourceTier.TIER_1: 1.0,
    SourceTier.TIER_2: 0.9,
    SourceTier.TIER_3: 0.7,
    SourceTier.TIER_4: 0.3,
}

_TIER_1_SUFFIXES = (".gov", ".edu", ".mil")

_TIER_1_DOMAINS = {
    "nature.com", "science.org", "sciencedirect.com", "nejm.org", "thelancet.com",
    "jamanetwork.com", "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "who.int",
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "un.org",
}

_TIER_2_DOMAINS = {
    "nytimes.com", "washingtonpost.com", "wsj.com", "economist.com", "npr.org",
    "pbs.org", "britannica.com", "wikipedia.org", "smithsonianmag.com",
    "scientificamerican.com", "theguardian.com", "forbes.com", "bloomberg.com",
    "statista.com", "nationalgeographic.com", "mayoclinic.org", "webmd.com",
}

_TIER_4_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "reddit.com", "quora.com", "pinterest.com", "tumblr.com", "linkedin.com",
    "threads.net", "snapchat.com",
}


def classify_domain(url: str) -> SourceTier:
    """
    Classify a URL's domain into a trust tier.
    Unknown domains default to TIER_3 — general web, not penalized, not privileged.
    Subdomains match their parent (en.wikipedia.org matches wikipedia.org).
    """
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return SourceTier.TIER_3

    domain = netloc[4:] if netloc.startswith("www.") else netloc

    def _matches(domain: str, known: set[str]) -> bool:
        return domain in known or any(
            domain == d or domain.endswith("." + d) for d in known
        )

    if any(domain.endswith(suffix) for suffix in _TIER_1_SUFFIXES):
        return SourceTier.TIER_1
    if _matches(domain, _TIER_1_DOMAINS):
        return SourceTier.TIER_1
    if _matches(domain, _TIER_2_DOMAINS):
        return SourceTier.TIER_2
    if _matches(domain, _TIER_4_DOMAINS):
        return SourceTier.TIER_4

    return SourceTier.TIER_3


def adjusted_confidence(raw_confidence: float, tier: SourceTier) -> float:
    """Apply tier multiplier to a raw confidence score. Never exceeds 1.0."""
    return min(1.0, max(0.0, raw_confidence * TIER_MULTIPLIER[tier]))
