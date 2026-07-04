class CouncilError(Exception):
    """Base class for observer council errors."""
    pass


class ObserverUnavailableError(CouncilError):
    """API key missing, endpoint unreachable, or request failed."""
    pass


class ObserverResponseError(CouncilError):
    """Observer returned something unusable — empty, malformed, or blocked."""
    pass
