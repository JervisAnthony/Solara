"""Tests for provider-boundary error contracts."""

import pytest

from solara_travel.ports.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        ProviderAuthenticationError,
        ProviderRateLimitError,
        ProviderResponseError,
        ProviderUnavailableError,
    ],
)
def test_provider_errors_share_common_base(
    error_type: type[ProviderError],
) -> None:
    """Specific provider failures should be catchable through ProviderError."""

    error = error_type("provider failure")

    assert isinstance(error, ProviderError)


@pytest.mark.parametrize(
    ("error_type", "message"),
    [
        (
            ProviderAuthenticationError,
            "provider credentials were rejected",
        ),
        (
            ProviderRateLimitError,
            "provider rate limit was exceeded",
        ),
        (
            ProviderResponseError,
            "provider returned an invalid response",
        ),
        (
            ProviderUnavailableError,
            "provider is currently unavailable",
        ),
    ],
)
def test_provider_errors_preserve_message(
    error_type: type[ProviderError],
    message: str,
) -> None:
    """Provider errors should preserve useful human-readable context."""

    error = error_type(message)

    assert str(error) == message


def test_provider_authentication_error_is_provider_error() -> None:
    """Authentication failures belong to the provider error hierarchy."""

    assert issubclass(ProviderAuthenticationError, ProviderError)


def test_provider_rate_limit_error_is_provider_error() -> None:
    """Rate-limit failures belong to the provider error hierarchy."""

    assert issubclass(ProviderRateLimitError, ProviderError)


def test_provider_response_error_is_provider_error() -> None:
    """Malformed or unusable responses belong to the provider hierarchy."""

    assert issubclass(ProviderResponseError, ProviderError)


def test_provider_unavailable_error_is_provider_error() -> None:
    """Temporary provider availability failures share the common boundary."""

    assert issubclass(ProviderUnavailableError, ProviderError)


def test_provider_errors_can_be_caught_through_common_base() -> None:
    """Application code should be able to handle provider failures generically."""

    with pytest.raises(ProviderError, match="places provider unavailable"):
        raise ProviderUnavailableError("places provider unavailable")