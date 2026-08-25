"""Deterministic tests for Google Places Photos metadata and media adapters."""

from dataclasses import dataclass, field
from urllib.error import URLError

import pytest

from solara_travel.domain import Attraction, Destination, GeoCoordinates
from solara_travel.infrastructure.http import (
    BinaryHttpResponse,
    JsonHttpDecodeError,
    JsonHttpResponse,
)
from solara_travel.infrastructure.places import (
    GooglePhotoMediaProvider,
    GooglePostcardMetadataProvider,
)
from solara_travel.ports import (
    PhotoAuthorAttribution,
    PhotoMedia,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)


@dataclass
class Transport:
    post_outcome: object = field(default_factory=lambda: JsonHttpResponse(200, {"places": []}))
    get_outcome: object = field(
        default_factory=lambda: JsonHttpResponse(
            200, {"photoUri": "https://lh3.googleusercontent.com/photo"}
        )
    )
    binary_outcome: object = field(
        default_factory=lambda: BinaryHttpResponse(200, b"image", "image/webp")
    )
    post_calls: list[dict[str, object]] = field(default_factory=list)
    get_calls: list[dict[str, object]] = field(default_factory=list)
    binary_calls: list[dict[str, object]] = field(default_factory=list)

    def post_json(self, **kwargs):
        self.post_calls.append(kwargs)
        if isinstance(self.post_outcome, BaseException):
            raise self.post_outcome
        return self.post_outcome

    def get_json(self, **kwargs):
        self.get_calls.append(kwargs)
        if isinstance(self.get_outcome, BaseException):
            raise self.get_outcome
        return self.get_outcome

    def get_bytes(self, **kwargs):
        self.binary_calls.append(kwargs)
        if isinstance(self.binary_outcome, BaseException):
            raise self.binary_outcome
        return self.binary_outcome


def _destination() -> Destination:
    return Destination("Budapest", "Hungary", GeoCoordinates(47.5, 19.0))


def _attractions() -> tuple[Attraction, ...]:
    return (Attraction("Parliament", "landmark", GeoCoordinates(47.5, 19.0)),)


def _photo(name: str, *, author: bool = True) -> dict[str, object]:
    return {
        "name": f"places/place/photos/{name}",
        "widthPx": 1200,
        "heightPx": 800,
        "googleMapsUri": f"https://www.google.com/maps/place/{name}",
        "authorAttributions": (
            [{"displayName": "Photographer", "uri": "https://example.com/profile"}]
            if author
            else []
        ),
    }


def test_metadata_provider_requests_one_bounded_search_and_normalizes_attribution() -> None:
    transport = Transport(
        post_outcome=JsonHttpResponse(
            200,
            {
                "places": [
                    {"displayName": {"text": "Parliament"}, "photos": [_photo("one")]},
                    {"displayName": {"text": "Castle"}, "photos": [_photo("two", author=False)]},
                ]
            },
        )
    )
    provider = GooglePostcardMetadataProvider("secret", transport, 7.0)

    candidates = provider.discover_postcard_photos(_destination(), _attractions(), limit=4)

    assert [item.place_name for item in candidates] == ["Parliament", "Castle"]
    assert candidates[0].author_attributions == (
        PhotoAuthorAttribution("Photographer", "https://example.com/profile"),
    )
    assert candidates[1].author_attributions == ()
    call = transport.post_calls[0]
    assert call["payload"]["textQuery"] == "tourist attractions in Budapest, Hungary"
    assert call["payload"]["pageSize"] == 8
    assert call["headers"]["X-Goog-Api-Key"] == "secret"
    assert "places.photos" in call["headers"]["X-Goog-FieldMask"]


