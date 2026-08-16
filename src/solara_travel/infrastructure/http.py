"""Reusable HTTP transport contracts and implementations for Solara."""

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class JsonHttpResponse:
    """Immutable HTTP response containing a status code and decoded JSON payload."""

    status_code: int
    payload: object


class JsonHttpDecodeError(ValueError):
    """Raised when an HTTP response body cannot be decoded as valid JSON."""


class JsonHttpTransport(Protocol):
    """Transport contract for synchronous JSON POST requests."""

    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """Send a JSON POST request and return its decoded response."""

        ...


class UrlResponse(Protocol):
    """Minimal response behavior required from an urllib-compatible opener."""

    def __enter__(self) -> "UrlResponse":
        """Enter the response context."""

        ...

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> bool | None:
        """Leave the response context."""

        ...

    def getcode(self) -> int:
        """Return the HTTP status code."""

        ...

    def read(self) -> bytes:
        """Read the complete response body."""

        ...


class UrlOpener(Protocol):
    """Callable contract required by the urllib JSON transport."""

    def __call__(
        self,
        request: Request,
        *,
        timeout: float,
    ) -> UrlResponse:
        """Open an HTTP request and return a response context."""

        ...


@dataclass(slots=True)
class UrllibJsonHttpTransport:
    """Synchronous JSON HTTP transport backed by Python's standard library."""

    opener: UrlOpener = urlopen  # type: ignore[assignment]

    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """POST JSON and return the decoded response.

        HTTPError responses are converted back into JsonHttpResponse values so
        provider-specific adapters can translate status codes into their own
        semantic error hierarchy. Network and timeout failures propagate to the
        calling provider layer unchanged.
        """

        request_body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        request = Request(
            url=url,
            data=request_body,
            headers=headers,
            method="POST",
        )

        try:
            with self.opener(
                request,
                timeout=timeout_seconds,
            ) as response:
                status_code = response.getcode()
                body = response.read()
        except HTTPError as exc:
            status_code = exc.code
            body = exc.read()

        return JsonHttpResponse(
            status_code=status_code,
            payload=_decode_json_body(body),
        )


def _decode_json_body(body: bytes) -> object:
    """Decode a UTF-8 response body containing standards-compliant JSON."""

    try:
        text = body.decode("utf-8")
        return json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JsonHttpDecodeError(
            "HTTP response did not contain valid JSON"
        ) from exc
