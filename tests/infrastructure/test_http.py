"""Tests for Solara's reusable urllib-based JSON HTTP transport."""

import json
from dataclasses import FrozenInstanceError
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from solara_travel.infrastructure.http import (
    JsonHttpDecodeError,
    JsonHttpResponse,
    UrllibJsonHttpTransport,
)


class FakeUrlResponse:
    """Minimal urllib-compatible response used by offline transport tests."""

    def __init__(
        self,
        *,
        status_code: int,
        body: bytes,
    ) -> None:
        self.status_code = status_code
        self.body = body

    def __enter__(self) -> "FakeUrlResponse":
        """Enter the fake response context."""

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> bool:
        """Leave the fake response context without suppressing failures."""

        return False

    def getcode(self) -> int:
        """Return the configured HTTP status code."""

        return self.status_code

    def read(self) -> bytes:
        """Return the configured response body."""

        return self.body


class RecordingOpener:
    """Record urllib requests and return controlled responses."""

    def __init__(
        self,
        *,
        response: FakeUrlResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = (
            response
            if response is not None
            else FakeUrlResponse(
                status_code=200,
                body=b'{"places": []}',
            )
        )
        self.error = error
        self.requests: list[Request] = []
        self.timeouts: list[float] = []

    def __call__(
        self,
        request: Request,
        *,
        timeout: float,
    ) -> FakeUrlResponse:
        """Record a request and return the configured response."""

        self.requests.append(request)
        self.timeouts.append(timeout)

        if self.error is not None:
            raise self.error

        return self.response


def test_json_http_response_preserves_values() -> None:
    """Decoded HTTP response values should remain available unchanged."""

    payload = {"places": []}

    response = JsonHttpResponse(
        status_code=200,
        payload=payload,
    )

    assert response.status_code == 200
    assert response.payload is payload


def test_json_http_response_uses_value_equality() -> None:
    """Equivalent HTTP response values should compare equally."""

    first = JsonHttpResponse(
        status_code=200,
        payload={"places": []},
    )
    second = JsonHttpResponse(
        status_code=200,
        payload={"places": []},
    )

    assert first == second


def test_json_http_response_is_immutable() -> None:
    """Transport responses must not change after creation."""

    response = JsonHttpResponse(
        status_code=200,
        payload={"places": []},
    )

    with pytest.raises(FrozenInstanceError):
        response.status_code = 500


def test_post_json_uses_post_method() -> None:
    """JSON transport should issue HTTP POST requests."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={"query": "Kyoto"},
        timeout_seconds=5.0,
    )

    assert opener.requests[0].get_method() == "POST"


def test_post_json_preserves_request_url() -> None:
    """Transport should send requests to the caller-provided URL."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={"query": "Kyoto"},
        timeout_seconds=5.0,
    )

    assert opener.requests[0].full_url == "https://example.com/search"


def test_post_json_preserves_headers() -> None:
    """Provider-specific HTTP headers should reach urllib unchanged in value."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    transport.post_json(
        url="https://example.com/search",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": "test-api-key",
            "X-Goog-FieldMask": "places.displayName",
        },
        payload={"query": "Kyoto"},
        timeout_seconds=5.0,
    )

    request = opener.requests[0]

    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("X-goog-api-key") == "test-api-key"
    assert request.get_header("X-goog-fieldmask") == "places.displayName"


def test_post_json_serializes_payload_as_json() -> None:
    """Python request values should be serialized into JSON request bytes."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    payload = {
        "textQuery": "travel destinations",
        "pageSize": 10,
        "strictTypeFiltering": True,
    }

    transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload=payload,
        timeout_seconds=5.0,
    )

    request_data = opener.requests[0].data

    assert request_data is not None
    assert json.loads(request_data.decode("utf-8")) == payload


def test_post_json_supports_unicode_request_values() -> None:
    """Unicode destination and attraction text should survive serialization."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    payload = {
        "query": "São Paulo 東京 München",
    }

    transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload=payload,
        timeout_seconds=5.0,
    )

    request_data = opener.requests[0].data

    assert request_data is not None
    assert json.loads(request_data.decode("utf-8")) == payload


def test_post_json_passes_configured_timeout_to_opener() -> None:
    """The caller's explicit timeout policy should reach urllib."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={"query": "Kyoto"},
        timeout_seconds=6.5,
    )

    assert opener.timeouts == [6.5]


