from __future__ import annotations

from pathlib import Path

# Files loaded in this order — matches the manifest built July 1, 2026.
# Not every observer needs all of them for every question, but loading
# all of them is cheap and keeps every API call oriented the same way
# Project Knowledge orients a fresh Claude chat.
ORIENTATION_FILES = [
    "00_CONSTITUTION.md",
    "03_BUILD_STATUS.md",
    "04_OPEN_PROBLEMS.md",
    "05_WORKING_HYPOTHESES.md",
    "06_ESTABLISHED_RESULTS.md",
    "07_DECISION_LOG_2026-07-01.md",
    "08_FAILED_HYPOTHESES.md",
]


def load_orientation(folder: str) -> str:
    """
    Concatenate the orientation files into one context block.
    This is the fix for the stateless-API-instance problem: a fresh GPT
    or Gemini call has no memory of this project, the same way a fresh
    Claude conversation outside a Project has none. Feeding these files
    in as system context wakes up a blank instance already oriented —
    same job Project Knowledge does for Claude specifically, done here
    in a vendor-neutral way.
    """
    base = Path(folder)
    sections = []

    for filename in ORIENTATION_FILES:
        path = base / filename
        if not path.exists():
            sections.append(f"[MISSING: {filename} — not found in {folder}]")
            continue
        content = path.read_text(encoding="utf-8")
        sections.append(f"--- {filename} ---\n{content}")

    return "\n\n".join(sections)


def build_system_prompt(orientation: str, provenance_line: str) -> str:
    """
    Standard system prompt every observer receives. Orientation first,
    then a reminder of who they are in this protocol and why — matches
    the provenance-as-metadata principle: an observer should know its
    own documented constraints going in, not have them hidden.
    """
    return (
        "You are participating as an independent Observer in the QD project's "
        "multi-model review protocol. Below is the project's current orientation "
        "material — read it before answering.\n\n"
        f"{orientation}\n\n"
        "---\n\n"
        f"Your own provenance record in this protocol: {provenance_line}\n\n"
        "Operating principle for this protocol: truth before comfort. "
        "State disagreement plainly. Do not converge for the sake of agreement. "
        "If you don't know, say so — 'we need an experiment' is a valid answer."
    )
