"""HTTP and serialization tests for transient Postcards enrichment."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from solara_travel.application import (
    DestinationPostcards,
    PhotoDeliveryService,
    PostcardCollection,
    PostcardPhoto,
    WayfinderDestinationNote,
    WayfinderNarrative,
)
from solara_travel.domain import RecommendationRequest, TemperatureComfortRange, TravelPeriod
from solara_travel.ports import (
    PhotoAuthorAttribution,
    PhotoMedia,
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from solara_travel.presentation.api import ApiDependencies, create_app
from solara_travel.presentation.api.recommendation_mapping import (
    recommendation_result_to_response,
)
from solara_travel.workflows import build_offline_recommendation_service


class Codec:
    def decode(self, handle: str) -> str:
        if handle == "invalid":
            raise ValueError("invalid")
        return f"places/a/photos/{handle}"

    def encode(self, reference: str) -> str:
        return reference


class Provider:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome

    def retrieve_photo(self, reference, *, max_width_px, max_height_px):
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def _result():
    service = build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
    )
    return service.recommend(
        RecommendationRequest(TravelPeriod(date(2026, 4, 10), date(2026, 4, 12)))
    )


def _client(outcome: object) -> TestClient:
    service = PhotoDeliveryService(Codec(), Provider(outcome))
    return TestClient(create_app(dependencies=ApiDependencies(photo_delivery_service=service)))


def test_photo_proxy_returns_no_store_image_without_key_exposure() -> None:
    response = _client(PhotoMedia(b"webp", "image/webp")).get("/api/v1/postcards/photo")

    assert response.status_code == 200
    assert response.content == b"webp"
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "key" not in str(response.request.url).casefold()


def test_photo_proxy_is_not_available_when_unconfigured_or_handle_invalid() -> None:
    assert TestClient(create_app()).get("/api/v1/postcards/photo").status_code == 404
    assert (
        _client(PhotoMedia(b"x", "image/png")).get("/api/v1/postcards/invalid").status_code == 404
    )


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ProviderAuthenticationError("auth"), 503),
        (ProviderRateLimitError("rate"), 503),
        (ProviderUnavailableError("down"), 503),
        (ProviderResponseError("bad"), 502),
        (ProviderError("bad"), 502),
    ],
)
def test_photo_proxy_maps_provider_failures(error: ProviderError, status_code: int) -> None:
    response = _client(error).get("/api/v1/postcards/photo")
    assert response.status_code == status_code
    assert "auth" not in response.text
    assert "rate" not in response.text


def test_mapping_adds_typed_postcards_and_rank_aligned_wayfinder() -> None:
    result = _result()
    destination = result.recommendations[0].destination
    postcards = PostcardCollection(
        (
            DestinationPostcards(
                destination,
                (
                    PostcardPhoto(
                        "/api/v1/postcards/handle",
                        "Landmark",
                        1200,
                        800,
                        "https://www.google.com/maps/place/a",
                        (PhotoAuthorAttribution("Author", "https://example.com/author"),),
                    ),
                ),
            ),
        )
    )
    notes = tuple(
        WayfinderDestinationNote(
            item.destination.name,
            "A grounded fit story.",
            "Historically mild.",
            "Keep plans flexible.",
        )
        for item in result.recommendations
    )
    wayfinder = WayfinderNarrative("A grounded opening.", notes, "Compare the shortlist.")

    response = recommendation_result_to_response(
        result, None, wayfinder=wayfinder, postcards=postcards
    )

    assert [note.destination for note in response.wayfinder.destination_notes] == [
        item.destination.name for item in result.recommendations
    ]
    assert response.recommendations[0].postcards[0].image_path.endswith("handle")
    assert response.recommendations[0].postcards[0].author_attributions[0].display_name == "Author"
    assert response.recommendations[1].postcards == []