def test_metadata_provider_deduplicates_and_takes_one_photo_per_place() -> None:
    duplicate = _photo("one")
    transport = Transport(
        post_outcome=JsonHttpResponse(
            200,
            {
                "places": [
                    {"displayName": {"text": "A"}, "photos": [duplicate, _photo("unused")]},
                    {"displayName": {"text": "B"}, "photos": [duplicate]},
                    {"displayName": {"text": "C"}, "photos": [_photo("three")]},
                ]
            },
        )
    )
    candidates = GooglePostcardMetadataProvider("secret", transport).discover_postcard_photos(
        _destination(), _attractions(), limit=2
    )
    assert [item.opaque_reference for item in candidates] == [
        "places/place/photos/one",
        "places/place/photos/three",
    ]


@pytest.mark.parametrize("api_key", [None, "", " "])
def test_photo_providers_require_api_key(api_key: object) -> None:
    with pytest.raises(ValueError):
        GooglePostcardMetadataProvider(api_key, Transport())  # type: ignore[arg-type]


@pytest.mark.parametrize("timeout", [True, "10", 0, float("inf")])
def test_photo_providers_require_valid_timeout(timeout: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        GooglePostcardMetadataProvider("secret", Transport(), timeout)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("destination", "attractions", "limit"),
    [
        (None, (), 1),
        (_destination(), [], 1),
        (_destination(), ("bad",), 1),
        (_destination(), (), 0),
        (_destination(), (), 5),
    ],
)
def test_metadata_provider_validates_inputs(destination, attractions, limit) -> None:
    with pytest.raises((TypeError, ValueError)):
        GooglePostcardMetadataProvider("secret", Transport()).discover_postcard_photos(
            destination, attractions, limit=limit
        )


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (429, ProviderRateLimitError),
        (400, ProviderResponseError),
        (500, ProviderUnavailableError),
        (700, ProviderResponseError),
    ],
)
def test_metadata_provider_maps_google_status(status: int, error: type[Exception]) -> None:
    transport = Transport(post_outcome=JsonHttpResponse(status, {}))
    with pytest.raises(error):
        GooglePostcardMetadataProvider("secret", transport).discover_postcard_photos(
            _destination(), (), limit=1
        )


@pytest.mark.parametrize(
    ("outcome", "error"),
    [
        (JsonHttpDecodeError("bad"), ProviderResponseError),
        (TimeoutError("timeout"), ProviderUnavailableError),
        (URLError("network"), ProviderUnavailableError),
    ],
)
def test_metadata_provider_maps_transport_failures(outcome, error) -> None:
    with pytest.raises(error):
        GooglePostcardMetadataProvider(
            "secret", Transport(post_outcome=outcome)
        ).discover_postcard_photos(_destination(), (), limit=1)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"places": {}},
        {"places": ["bad"]},
        {"places": [{"displayName": "bad", "photos": []}]},
        {"places": [{"displayName": {"text": ""}, "photos": []}]},
        {"places": [{"displayName": {"text": "Place"}, "photos": {}}]},
        {"places": [{"displayName": {"text": "Place"}, "photos": ["bad"]}]},
        {"places": [{"displayName": {"text": "Place"}, "photos": [{"name": "bad"}]}]},
        {
            "places": [
                {
                    "displayName": {"text": "Place"},
                    "photos": [{**_photo("a"), "authorAttributions": {}}],
                }
            ]
        },
        {
            "places": [
                {
                    "displayName": {"text": "Place"},
                    "photos": [{**_photo("a"), "authorAttributions": ["bad"]}],
                }
            ]
        },
        {
            "places": [
                {
                    "displayName": {"text": "Place"},
                    "photos": [{**_photo("a"), "authorAttributions": [{"displayName": ""}]}],
                }
            ]
        },
        {
            "places": [
                {
                    "displayName": {"text": "Place"},
                    "photos": [
                        {
                            **_photo("a"),
                            "authorAttributions": [{"displayName": "A", "uri": "http://bad"}],
                        }
                    ],
                }
            ]
        },
    ],
)
def test_metadata_provider_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ProviderResponseError):
        GooglePostcardMetadataProvider(
            "secret", Transport(post_outcome=JsonHttpResponse(200, payload))
        ).discover_postcard_photos(_destination(), (), limit=1)


