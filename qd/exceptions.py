"""
QD Exception Taxonomy

Two distinct severities — Q was right that they shouldn't share a type.

STRUCTURAL — constitutional violations. The kernel's guarantees were broken.
             These mean something is wrong with the system, not the input.
             Recovery strategy: halt, inspect, fix the code.

RUNTIME    — operational failures. The model misbehaved or is unreachable.
             These mean something went wrong during execution.
             Recovery strategy: retry, fallback model, surface to caller.

POLICY     — evidence integrity violations. Handled inside the Falsifier.
             Not a kernel crash — a legitimate epistemic outcome.
"""


class QDError(Exception):
    """Base class for all QD errors."""
    pass


# ── Structural ─────────────────────────────────────────────────────────────
# Constitutional violations. Kernel guarantees broken.

class StructuralViolationError(QDError):
    """
    A constitutional guarantee of the kernel was violated.
    Severity: critical. Recovery: halt and inspect.
    """
    pass


class FalsifierSkippedError(StructuralViolationError):
    """Verdict attempted without Falsifier review."""
    pass


class SchemaViolationError(StructuralViolationError):
    """Impossible schema state that could not be reconciled."""
    pass


# ── Runtime ────────────────────────────────────────────────────────────────
# Operational failures. Model misbehaved or unreachable.

class KernelRuntimeError(QDError):
    """
    Operational failure during kernel evaluation.
    Severity: operational. Recovery: retry or fallback.
    """
    pass


class ModelUnavailableError(KernelRuntimeError):
    """Ollama model not reachable or not responding."""
    pass


class ModelResponseError(KernelRuntimeError):
    """Model returned malformed or unparseable response."""
    pass


# ── Policy ─────────────────────────────────────────────────────────────────
# Evidence integrity. Not a crash — a legitimate epistemic outcome.

class EvidencePolicyViolation(QDError):
    """Evidence fails Evidence Policy. Handled inside the Falsifier."""
    pass


# ── Backward compat ────────────────────────────────────────────────────────
# EmergencyStopError mapped to StructuralViolationError.
# Nothing external depended on it yet — clean break preferred.

EmergencyStopError = StructuralViolationError
