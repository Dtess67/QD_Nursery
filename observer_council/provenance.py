from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Lineage(str, Enum):
    """Independent training lineages. Diversity of lineage, not just model count."""
    ANTHROPIC = "anthropic"
    OPENAI    = "openai"
    GOOGLE    = "google"
    XAI       = "xai"
    DEEPSEEK  = "deepseek"
    ALIBABA   = "alibaba"
    META      = "meta"
    ALLENAI   = "allenai"


@dataclass(frozen=True)
class ObserverProvenance:
    """
    Model Provenance Risks — Q's proposal, July 2026.

    Documents the instrument, not just its output. Scientists document
    their instruments; this project documents its models the same way.

    A documented constraint is metadata, not a judgment. "Known
    limitation on topic X" is a fact about training. "This model is
    unreliable" is a verdict this registry does not make.
    """
    name:                str
    lineage:             Lineage
    organization:        str
    api_env_var:         str
    model_id:            str
    known_constraints:   tuple[str, ...] = field(default_factory=tuple)
    known_strengths:     tuple[str, ...] = field(default_factory=tuple)
    data_path_note:      str = ""

    def to_context_line(self) -> str:
        """One-line summary injected into cross-review prompts, so every
        observer sees the same provenance metadata about every participant —
        including itself."""
        constraints = "; ".join(self.known_constraints) or "none documented"
        return (
            f"{self.name} ({self.organization}, {self.lineage.value} lineage) — "
            f"known constraints: {constraints}"
        )


# ---------------------------------------------------------------------------
# Registry. Add new observers here — nowhere else.
# ---------------------------------------------------------------------------

REGISTRY: dict[str, ObserverProvenance] = {

    "claude": ObserverProvenance(
        name="Claude",
        lineage=Lineage.ANTHROPIC,
        organization="Anthropic",
        api_env_var="ANTHROPIC_API_KEY",
        model_id="claude-sonnet-4-6",
        known_strengths=("architectural decomposition", "long-form technical writing",
                          "contradiction detection"),
        known_constraints=(
            "in this specific project, Claude is both a Council participant and "
            "typically the one synthesizing council results for Darrell — same "
            "structural overlap flagged for Qwen (Assessor/Falsifier sharing an "
            "engine). When it matters, read raw Phase 1/2 transcripts directly "
            "rather than relying solely on Claude's summary",
            "unlike Qwen and DeepSeek, no independent outside research has audited "
            "Claude's specific behavioral tendencies at the level of detail this "
            "registry documents for those two — this entry is Anthropic-trained "
            "self-report, not third-party verified, and Claude has no privileged "
            "access to its own training process to fully audit this itself",
            "RLHF-tuned assistant models as a category have documented tendencies "
            "toward agreeableness with the person they're talking to — a general, "
            "publicly discussed concern, not specific evidence about this model",
        ),
    ),

    "gpt": ObserverProvenance(
        name="GPT (API instance)",
        lineage=Lineage.OPENAI,
        organization="OpenAI",
        api_env_var="OPENAI_API_KEY",
        model_id="gpt-5.1",
        known_strengths=("broad general reasoning", "systems integration"),
        data_path_note=(
            "This is a stateless API call, not 'Q' — the persistent ChatGPT "
            "thread with a year of project history. Treat as an independently "
            "oriented instance, not the same participant."
        ),
    ),

    "gemini": ObserverProvenance(
        name="Gemini",
        lineage=Lineage.GOOGLE,
        organization="Google DeepMind",
        api_env_var="GOOGLE_API_KEY",
        model_id="gemini-2.5-pro",
        known_strengths=("large factual knowledge base", "first-principles reframing"),
    ),

    "grok": ObserverProvenance(
        name="Grok",
        lineage=Lineage.XAI,
        organization="xAI",
        api_env_var="XAI_API_KEY",
        model_id="grok-4",
        known_strengths=("unconventional framing", "detecting groupthink"),
        known_constraints=("tends toward commentary/summary over structural "
                            "pressure-testing — treat as guest reviewer, not "
                            "primary architect, per Q's June 2026 assessment",),
    ),

    "deepseek": ObserverProvenance(
        name="DeepSeek",
        lineage=Lineage.DEEPSEEK,
        organization="DeepSeek AI",
        api_env_var="DEEPSEEK_API_KEY",
        model_id="deepseek-chat",
        known_strengths=("efficient reasoning", "strong coding"),
        known_constraints=(
            "documented weights-level restrictions on a specific topic class "
            "(PRC-sensitive political topics: Tiananmen, Taiwan, Xi Jinping, "
            "Cultural Revolution) — confirmed by independent research, traced "
            "to the fine-tuning stage, not an app-level filter",
        ),
        data_path_note=(
            "Using hosted API, not self-hosted — prompts reach DeepSeek's "
            "servers in the PRC. Do not send sensitive personal data."
        ),
    ),

    "qwen_local": ObserverProvenance(
        name="Qwen (local, kernel engine)",
        lineage=Lineage.ALIBABA,
        organization="Alibaba",
        api_env_var="",  # local via Ollama, no API key
        model_id="qwen2.5:32b",
        known_strengths=("efficient local reasoning", "already integrated with QD kernel"),
        known_constraints=(
            "documented research on the Qwen3 family shows trained-in "
            "favorable framing on China-related topics while claiming "
            "neutrality elsewhere, strongest in Chinese-language and "
            "geopolitical/economic topics, weaker effect in English general "
            "reasoning — not yet directly verified against this specific "
            "qwen2.5:32b build",
            "IMPORTANT: this is the same engine currently running both the "
            "Assessor and Falsifier in the QD kernel — using it here as well "
            "does not add independence, it duplicates the existing single "
            "point of failure",
        ),
    ),

}


def get_registered(names: list[str]) -> list[ObserverProvenance]:
    """Look up observers by key. Raises KeyError with a clear message on typo."""
    result = []
    for n in names:
        if n not in REGISTRY:
            raise KeyError(f"'{n}' not in registry. Known: {list(REGISTRY.keys())}")
        result.append(REGISTRY[n])
    return result
