"""Provider-boundary errors used by Solara infrastructure adapters."""


class ProviderError(RuntimeError):
    """Base exception for failures originating at provider boundaries."""


class ProviderAuthenticationError(ProviderError):
    """Raised when a provider rejects configured credentials."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider refuses requests because of rate limiting."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns malformed or unusable data."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider cannot currently satisfy a request."""