def test_media_provider_resolves_without_redirect_then_fetches_keyless_uri() -> None:
    transport = Transport()
    provider = GooglePhotoMediaProvider("secret", transport, transport, 6.0)

    media = provider.retrieve_photo(
        "places/place/photos/photo", max_width_px=1600, max_height_px=1200
    )

    assert media == PhotoMedia(b"image", "image/webp")
    get_call = transport.get_calls[0]
    assert get_call["query"] == {
        "maxWidthPx": 1600,
        "maxHeightPx": 1200,
        "skipHttpRedirect": "true",
    }
    assert get_call["headers"] == {"X-Goog-Api-Key": "secret"}
    binary_call = transport.binary_calls[0]
    assert binary_call["url"] == "https://lh3.googleusercontent.com/photo"
    assert "secret" not in binary_call["url"]
    assert "X-Goog-Api-Key" not in binary_call["headers"]


@pytest.mark.parametrize("maximum", [True, 0, -1, 1.5])
def test_media_provider_validates_body_limit(maximum: object) -> None:
    with pytest.raises(ValueError):
        GooglePhotoMediaProvider("secret", Transport(), Transport(), maximum_body_bytes=maximum)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("reference", "width", "height"),
    [
        (None, 1, 1),
        ("bad", 1, 1),
        ("places/a/photos/b", 0, 1),
        ("places/a/photos/b", 4801, 1),
        ("places/a/photos/b", 1, 0),
        ("places/a/photos/b", 1, 4801),
    ],
)
def test_media_provider_validates_request(reference, width, height) -> None:
    with pytest.raises((ValueError, ProviderResponseError)):
        GooglePhotoMediaProvider("secret", Transport(), Transport()).retrieve_photo(
            reference, max_width_px=width, max_height_px=height
        )


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"photoUri": 1},
        {"photoUri": "http://lh3.googleusercontent.com/a"},
        {"photoUri": "https://evil.example/a"},
        {"photoUri": "https://user:pass@lh3.googleusercontent.com/a"},
    ],
)
def test_media_provider_rejects_unsafe_media_uri(payload: object) -> None:
    transport = Transport(get_outcome=JsonHttpResponse(200, payload))
    with pytest.raises(ProviderResponseError):
        GooglePhotoMediaProvider("secret", transport, transport).retrieve_photo(
            "places/a/photos/b", max_width_px=1, max_height_px=1
        )


@pytest.mark.parametrize(
    "binary",
    [
        BinaryHttpResponse(200, b"", "image/webp"),
        BinaryHttpResponse(200, b"body", None),
        BinaryHttpResponse(200, b"body", "text/html"),
        BinaryHttpResponse(200, b"x" * 5, "image/jpeg; charset=binary"),
    ],
)
def test_media_provider_rejects_invalid_or_oversized_content(binary: BinaryHttpResponse) -> None:
    transport = Transport(binary_outcome=binary)
    provider = GooglePhotoMediaProvider("secret", transport, transport, maximum_body_bytes=4)
    with pytest.raises(ProviderResponseError):
        provider.retrieve_photo("places/a/photos/b", max_width_px=1, max_height_px=1)


@pytest.mark.parametrize(
    ("stage", "outcome", "error"),
    [
        ("json", JsonHttpDecodeError("bad"), ProviderResponseError),
        ("json", TimeoutError("bad"), ProviderUnavailableError),
        ("binary", TimeoutError("bad"), ProviderUnavailableError),
        ("json", JsonHttpResponse(429, {}), ProviderRateLimitError),
        ("binary", BinaryHttpResponse(503, b"", None), ProviderUnavailableError),
    ],
)
def test_media_provider_maps_failures(stage: str, outcome: object, error: type[Exception]) -> None:
    transport = Transport()
    if stage == "json":
        transport.get_outcome = outcome
    else:
        transport.binary_outcome = outcome
    with pytest.raises(error):
        GooglePhotoMediaProvider("secret", transport, transport).retrieve_photo(
            "places/a/photos/b", max_width_px=1, max_height_px=1
        )
