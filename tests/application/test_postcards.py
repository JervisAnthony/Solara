"""Tests for non-fatal Postcards enrichment and photo delivery."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from solara_travel.application import (
    DestinationPostcards,
    InvalidPhotoHandleError,
    PhotoDeliveryService,
    PostcardCollection,
    PostcardEnrichmentService,
    PostcardPhoto,
)
from solara_travel.domain import RecommendationRequest, TemperatureComfortRange, TravelPeriod
from solara_travel.ports import (
    PhotoAuthorAttribution,
    PhotoMedia,
    PostcardPhotoCandidate,
    ProviderUnavailableError,
)
from solara_travel.workflows import build_offline_recommendation_service


def _result():
    service = build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
    )
    return service.recommend(
        RecommendationRequest(TravelPeriod(date(2026, 4, 10), date(2026, 4, 12)))
    )


class Codec:
    def encode(self, reference: str) -> str:
        return f"signed-{reference.rsplit('/', 1)[-1]}"

    def decode(self, handle: str) -> str:
        if handle == "bad":
            raise ValueError("invalid")
        return f"places/a/photos/{handle}"


class MetadataProvider:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[object] = []

    def discover_postcard_photos(self, destination, attractions, *, limit):
        self.calls.append((destination, attractions, limit))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class MediaProvider:
    def __init__(self, outcome: PhotoMedia | None = None) -> None:
        self.outcome = outcome or PhotoMedia(b"image", "image/webp")
        self.calls: list[object] = []

    def retrieve_photo(self, reference, *, max_width_px, max_height_px):
        self.calls.append((reference, max_width_px, max_height_px))
        return self.outcome


def _candidate(index: int = 1) -> PostcardPhotoCandidate:
    return PostcardPhotoCandidate(
        f"places/a/photos/{index}",
        f"Place {index}",
        1200,
        800,
        f"https://www.google.com/maps/place/{index}",
        (PhotoAuthorAttribution("Photographer", "https://example.com/profile"),),
    )


def test_enrichment_preserves_destination_order_and_bounds_photos() -> None:
    provider = MetadataProvider(tuple(_candidate(index) for index in range(1, 6)))
    service = PostcardEnrichmentService(provider, Codec())
    result = _result()

    collection = service.enrich(result)

    assert [item.destination for item in collection.destinations] == [
        item.destination for item in result.recommendations
    ]
    assert len(collection.destinations[0].photos) == 4
    assert collection.destinations[0].photos[0].image_path == "/api/v1/postcards/signed-1"
    assert collection.for_destination(result.recommendations[0].destination) is not None
    assert all(call[2] == 4 for call in provider.calls)


@pytest.mark.parametrize(
    "outcome",
    [ProviderUnavailableError("offline"), ValueError("invalid"), TypeError("invalid")],
)
def test_enrichment_failure_is_nonfatal(outcome: BaseException) -> None:
    collection = PostcardEnrichmentService(MetadataProvider(outcome), Codec()).enrich(_result())
    assert all(item.photos == () for item in collection.destinations)


def test_enrichment_validates_dependencies_and_input() -> None:
    with pytest.raises(TypeError, match="provider"):
        PostcardEnrichmentService(object(), Codec())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="handle_codec"):
        PostcardEnrichmentService(MetadataProvider(()), object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="between one and four"):
        PostcardEnrichmentService(MetadataProvider(()), Codec(), 5)
    with pytest.raises(TypeError, match="RecommendationResult"):
        PostcardEnrichmentService(MetadataProvider(()), Codec()).enrich(None)  # type: ignore[arg-type]


def test_postcard_values_validate_browser_safe_metadata() -> None:
    photo = PostcardPhoto(
        "/api/v1/postcards/handle",
        "Parliament",
        1200,
        800,
        "https://www.google.com/maps/place/a",
    )
    destination = _result().recommendations[0].destination
    cards = DestinationPostcards(destination, (photo,))
    collection = PostcardCollection((cards,))
    assert collection.for_destination(destination) is cards
    assert collection.for_destination(_result().recommendations[1].destination) is None
    with pytest.raises(FrozenInstanceError):
        photo.place_name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "values",
    [
        ("/elsewhere", "Place", 1, 1, "https://www.google.com/maps/a"),
        ("/api/v1/postcards/a", " ", 1, 1, "https://www.google.com/maps/a"),
        ("/api/v1/postcards/a", "Place", 0, 1, "https://www.google.com/maps/a"),
        ("/api/v1/postcards/a", "Place", 1, 0, "https://www.google.com/maps/a"),
        ("/api/v1/postcards/a", "Place", 1, 1, "https://example.com/a"),
    ],
)
def test_postcard_photo_rejects_invalid_metadata(values: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        PostcardPhoto(*values)  # type: ignore[arg-type]


def test_destination_and_collection_validate_types_and_bounds() -> None:
    destination = _result().recommendations[0].destination
    photo = PostcardPhoto("/api/v1/postcards/a", "Place", 1, 1, "https://www.google.com/maps/a")
    with pytest.raises(TypeError, match="destination"):
        DestinationPostcards(None, ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="photos must be a tuple"):
        DestinationPostcards(destination, [])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at most four"):
        DestinationPostcards(destination, (photo,) * 5)
    with pytest.raises(TypeError, match="every photo"):
        DestinationPostcards(destination, ("bad",))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="destinations"):
        PostcardCollection(("bad",))  # type: ignore[arg-type]


def test_photo_delivery_verifies_handle_and_dimensions() -> None:
    provider = MediaProvider()
    service = PhotoDeliveryService(Codec(), provider, 1400, 1000)
    assert service.retrieve("photo-1") == PhotoMedia(b"image", "image/webp")
    assert provider.calls == [("places/a/photos/photo-1", 1400, 1000)]


@pytest.mark.parametrize("handle", [None, "", "bad"])
def test_photo_delivery_rejects_invalid_handle(handle: object) -> None:
    with pytest.raises(InvalidPhotoHandleError):
        PhotoDeliveryService(Codec(), MediaProvider()).retrieve(handle)  # type: ignore[arg-type]


def test_photo_delivery_validates_configuration() -> None:
    with pytest.raises(TypeError, match="handle_codec"):
        PhotoDeliveryService(object(), MediaProvider())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="provider"):
        PhotoDeliveryService(Codec(), object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="max_width"):
        PhotoDeliveryService(Codec(), MediaProvider(), 0, 100)
    with pytest.raises(ValueError, match="max_height"):
        PhotoDeliveryService(Codec(), MediaProvider(), 100, 5000)