def test_post_json_does_not_mutate_headers() -> None:
    """Transport serialization should leave caller-owned headers unchanged."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": "test-api-key",
    }
    original = headers.copy()

    transport.post_json(
        url="https://example.com/search",
        headers=headers,
        payload={"query": "Kyoto"},
        timeout_seconds=5.0,
    )

    assert headers == original


def test_post_json_does_not_mutate_payload() -> None:
    """Transport serialization should leave caller-owned payloads unchanged."""

    opener = RecordingOpener()
    transport = UrllibJsonHttpTransport(opener=opener)

    payload = {
        "query": "Kyoto",
        "filters": {
            "type": "locality",
        },
    }
    original = {
        "query": "Kyoto",
        "filters": {
            "type": "locality",
        },
    }

    transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload=payload,
        timeout_seconds=5.0,
    )

    assert payload == original


def test_post_json_returns_decoded_json_response() -> None:
    """Successful JSON responses should become JsonHttpResponse values."""

    payload = {
        "places": [
            {
                "displayName": {
                    "text": "Kyoto",
                },
            },
        ],
    }
    opener = RecordingOpener(
        response=FakeUrlResponse(
            status_code=200,
            body=json.dumps(payload).encode("utf-8"),
        ),
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    response = transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={"query": "Kyoto"},
        timeout_seconds=5.0,
    )

    assert response == JsonHttpResponse(
        status_code=200,
        payload=payload,
    )


@pytest.mark.parametrize(
    ("body", "expected_payload"),
    [
        (b"[]", []),
        (b'"Kyoto"', "Kyoto"),
        (b"42", 42),
        (b"true", True),
        (b"null", None),
    ],
)
def test_post_json_supports_any_valid_top_level_json_value(
    body: bytes,
    expected_payload: object,
) -> None:
    """The reusable transport should decode any standards-compliant JSON value."""

    opener = RecordingOpener(
        response=FakeUrlResponse(
            status_code=200,
            body=body,
        ),
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    response = transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={},
        timeout_seconds=5.0,
    )

    assert response.payload == expected_payload


def test_post_json_decodes_unicode_response() -> None:
    """UTF-8 provider text should survive response decoding."""

    payload = {
        "name": "São Paulo 東京 München",
    }
    opener = RecordingOpener(
        response=FakeUrlResponse(
            status_code=200,
            body=json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8"),
        ),
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    response = transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={},
        timeout_seconds=5.0,
    )

    assert response.payload == payload


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"not-json",
        b"{",
        b'{"places":',
    ],
)
def test_post_json_rejects_malformed_json_response(
    body: bytes,
) -> None:
    """Malformed provider bodies should produce an explicit decode failure."""

    opener = RecordingOpener(
        response=FakeUrlResponse(
            status_code=200,
            body=body,
        ),
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    with pytest.raises(
        JsonHttpDecodeError,
        match="HTTP response did not contain valid JSON",
    ):
        transport.post_json(
            url="https://example.com/search",
            headers={"Content-Type": "application/json"},
            payload={},
            timeout_seconds=5.0,
        )


def test_post_json_rejects_invalid_utf8_response() -> None:
    """Provider bodies must use valid UTF-8 before JSON parsing."""

    opener = RecordingOpener(
        response=FakeUrlResponse(
            status_code=200,
            body=b"\xff\xfe\xfa",
        ),
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    with pytest.raises(
        JsonHttpDecodeError,
        match="HTTP response did not contain valid JSON",
    ):
        transport.post_json(
            url="https://example.com/search",
            headers={"Content-Type": "application/json"},
            payload={},
            timeout_seconds=5.0,
        )


def test_json_decode_error_preserves_original_cause() -> None:
    """Decode failures should retain their underlying parsing exception."""

    opener = RecordingOpener(
        response=FakeUrlResponse(
            status_code=200,
            body=b"not-json",
        ),
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    with pytest.raises(JsonHttpDecodeError) as exc_info:
        transport.post_json(
            url="https://example.com/search",
            headers={"Content-Type": "application/json"},
            payload={},
            timeout_seconds=5.0,
        )

    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        403,
        404,
        429,
        500,
        503,
    ],
)
def test_post_json_preserves_http_error_status_and_json_payload(
    status_code: int,
) -> None:
    """urllib HTTP errors should remain available to provider status mapping."""

    payload = {
        "error": {
            "message": "Google Places request failed",
        },
    }
    http_error = HTTPError(
        url="https://example.com/search",
        code=status_code,
        msg="provider error",
        hdrs=None,
        fp=BytesIO(
            json.dumps(payload).encode("utf-8")
        ),
    )
    opener = RecordingOpener(
        error=http_error,
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    response = transport.post_json(
        url="https://example.com/search",
        headers={"Content-Type": "application/json"},
        payload={},
        timeout_seconds=5.0,
    )

    assert response == JsonHttpResponse(
        status_code=status_code,
        payload=payload,
    )


def test_post_json_rejects_malformed_http_error_body() -> None:
    """HTTP error responses still require valid JSON provider payloads."""

    http_error = HTTPError(
        url="https://example.com/search",
        code=500,
        msg="provider error",
        hdrs=None,
        fp=BytesIO(b"not-json"),
    )
    opener = RecordingOpener(
        error=http_error,
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    with pytest.raises(
        JsonHttpDecodeError,
        match="HTTP response did not contain valid JSON",
    ):
        transport.post_json(
            url="https://example.com/search",
            headers={"Content-Type": "application/json"},
            payload={},
            timeout_seconds=5.0,
        )


def test_post_json_propagates_url_error() -> None:
    """Network failures should remain available for provider-level translation."""

    error = URLError("network unavailable")
    opener = RecordingOpener(
        error=error,
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    with pytest.raises(URLError) as exc_info:
        transport.post_json(
            url="https://example.com/search",
            headers={"Content-Type": "application/json"},
            payload={},
            timeout_seconds=5.0,
        )

    assert exc_info.value is error



def test_post_json_propagates_timeout_error() -> None:
    """Timeout failures should remain available for provider-level translation."""

    error = TimeoutError("request timed out")
    opener = RecordingOpener(
        error=error,
    )
    transport = UrllibJsonHttpTransport(opener=opener)

    with pytest.raises(TimeoutError) as exc_info:
        transport.post_json(
            url="https://example.com/search",
            headers={"Content-Type": "application/json"},
            payload={},
            timeout_seconds=5.0,
        )

    assert exc_info.value is error
