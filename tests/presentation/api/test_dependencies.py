"""Tests for immutable FastAPI application-service dependencies."""

from dataclasses import FrozenInstanceError

import pytest

from solara_travel.application import (
    PhotoDeliveryService,
    PostcardEnrichmentService,
    RecommendationNarrationService,
    RecommendationService,
)
from solara_travel.domain import TemperatureComfortRange
from solara_travel.ports import PhotoMedia
from solara_travel.presentation.api import ApiDependencies
from solara_travel.workflows import build_offline_recommendation_service


class FakeNarrationProvider:
    """Minimal provider satisfying the narration port."""

    def generate(self, prompt: object) -> str:
        return "Grounded prose"


class Codec:
    def encode(self, reference: str) -> str:
        return reference

    def decode(self, handle: str) -> str:
        return handle


class MetadataProvider:
    def discover_postcard_photos(self, destination, attractions, *, limit):
        return ()


class MediaProvider:
    def retrieve_photo(self, reference, *, max_width_px, max_height_px):
        return PhotoMedia(b"image", "image/webp")


def _recommendation_service() -> RecommendationService:
    return build_offline_recommendation_service(
        comfort_range=TemperatureComfortRange(18.0, 28.0, 10.0)
    )


def test_dependencies_default_to_unconfigured_services() -> None:
    dependencies = ApiDependencies()

    assert dependencies.recommendation_service is None
    assert dependencies.narration_service is None
    assert dependencies.postcard_enrichment_service is None
    assert dependencies.photo_delivery_service is None


def test_dependencies_accept_valid_services() -> None:
    recommendation_service = _recommendation_service()
    narration_service = RecommendationNarrationService(FakeNarrationProvider())

    dependencies = ApiDependencies(recommendation_service, narration_service)

    assert dependencies.recommendation_service is recommendation_service
    assert dependencies.narration_service is narration_service


@pytest.mark.parametrize("value", [object(), False, "service"])
def test_dependencies_reject_invalid_recommendation_service(value: object) -> None:
    with pytest.raises(
        TypeError, match="recommendation_service must be RecommendationService or None"
    ):
        ApiDependencies(recommendation_service=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [object(), False, "service"])
def test_dependencies_reject_invalid_narration_service(value: object) -> None:
    with pytest.raises(
        TypeError,
        match="narration_service must be RecommendationNarrationService or None",
    ):
        ApiDependencies(
            recommendation_service=_recommendation_service(),
            narration_service=value,  # type: ignore[arg-type]
        )


def test_dependencies_reject_narration_without_recommendation_service() -> None:
    narration_service = RecommendationNarrationService(FakeNarrationProvider())

    with pytest.raises(
        ValueError,
        match="narration_service requires recommendation_service",
    ):
        ApiDependencies(narration_service=narration_service)


def test_dependencies_are_frozen() -> None:
    dependencies = ApiDependencies()

    with pytest.raises(FrozenInstanceError):
        dependencies.recommendation_service = _recommendation_service()  # type: ignore[misc]


def test_dependencies_accept_postcards_services() -> None:
    recommendation = _recommendation_service()
    enrichment = PostcardEnrichmentService(MetadataProvider(), Codec())
    delivery = PhotoDeliveryService(Codec(), MediaProvider())
    dependencies = ApiDependencies(
        recommendation_service=recommendation,
        postcard_enrichment_service=enrichment,
        photo_delivery_service=delivery,
    )
    assert dependencies.postcard_enrichment_service is enrichment
    assert dependencies.photo_delivery_service is delivery


def test_dependencies_validate_postcards_services_and_invariant() -> None:
    with pytest.raises(TypeError, match="postcard_enrichment_service"):
        ApiDependencies(
            recommendation_service=_recommendation_service(),
            postcard_enrichment_service=object(),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="requires recommendation_service"):
        ApiDependencies(
            postcard_enrichment_service=PostcardEnrichmentService(MetadataProvider(), Codec())
        )
    with pytest.raises(TypeError, match="photo_delivery_service"):
        ApiDependencies(photo_delivery_service=object())  # type: ignore[arg-type]
