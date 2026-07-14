from __future__ import annotations

import os
from tavily import TavilyClient

from .schema import Evidence, EvidenceSource, SourceRelation
from .exceptions import KernelRuntimeError
from .source_quality import SourceTier, classify_domain, adjusted_confidence, TIER_LABELS


class Retriever:
    """
    Evidence retriever using Tavily Search API.

    Runs before the assessor. Fetches real external sources for the claim,
    classifies each by domain trust tier, filters out low-trust noise, and
    packages the rest as Evidence objects with source_type=EXTERNAL and
    real source_urls.

    Source Quality Policy v0.1:
      TIER_4 (social media, forums) is excluded by default — not because
      it's always wrong, but because it adds noise the assessor shouldn't
      have to sort through. Raise max_tier to include it explicitly.
      Every filtered source is returned in the fetch report, not silently
      dropped — the kernel logs what was excluded and why.
    """

    DEFAULT_MAX_RESULTS = 5
    FETCH_BUFFER        = 10   # raw results requested before tier filtering

    def __init__(self, api_key: str = None):
        key = api_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise KernelRuntimeError(
                "TAVILY_API_KEY not set. "
                "Set via: $env:TAVILY_API_KEY='tvly-...'"
            )
        self.client = TavilyClient(api_key=key)

    def fetch(
        self,
        claim_text:  str,
        max_results: int              = DEFAULT_MAX_RESULTS,
        max_tier:    SourceTier        = SourceTier.TIER_3,
    ) -> tuple[list[Evidence], list[dict]]:
        """
        Search for evidence relevant to the claim.

        Returns (evidence, filtered_report):
          evidence        — accepted Evidence objects, tier-classified,
                             confidence-adjusted, sorted best-first.
          filtered_report — sources excluded for being below max_tier,
                             with url + tier, for ledger transparency.
        """
        try:
            response = self.client.search(
                query=claim_text,
                max_results=self.FETCH_BUFFER,
                search_depth="basic",
            )
        except Exception as e:
            raise KernelRuntimeError(f"Tavily search failed: {e}") from e

        accepted = []
        filtered_report = []

        for r in response.get("results", []):
            url     = r.get("url", "").strip()
            content = r.get("content", "").strip()
            raw_score = float(r.get("score", 0.5))

            if not url or not content:
                continue

            tier = classify_domain(url)

            if tier > max_tier:
                filtered_report.append({
                    "url":    url,
                    "tier":   tier.value,
                    "label":  TIER_LABELS[tier],
                    "reason": "below max_tier threshold",
                })
                continue

            accepted.append(Evidence(
                content=content[:500],
                source_url=url,
                source_type=EvidenceSource.EXTERNAL,
                # Not yet classified. UNCLEAR is the only honest placeholder —
                # the kernel's clean-room classifier assigns the real relation.
                source_relation=SourceRelation.UNCLEAR,
                confidence=adjusted_confidence(raw_score, tier),
                source_tier=tier.value,
            ))

        # Sort best-first by adjusted confidence, then take top max_results
        accepted.sort(key=lambda e: e.confidence, reverse=True)
        accepted = accepted[:max_results]

        return accepted, filtered_report
