from __future__ import annotations

import os
from tavily import TavilyClient

from .schema import Evidence, EvidenceSource
from .exceptions import KernelRuntimeError


class Retriever:
    """
    Evidence retriever using Tavily Search API.

    Runs before the assessor. Fetches real external sources for the claim
    and packages them as Evidence objects with source_type=EXTERNAL and
    real source_urls.

    This is why the Evidence Policy stops firing — the retriever provides
    what the assessor previously couldn't: verifiable external sources.

    The assessor's job changes: it no longer generates evidence from model
    memory. It reasons over what the retriever provides.
    """

    DEFAULT_MAX_RESULTS = 5

    def __init__(self, api_key: str = None):
        key = api_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise KernelRuntimeError(
                "TAVILY_API_KEY not set. "
                "Set via: $env:TAVILY_API_KEY='tvly-...'"
            )
        self.client = TavilyClient(api_key=key)

    def fetch(self, claim_text: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[Evidence]:
        """
        Search for evidence relevant to the claim.
        Returns Evidence objects — all EXTERNAL, all with real URLs.
        supports_claim defaults to True; assessor reclassifies during reasoning.
        """
        try:
            response = self.client.search(
                query=claim_text,
                max_results=max_results,
                search_depth="basic",
            )
        except Exception as e:
            raise KernelRuntimeError(f"Tavily search failed: {e}") from e

        evidence = []
        for r in response.get("results", []):
            url     = r.get("url", "").strip()
            content = r.get("content", "").strip()
            score   = float(r.get("score", 0.5))

            if not url or not content:
                continue

            evidence.append(Evidence(
                content=content[:500],
                source_url=url,
                source_type=EvidenceSource.EXTERNAL,
                supports_claim=True,   # assessor reclassifies — see kernel._assess()
                confidence=min(score, 1.0),
            ))

        return evidence
